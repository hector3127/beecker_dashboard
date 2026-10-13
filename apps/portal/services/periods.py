"""Trimestre en curso para las pantallas del portal."""

import calendar
from datetime import date

from apps.portal.schemas import PeriodLabel

"""BKD.120.007 - Periodo del portal
Calcula el trimestre calendario actual y lo escribe como en el diseno:
01-jul-2026 -> 30-sep-2026.
"""

MONTH_ABBREVIATIONS = (
    "ene",
    "feb",
    "mar",
    "abr",
    "may",
    "jun",
    "jul",
    "ago",
    "sep",
    "oct",
    "nov",
    "dic",
)

MONTHS_PER_QUARTER = 3


def format_date(value: date) -> str:
    """
    Escribe una fecha como 01-jul-2026.

    Args:
        value: Fecha a escribir.

    Returns:
        La fecha con el mes abreviado en espanol.
    """
    month = MONTH_ABBREVIATIONS[value.month - 1]

    return f"{value.day:02d}-{month}-{value.year}"


def current_quarter(today: date) -> PeriodLabel:
    """
    Calcula el trimestre calendario que contiene a una fecha.

    Args:
        today: Fecha de referencia.

    Returns:
        Primer y ultimo dia del trimestre, ya escritos.
    """
    quarter_index = (today.month - 1) // MONTHS_PER_QUARTER
    first_month = quarter_index * MONTHS_PER_QUARTER + 1
    last_month = first_month + MONTHS_PER_QUARTER - 1
    last_day = calendar.monthrange(today.year, last_month)[1]

    return PeriodLabel(
        start=format_date(date(today.year, first_month, 1)),
        end=format_date(date(today.year, last_month, last_day)),
    )
