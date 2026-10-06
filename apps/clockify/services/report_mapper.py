"""Conversion de registros del reporte de Clockify a TimeEntry."""

from collections.abc import Mapping
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from apps.clockify.services.duration_parser import parse_duration_hours
from core.time_entries.models import TimeEntry
from core.utils.numbers import round_half_up
from core.utils.text import normalize_name, to_text

"""BKD.020.007 - Registros de Clockify
Convierte cada registro del reporte detallado al mismo formato que
regresaba obtenerHorasClockifyPorProyecto().
"""

UNKNOWN_RESOURCE_NAME = "Sin nombre"


def build_time_entry_from_report(
    report_entry: Mapping[str, Any],
    internal_project_id: str,
    costing_rate_by_resource: Mapping[str, float],
    report_timezone: ZoneInfo,
) -> TimeEntry:
    """
    Convierte un registro del reporte detallado.

    Args:
        report_entry: Registro tal como lo regresa Clockify.
        internal_project_id: ID del proyecto en el panel.
        costing_rate_by_resource: Nombre normalizado -> costing rate.
        report_timezone: Zona horaria para calcular la fecha del dia.

    Returns:
        El registro de tiempo equivalente.
    """
    entry_id = to_text(report_entry.get("_id") or report_entry.get("id"))
    time_interval = report_entry.get("timeInterval") or {}
    user = report_entry.get("user") or {}
    resource_name = to_text(
        report_entry.get("userName")
        or user.get("name")
        or report_entry.get("userId")
        or UNKNOWN_RESOURCE_NAME,
    )
    hours = parse_duration_hours(time_interval.get("duration"), entry_id)

    return TimeEntry(
        entry_id=entry_id,
        project_id=internal_project_id,
        resource_name=resource_name,
        entry_date=parse_entry_day(time_interval.get("start"), report_timezone),
        duration_hours=round_half_up(hours, 2),
        is_billable=bool(report_entry.get("billable")),
        costing_rate=costing_rate_by_resource.get(
            normalize_name(resource_name),
            0.0,
        ),
        description=to_text(report_entry.get("description")),
        tags=read_tag_names(report_entry.get("tags")),
        task_name=read_task_name(report_entry),
        task_id=read_task_id(report_entry),
        started_at=parse_local_moment(
            time_interval.get("start"), report_timezone
        ),
        ended_at=parse_local_moment(time_interval.get("end"), report_timezone),
    )


def read_tag_names(raw_tags: object) -> tuple[str, ...]:
    """
    Lee los nombres de los tags de un registro.

    Args:
        raw_tags: Lista de tags (objetos con name o textos).

    Returns:
        Los nombres de los tags.
    """
    if not isinstance(raw_tags, list):
        return ()

    return tuple(
        to_text(tag.get("name") if isinstance(tag, dict) else tag).strip()
        for tag in raw_tags
    )


def read_task_name(report_entry: Mapping[str, Any]) -> str:
    """
    Lee el nombre de la tarea de un registro.

    Args:
        report_entry: Registro del reporte detallado.

    Returns:
        El nombre de la tarea, o cadena vacia.
    """
    task = report_entry.get("task")
    task_name = report_entry.get("taskName") or (
        task.get("name") if isinstance(task, dict) else ""
    )

    return to_text(task_name)


def read_task_id(report_entry: Mapping[str, Any]) -> str:
    """
    Lee el ID de la tarea de un registro (taskId o task.id).

    Args:
        report_entry: Registro del reporte detallado.

    Returns:
        El ID de la tarea, o cadena vacia.
    """
    task = report_entry.get("task")
    task_id = report_entry.get("taskId") or (
        task.get("id") if isinstance(task, dict) else ""
    )

    return to_text(task_id)


def parse_local_moment(
    moment_text: object,
    report_timezone: ZoneInfo,
) -> datetime | None:
    """
    Convierte un instante ISO 8601 de Clockify a hora local sin zona.

    Args:
        moment_text: Inicio o fin del registro.
        report_timezone: Zona horaria del reporte.

    Returns:
        La fecha y hora local, o None si no es valida.
    """
    if not isinstance(moment_text, str) or not moment_text:
        return None

    try:
        moment = datetime.fromisoformat(moment_text.replace("Z", "+00:00"))
    except ValueError:
        return None

    if moment.tzinfo is not None:
        moment = moment.astimezone(report_timezone).replace(tzinfo=None)

    return moment


def parse_entry_day(
    start_text: object,
    report_timezone: ZoneInfo,
) -> datetime | None:
    """
    Calcula el dia local en que inicio el registro.

    Args:
        start_text: Inicio del registro en ISO 8601.
        report_timezone: Zona horaria del reporte.

    Returns:
        La medianoche local de ese dia, o None si no hay inicio valido.
    """
    if not isinstance(start_text, str) or not start_text:
        return None

    try:
        start_moment = datetime.fromisoformat(start_text.replace("Z", "+00:00"))
    except ValueError:
        # Un inicio ilegible deja el registro sin fecha; sus horas
        # cuentan en el total pero no en la semana actual.
        return None

    if start_moment.tzinfo is not None:
        start_moment = start_moment.astimezone(report_timezone)

    return datetime(start_moment.year, start_moment.month, start_moment.day)
