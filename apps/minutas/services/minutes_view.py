"""Datos de la vista Minutas IA con filtros de fecha y proyecto."""

import math
from collections.abc import Sequence
from datetime import datetime
from typing import Any

from apps.minutas.constants import (
    AGREEMENT_SEPARATOR,
    ALL_PROJECTS,
    MINUTE_RISK_ORIGINS,
)
from core.utils.cell_types import SheetRow
from core.utils.dates import to_datetime, to_utc_iso
from core.utils.text import to_text

"""BKD.060.007 - Vista de minutas
Equivale a getMinutasViewData() y getProyectosConMinutas().
"""

JsonObject = dict[str, Any]


def build_minutes_view(
    minute_rows: Sequence[SheetRow],
    pending_rows: Sequence[SheetRow],
    risk_rows: Sequence[SheetRow],
    filters: object,
) -> JsonObject:
    """
    Arma las minutas con sus pendientes, riesgos y acuerdos.

    Args:
        minute_rows: Filas de Minutas.
        pending_rows: Filas de Pendientes_Minutas.
        risk_rows: Filas de Riesgos.
        filters: {"fecha": "YYYY-MM-DD", "proyecto": ID} o None.

    Returns:
        {"minutas": [...]} ordenadas de la mas reciente a la mas antigua.
    """
    minutes = sorted(
        minute_rows,
        key=lambda row: MeetingOrder(meeting_ms(row.get("Fecha_Reunion"))),
    )
    minutes = apply_filters(minutes, filters)
    minute_risks = [
        row for row in risk_rows if row.get("Origen") in MINUTE_RISK_ORIGINS
    ]

    return {
        "minutas": [
            build_minute(row, pending_rows, minute_risks) for row in minutes
        ],
    }


class MeetingOrder:
    """
    Orden de la reunion mas reciente a la mas antigua.

    Replica el comparador del original (b - a): con una fecha invalida
    el resultado es NaN, nunca es "menor", y el registro queda donde cae
    (Python y V8 usan el mismo algoritmo TimSort).
    """

    __slots__ = ("milliseconds",)

    def __init__(self, milliseconds: float) -> None:
        self.milliseconds = milliseconds

    def __lt__(self, other: "MeetingOrder") -> bool:
        return other.milliseconds - self.milliseconds < 0


def meeting_ms(value: object) -> float:
    """
    Milisegundos de la fecha de reunion, como new Date(valor).

    Args:
        value: Fecha de la celda.

    Returns:
        Los milisegundos, o NaN si no es fecha.
    """
    if isinstance(value, bool) or not isinstance(value, str | int | float):
        return math.nan

    moment = to_datetime(value)

    return moment.timestamp() * 1000 if moment is not None else math.nan


def apply_filters(
    minutes: list[SheetRow],
    filters: object,
) -> list[SheetRow]:
    """
    Filtra por fecha de reunion (dia local) y por proyecto.

    Args:
        minutes: Minutas ordenadas.
        filters: Filtros del frontend.

    Returns:
        Las minutas que cumplen los filtros.
    """
    if not isinstance(filters, dict):
        return minutes

    wanted_date = filters.get("fecha")
    wanted_project = filters.get("proyecto")

    if wanted_date:
        minutes = [
            row
            for row in minutes
            if meeting_day(row.get("Fecha_Reunion")) == wanted_date
        ]

    if wanted_project and wanted_project != ALL_PROJECTS:
        minutes = [
            row for row in minutes if row.get("ID_Proyecto") == wanted_project
        ]

    return minutes


def meeting_day(value: object) -> str | None:
    """
    Dia local de la reunion en formato YYYY-MM-DD.

    Args:
        value: Fecha de la reunion.

    Returns:
        El dia, o None si no hay fecha valida.
    """
    if not value or not isinstance(value, str | int | float):
        return None

    moment = to_datetime(value)

    return moment.strftime("%Y-%m-%d") if moment is not None else None


def build_minute(
    row: SheetRow,
    pending_rows: Sequence[SheetRow],
    risk_rows: Sequence[SheetRow],
) -> JsonObject:
    """
    Arma una minuta con las llaves que usa el frontend.

    Args:
        row: Fila de Minutas.
        pending_rows: Filas de Pendientes_Minutas.
        risk_rows: Riesgos generados por minutas.

    Returns:
        La minuta.
    """
    minute_id = row.get("ID_Minuta")
    minute_prefix = to_text(minute_id) if minute_id else ""
    agreements = row.get("Acuerdos")

    return {
        "id": minute_id,
        "proyecto": row.get("ID_Proyecto"),
        "fecha": format_meeting_date(row.get("Fecha_Reunion")),
        "asistentes": row.get("Asistentes"),
        "resumen": row.get("Resumen_IA"),
        "acuerdos": (
            to_text(agreements).split(AGREEMENT_SEPARATOR) if agreements else []
        ),
        "docUrl": row.get("Doc_URL"),
        "pendientes": [
            pending
            for pending in pending_rows
            if pending.get("ID_Minuta") == minute_id
        ],
        "riesgos": [
            risk
            for risk in risk_rows
            if risk.get("ID_Riesgo")
            and minute_prefix
            and to_text(risk.get("ID_Riesgo")).startswith(minute_prefix)
        ],
    }


def format_meeting_date(value: object) -> object:
    """
    Convierte la fecha de reunion a ISO para el frontend.

    Args:
        value: Fecha de la celda.

    Returns:
        La fecha ISO UTC; el valor original si no es fecha.
    """
    if not value or not isinstance(value, str | int | float):
        return value

    moment = to_datetime(value)

    return to_utc_iso(moment) if isinstance(moment, datetime) else value


def list_projects_with_minutes(
    minute_rows: Sequence[SheetRow],
    project_rows: Sequence[SheetRow],
) -> list[str]:
    """
    Lista los proyectos que tienen minutas para el filtro.

    Args:
        minute_rows: Filas de Minutas.
        project_rows: Filas de Proyectos.

    Returns:
        "Todos los proyectos" seguido de los IDs con minutas.
    """
    ids_with_minutes = {
        row.get("ID_Proyecto") for row in minute_rows if row.get("ID_Proyecto")
    }

    return [ALL_PROJECTS] + [
        to_text(row.get("ID_Proyecto"))
        for row in project_rows
        if row.get("ID_Proyecto") in ids_with_minutes
    ]
