"""Horas FACT y registros foco rojo de los ultimos 7 dias."""

from collections.abc import Collection, Sequence
from datetime import datetime, timedelta

from apps.dashboard.constants import (
    EXCESSIVE_DAY_THRESHOLD_HOURS,
    LONG_ENTRY_THRESHOLD_HOURS,
    WEEK_DAYS,
)
from apps.dashboard.schemas.dashboard_models import WeeklyHours
from core.time_entries.models import TimeEntry
from core.utils.dates import format_iso_date
from core.utils.numbers import round_half_up

"""BKD.010.008 - Horas de la semana y foco rojo
Equivale a calcularHorasYFocoRojoDeLaSemana(). Un registro es foco rojo
si dura 4 horas o mas, o si su recurso suma mas de 10 horas ese dia.
"""


def calculate_weekly_hours(
    project_ids: Collection[str],
    time_entries: Sequence[TimeEntry],
    now: datetime,
) -> WeeklyHours:
    """
    Calcula las horas de la ultima semana del portafolio filtrado.

    Args:
        project_ids: IDs de los proyectos filtrados.
        time_entries: Registros de tiempo del portafolio.
        now: Fecha y hora actual.

    Returns:
        Horas FACT por proyecto, total y cantidad de focos rojos.
    """
    week_start = now - timedelta(days=WEEK_DAYS)
    weekly_entries = [
        time_entry
        for time_entry in time_entries
        if time_entry.project_id in project_ids
        and time_entry.entry_date is not None
        and week_start <= time_entry.entry_date <= now
    ]

    hours_by_project: dict[str, float] = {}
    hours_by_resource_day: dict[str, float] = {}

    for time_entry in weekly_entries:
        if time_entry.is_billable:
            hours_by_project[time_entry.project_id] = (
                hours_by_project.get(time_entry.project_id, 0.0)
                + time_entry.duration_hours
            )

        day_key = build_resource_day_key(time_entry)
        hours_by_resource_day[day_key] = (
            hours_by_resource_day.get(day_key, 0.0) + time_entry.duration_hours
        )

    red_flag_count = sum(
        1
        for time_entry in weekly_entries
        if is_red_flag(time_entry, hours_by_resource_day)
    )

    return WeeklyHours(
        hours_by_project=hours_by_project,
        total_hours=round_half_up(sum(hours_by_project.values()), 2),
        red_flag_count=red_flag_count,
    )


def build_resource_day_key(time_entry: TimeEntry) -> str:
    """
    Construye la llave recurso|fecha para sumar horas por dia.

    Args:
        time_entry: Registro con fecha valida.

    Returns:
        La llave del recurso y el dia.
    """
    entry_day = (
        format_iso_date(time_entry.entry_date)
        if time_entry.entry_date is not None
        else ""
    )

    return f"{time_entry.resource_name}|{entry_day}"


def is_red_flag(
    time_entry: TimeEntry,
    hours_by_resource_day: dict[str, float],
) -> bool:
    """
    Indica si un registro es foco rojo.

    Args:
        time_entry: Registro a evaluar.
        hours_by_resource_day: Horas totales por recurso y dia.

    Returns:
        True si el dia es excesivo o el registro es demasiado largo.
    """
    day_total = hours_by_resource_day.get(
        build_resource_day_key(time_entry),
        0.0,
    )

    return (
        day_total > EXCESSIVE_DAY_THRESHOLD_HOURS
        or time_entry.duration_hours >= LONG_ENTRY_THRESHOLD_HOURS
    )
