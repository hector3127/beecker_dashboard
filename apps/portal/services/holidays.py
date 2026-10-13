"""Dias festivos oficiales de Mexico (Ley Federal del Trabajo, art. 74)."""

import calendar
from datetime import date

"""BKD.120.027 - Festivos de Mexico
Dias de descanso obligatorio que se descuentan de los dias habiles:
1 de enero, primer lunes de febrero, tercer lunes de marzo, 1 de mayo,
16 de septiembre, tercer lunes de noviembre, 25 de diciembre y el 1 de
octubre de cada seis anos (transmision del Poder Ejecutivo: 2024, 2030).
"""

MONDAY = 0
WEEKDAYS_PER_WEEK = 5
FIRST_TRANSMISSION_YEAR = 2024
TRANSMISSION_PERIOD = 6
FEBRUARY = 2
MARCH = 3
NOVEMBER = 11
FIRST = 1
THIRD = 3


def nth_monday(year: int, month: int, nth: int) -> date:
    """
    N-esimo lunes de un mes.

    Args:
        year: Ano.
        month: Mes (1 a 12).
        nth: 1 para el primero, 3 para el tercero.

    Returns:
        La fecha de ese lunes.
    """
    first_day = date(year, month, 1)
    offset = (MONDAY - first_day.weekday()) % 7

    return date(year, month, 1 + offset + (nth - 1) * 7)


def mexican_holidays(year: int) -> frozenset[date]:
    """
    Festivos oficiales de un ano.

    Args:
        year: Ano.

    Returns:
        Las fechas de descanso obligatorio.
    """
    holidays = {
        date(year, 1, 1),
        nth_monday(year, FEBRUARY, FIRST),
        nth_monday(year, MARCH, THIRD),
        date(year, 5, 1),
        date(year, 9, 16),
        nth_monday(year, NOVEMBER, THIRD),
        date(year, 12, 25),
    }

    if (
        year >= FIRST_TRANSMISSION_YEAR
        and (year - FIRST_TRANSMISSION_YEAR) % TRANSMISSION_PERIOD == 0
    ):
        holidays.add(date(year, 10, 1))

    return frozenset(holidays)


def count_business_days(month: str, until: date | None = None) -> int:
    """
    Dias habiles de un mes: lunes a viernes sin festivos.

    Args:
        month: Mes valido YYYY-MM.
        until: Ultimo dia a contar (para el mes en curso); None cuenta el
            mes completo.

    Returns:
        La cantidad de dias habiles.
    """
    year, month_number = int(month[:4]), int(month[5:7])
    last_day = calendar.monthrange(year, month_number)[1]

    if until is not None and (until.year, until.month) == (year, month_number):
        last_day = until.day

    holidays = mexican_holidays(year)

    return sum(
        1
        for day in range(1, last_day + 1)
        if date(year, month_number, day).weekday() < WEEKDAYS_PER_WEEK
        and date(year, month_number, day) not in holidays
    )
