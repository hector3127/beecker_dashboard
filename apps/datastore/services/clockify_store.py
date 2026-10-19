"""Lectura de las horas de Clockify guardadas en la base diaria."""

import threading
from collections.abc import Container
from datetime import date
from typing import Any

from django.db import connection

from apps.datastore.models import ClockifyMonthSync, ClockifyTimeEntry
from core.utils.parallel import is_pool_worker

"""BKD.130.004 - Lectura de la base de Clockify
Regresa los registros con la misma forma que el reporte detallado, para
que el mapeo y las reglas existentes (CR, fechas, tarifas) no cambien.
"""

JsonObject = dict[str, Any]

ROW_FIELDS = (
    "entry_id",
    "project_id",
    "project_name",
    "task_id",
    "task_name",
    "user_id",
    "user_name",
    "tags",
    "description",
    "billable",
    "start",
    "end",
    "duration_seconds",
)


def store_state() -> tuple[str, frozenset[date]]:
    """
    Meses sincronizados y marca de la ultima sincronizacion (una consulta).

    Returns:
        La marca (fecha y hora de la ultima sincronizacion, o cadena
        vacia) y el primer dia de cada mes guardado. La marca invalida
        los cortes guardados con la base anterior.
    """
    synced = dict(ClockifyMonthSync.objects.values_list("month", "synced_at"))
    last = max(synced.values(), default=None)
    return (last.isoformat() if last else ""), frozenset(synced)


def store_stamp() -> str:
    """
    Marca de la ultima sincronizacion, para invalidar cortes guardados.

    Returns:
        Fecha y hora de la ultima sincronizacion, o cadena vacia.
    """
    return store_state()[0]


def read_month_rows(
    project_id: str,
    month: date,
    synced: Container[date] | None = None,
) -> list[JsonObject] | None:
    """
    Registros de un proyecto en un mes ya sincronizado.

    Args:
        project_id: ID del proyecto en Clockify.
        month: Primer dia del mes.
        synced: Meses guardados, si quien llama ya los conoce (evita una
            consulta por cada lectura).

    Returns:
        Los registros en formato de reporte, o None si el mes no esta en
        la base (quien llama consulta Clockify).
    """
    try:
        if synced is None:
            synced = frozenset(
                ClockifyMonthSync.objects.values_list("month", flat=True)
            )
        if month not in synced:
            return None
        return [
            {
                "_id": entry_id,
                "projectId": entry_project,
                "projectName": project_name,
                "taskId": task_id,
                "taskName": task_name,
                "userId": user_id,
                "userName": user_name,
                "tags": [{"name": tag} for tag in tags],
                "description": description,
                "billable": billable,
                "timeInterval": {
                    "start": start,
                    "end": end,
                    "duration": duration,
                },
            }
            for (
                entry_id,
                entry_project,
                project_name,
                task_id,
                task_name,
                user_id,
                user_name,
                tags,
                description,
                billable,
                start,
                end,
                duration,
            ) in ClockifyTimeEntry.objects.filter(
                project_id=project_id, month=month
            ).values_list(*ROW_FIELDS)
        ]
    finally:
        # Los hilos de map_in_parallel cierran su conexion al terminar; otro
        # hilo (que no es el principal) la cierra aqui para no dejarla abierta.
        if (
            threading.current_thread() is not threading.main_thread()
            and not is_pool_worker()
        ):
            connection.close()
