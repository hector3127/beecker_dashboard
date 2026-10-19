"""Lectura de las horas de Clockify guardadas en la base diaria."""

import threading
from datetime import date
from typing import Any

from django.db import connection
from django.db.models import Max

from apps.datastore.models import ClockifyMonthSync, ClockifyTimeEntry

"""BKD.130.004 - Lectura de la base de Clockify
Regresa los registros con la misma forma que el reporte detallado, para
que el mapeo y las reglas existentes (CR, fechas, tarifas) no cambien.
"""

JsonObject = dict[str, Any]


def read_month_rows(project_id: str, month: date) -> list[JsonObject] | None:
    """
    Registros de un proyecto en un mes ya sincronizado.

    Args:
        project_id: ID del proyecto en Clockify.
        month: Primer dia del mes.

    Returns:
        Los registros en formato de reporte, o None si el mes no esta en
        la base (quien llama consulta Clockify).
    """
    try:
        if not ClockifyMonthSync.objects.filter(month=month).exists():
            return None
        return [
            {
                "_id": entry.entry_id,
                "projectId": entry.project_id,
                "projectName": entry.project_name,
                "taskId": entry.task_id,
                "taskName": entry.task_name,
                "userId": entry.user_id,
                "userName": entry.user_name,
                "tags": [{"name": tag} for tag in entry.tags],
                "description": entry.description,
                "billable": entry.billable,
                "timeInterval": {
                    "start": entry.start,
                    "end": entry.end,
                    "duration": entry.duration_seconds,
                },
            }
            for entry in ClockifyTimeEntry.objects.filter(
                project_id=project_id, month=month
            )
        ]
    finally:
        # shortcut: los reportes se leen en hilos; se cierra su conexion
        # para no dejarla abierta. Cambiar si el loader deja de usar hilos.
        if threading.current_thread() is not threading.main_thread():
            connection.close()


def store_stamp() -> str:
    """
    Marca de la ultima sincronizacion, para invalidar cortes guardados.

    Returns:
        Fecha y hora de la ultima sincronizacion, o cadena vacia.
    """
    last = ClockifyMonthSync.objects.aggregate(last=Max("synced_at"))["last"]
    return last.isoformat() if last else ""
