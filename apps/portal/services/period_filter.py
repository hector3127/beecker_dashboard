"""Filtro de periodo (ano, trimestre y mes) de las pantallas de Operations."""

from collections.abc import Callable, Mapping, Sequence
from datetime import date
from urllib.parse import urlencode

from apps.portal.schemas import (
    Period,
    PeriodPicker,
    PickerLink,
    PickerYear,
)
from apps.portal.services.periods import MONTH_ABBREVIATIONS

"""BKD.120.028 - Filtro de periodo
Parametros de la URL (todos opcionales):
- ?periodo=anio&anio=2026
- ?periodo=trimestre&anio=2026&trim=3
- ?periodo=mes&mes=2026-09  (tambien basta ?mes=2026-09)
Sin parametros se usa el mes actual. Un periodo nunca llega mas alla del
mes actual. El selector (estilo Clockify) tiene tres pestanas: Mes (solo
meses), Trimestre (rangos de tres meses) y Ano (solo anos).
"""

KIND_YEAR = "anio"
KIND_QUARTER = "trimestre"
KIND_MONTH = "mes"
KINDS = (KIND_YEAR, KIND_QUARTER, KIND_MONTH)
KIND_LABELS = {
    KIND_YEAR: "Año",
    KIND_QUARTER: "Trimestre",
    KIND_MONTH: "Mes",
}
PERIOD_KEYS = ("periodo", "anio", "trim", "mes")
MONTHS_PER_QUARTER = 3
QUARTERS_PER_YEAR = 4
MONTHS_PER_YEAR = 12
FIRST_YEAR = 2020
YEARS_SHOWN = 3
MONTH_NAMES = (
    "Enero",
    "Febrero",
    "Marzo",
    "Abril",
    "Mayo",
    "Junio",
    "Julio",
    "Agosto",
    "Septiembre",
    "Octubre",
    "Noviembre",
    "Diciembre",
)

Params = Mapping[str, Sequence[str]]


def month_key(year: int, month: int) -> str:
    """Mes como YYYY-MM."""
    return f"{year}-{month:02d}"


def build_period(
    kind: str,
    year: int,
    value: int,
    today: date,
) -> Period:
    """
    Arma un periodo sin pasar del mes actual.

    Args:
        kind: anio, trimestre o mes.
        year: Ano del periodo.
        value: Trimestre (1 a 4) o mes (1 a 12); se ignora para el ano.
        today: Fecha de hoy.

    Returns:
        El periodo con los meses que ya empezaron.
    """
    last_allowed = today.month if year == today.year else MONTHS_PER_YEAR

    if year > today.year:
        year, last_allowed = today.year, today.month

    if kind == KIND_MONTH:
        month = min(max(value, 1), last_allowed)

        return Period(
            kind=kind,
            year=year,
            quarter=0,
            months=(month_key(year, month),),
            label=f"{MONTH_NAMES[month - 1]} {year}",
        )

    if kind == KIND_QUARTER:
        quarter = min(max(value, 1), QUARTERS_PER_YEAR)
        first = (quarter - 1) * MONTHS_PER_QUARTER + 1

        if first > last_allowed:
            quarter = (last_allowed - 1) // MONTHS_PER_QUARTER + 1
            first = (quarter - 1) * MONTHS_PER_QUARTER + 1

        last = min(first + MONTHS_PER_QUARTER - 1, last_allowed)

        return Period(
            kind=kind,
            year=year,
            quarter=quarter,
            months=tuple(month_key(year, m) for m in range(first, last + 1)),
            label=f"T{quarter} {year}",
        )

    return Period(
        kind=KIND_YEAR,
        year=year,
        quarter=0,
        months=tuple(month_key(year, m) for m in range(1, last_allowed + 1)),
        label=str(year),
    )


def parse_period(params: Mapping[str, str], today: date) -> Period:
    """
    Lee el periodo de la URL.

    Args:
        params: Parametros GET (un valor por llave).
        today: Fecha de hoy.

    Returns:
        El periodo elegido; el mes actual si no hay nada valido.
    """
    kind = params.get("periodo", "")
    year = _to_int(params.get("anio", ""), today.year)
    year = min(max(year, FIRST_YEAR), today.year)

    if kind == KIND_YEAR:
        return build_period(KIND_YEAR, year, 0, today)

    if kind == KIND_QUARTER:
        default = (today.month - 1) // MONTHS_PER_QUARTER + 1

        return build_period(
            KIND_QUARTER,
            year,
            _to_int(params.get("trim", ""), default),
            today,
        )

    month_text = params.get("mes", "").strip()
    parts = month_text.split("-")

    if (
        len(parts) == 2
        and parts[0].isdigit()
        and parts[1].isdigit()
        and int(parts[0]) <= today.year
    ):
        return build_period(
            KIND_MONTH,
            max(int(parts[0]), FIRST_YEAR),
            int(parts[1]),
            today,
        )

    return build_period(KIND_MONTH, today.year, today.month, today)


def period_params(period: Period) -> dict[str, str]:
    """Parametros de la URL que describen un periodo."""
    if period.kind == KIND_YEAR:
        return {"periodo": KIND_YEAR, "anio": str(period.year)}

    if period.kind == KIND_QUARTER:
        return {
            "periodo": KIND_QUARTER,
            "anio": str(period.year),
            "trim": str(period.quarter),
        }

    return {"periodo": KIND_MONTH, "mes": period.end_month}


def build_picker(
    period: Period,
    today: date,
    extra: Params,
) -> PeriodPicker:
    """
    Arma las opciones y los enlaces del selector de periodo.

    Args:
        period: Periodo elegido.
        today: Fecha de hoy.
        extra: Otros parametros de la URL que se conservan (areas, etc.).

    Returns:
        El selector con atajos, anos, trimestres y meses.
    """
    kept = [
        (key, value)
        for key, values in extra.items()
        if key not in PERIOD_KEYS
        for value in values
    ]

    def href(params: Mapping[str, str]) -> str:
        return "?" + urlencode(kept + list(params.items()))

    first_year = max(FIRST_YEAR, today.year - YEARS_SHOWN + 1)
    chosen = period_params(period)

    return PeriodPicker(
        label=period.label,
        kind=period.kind,
        kind_label=KIND_LABELS[period.kind],
        years=tuple(
            PickerLink(
                label=str(year),
                href=href({"periodo": KIND_YEAR, "anio": str(year)}),
                active=period.kind == KIND_YEAR and period.year == year,
            )
            for year in range(first_year, today.year + 1)
        ),
        by_year=tuple(
            _year_options(year, period, today, href)
            for year in range(first_year, today.year + 1)
        ),
        hidden=tuple(chosen.items()),
        query="?" + urlencode(chosen),
        reset_href="?" + urlencode(chosen),
    )


def _year_options(
    year: int,
    period: Period,
    today: date,
    href: Callable[[Mapping[str, str]], str],
) -> PickerYear:
    """Trimestres y meses de un ano, con los futuros deshabilitados."""
    return PickerYear(
        year=year,
        active=period.year == year,
        quarters=tuple(
            PickerLink(
                label=f"T{number}",
                href=href(
                    {
                        "periodo": KIND_QUARTER,
                        "anio": str(year),
                        "trim": str(number),
                    },
                ),
                active=(
                    period.kind == KIND_QUARTER
                    and period.year == year
                    and period.quarter == number
                ),
                disabled=_is_future(
                    year, (number - 1) * MONTHS_PER_QUARTER + 1, today
                ),
            )
            for number in range(1, QUARTERS_PER_YEAR + 1)
        ),
        months=tuple(
            PickerLink(
                label=MONTH_ABBREVIATIONS[number - 1].capitalize(),
                href=href(
                    {
                        "periodo": KIND_MONTH,
                        "mes": month_key(year, number),
                    },
                ),
                active=(
                    period.kind == KIND_MONTH
                    and period.end_month == month_key(year, number)
                ),
                disabled=_is_future(year, number, today),
            )
            for number in range(1, MONTHS_PER_YEAR + 1)
        ),
    )


def _is_future(year: int, month: int, today: date) -> bool:
    """El mes todavia no empieza."""
    return (year, month) > (today.year, today.month)


def _to_int(text: str, default: int) -> int:
    """Entero de un texto; el valor por omision si no es un numero."""
    value = text.strip()

    return int(value) if value.isdigit() else default
