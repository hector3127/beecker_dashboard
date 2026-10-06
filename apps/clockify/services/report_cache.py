"""Tiempo de cache de los reportes de horas de Clockify."""

from datetime import date

from apps.clockify.constants import (
    CLOSED_REPORT_CACHE_SECONDS,
    EMPTY_REPORT_CACHE_SECONDS,
    PROJECT_REPORT_CACHE_SECONDS,
)

"""BKD.020.012 - Cache de reportes por estado del proyecto
Un proyecto cuyo rango termino antes de hoy ya no recibe horas nuevas,
asi que su reporte se guarda mucho mas tiempo que el de un activo.
"""


def report_cache_seconds(
    has_entries: bool,
    end_date: date,
    today: date,
) -> int:
    """
    Segundos que se guarda el reporte de un proyecto.

    Args:
        has_entries: Si el reporte trajo registros.
        end_date: Ultimo dia del rango consultado.
        today: Fecha de hoy.

    Returns:
        24 h si el rango ya termino; si no, 6 h con registros o 30 min
        sin ellos.
    """
    if end_date < today:
        return CLOSED_REPORT_CACHE_SECONDS

    if has_entries:
        return PROJECT_REPORT_CACHE_SECONDS

    return EMPTY_REPORT_CACHE_SECONDS
