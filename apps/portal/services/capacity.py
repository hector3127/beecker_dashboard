"""Pantalla de Capacidad instalada: asignaciones y capacidad base."""

import calendar
import csv
import io
import re
from collections.abc import Mapping, Sequence
from datetime import date
from typing import Any

from apps.capacidad.constants import MONTH_NAMES
from apps.capacidad.services.capacity_text import normalize_capacity_text
from apps.portal.constants import (
    DEFAULT_WORKDAY_HOURS,
    MAX_WORKDAY_HOURS,
    WEEKDAYS_PER_WEEK,
)
from apps.portal.schemas import CapacityFilters, CapacityRow, CapacityView

"""BKD.120.015 - Capacidad instalada del portal
Arma la pantalla con las asignaciones del mes que ya calcula
apps/capacidad (Recursos + Bandas/rol + MPB): recursos, capacidad base
(dias habiles por jornada) y horas diarias asignadas. Las horas reales de
Clockify y Azure DevOps se quedan en el panel anterior.
"""

MONTH_FORMAT = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")
CSV_HEADER = (
    "Recurso",
    "Banda",
    "Concepto",
    "Tecnologia",
    "Delivery Manager",
    "ID proyecto",
    "Proyecto",
    "Horas diarias",
    "Horas estimadas",
    "Cargable",
    "Facturable",
    "Afecta capacidad",
)


def normalize_month(text: str, today: date) -> str:
    """
    Valida el mes de la URL.

    Args:
        text: Valor recibido, esperado como YYYY-MM.
        today: Fecha local de hoy.

    Returns:
        El mismo mes si es valido; si no, el mes actual.
    """
    value = text.strip()

    if MONTH_FORMAT.match(value):
        return value

    return today.strftime("%Y-%m")


def parse_workday_hours(text: str) -> float:
    """
    Lee la jornada diaria escrita por el usuario.

    Args:
        text: Valor recibido (puede venir vacio o con letras).

    Returns:
        Las horas, o 8 cuando el valor no es un numero entre 1 y 24.
    """
    try:
        hours = float(text.strip().replace(",", "."))
    except ValueError:
        return DEFAULT_WORKDAY_HOURS

    if 0 < hours <= MAX_WORKDAY_HOURS:
        return hours

    return DEFAULT_WORKDAY_HOURS


def count_workdays(month: str) -> int:
    """
    Cuenta los dias de lunes a viernes de un mes (sin feriados).

    Args:
        month: Mes valido YYYY-MM.

    Returns:
        La cantidad de dias habiles.
    """
    year, month_number = int(month[:4]), int(month[5:7])
    days_in_month = calendar.monthrange(year, month_number)[1]

    return sum(
        1
        for day in range(1, days_in_month + 1)
        if date(year, month_number, day).weekday() < WEEKDAYS_PER_WEEK
    )


def format_month(month: str) -> str:
    """
    Escribe el mes con letras.

    Args:
        month: Mes valido YYYY-MM.

    Returns:
        "Octubre 2026".
    """
    return f"{MONTH_NAMES[int(month[5:7]) - 1].capitalize()} {month[:4]}"


def build_capacity_view(
    data: Mapping[str, Any],
    filters: CapacityFilters,
) -> CapacityView:
    """
    Arma la pantalla a partir de las asignaciones del mes.

    Args:
        data: Resultado correcto de capacidadInstaladaBase().
        filters: Mes, jornada y filtros elegidos.

    Returns:
        Los totales, las opciones de filtro y las filas visibles.
    """
    all_rows = _read_rows(data.get("filas"))
    visible = [row for row in all_rows if _matches(row, filters)]
    names = {row.resource for row in visible}
    totals: dict[str, float] = {}

    for row in visible:
        if _counts_as_assigned(row):
            totals[row.resource] = (
                totals.get(row.resource, 0.0) + row.daily_hours
            )

    workdays = count_workdays(filters.month)

    return CapacityView(
        month=filters.month,
        month_label=format_month(filters.month),
        workdays=workdays,
        workday_hours=filters.workday_hours,
        resources=len(names),
        base_hours=len(names) * workdays * filters.workday_hours,
        assigned_daily_hours=sum(totals.values()),
        over_workday=sum(
            1 for hours in totals.values() if hours > filters.workday_hours
        ),
        rows=tuple(visible),
        technologies=tuple(sorted({row.technology for row in all_rows})),
        concepts=tuple(sorted({row.concept for row in all_rows})),
        band_notice=_text(data.get("bandasAviso")),
        band_column=_text(data.get("bandaColumna")),
    )


def build_capacity_csv(rows: Sequence[CapacityRow]) -> str:
    """
    Escribe las asignaciones visibles como CSV.

    Args:
        rows: Filas de la pantalla.

    Returns:
        El texto CSV con encabezado.
    """
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(CSV_HEADER)

    for row in rows:
        writer.writerow(
            (
                row.resource,
                row.band,
                row.concept,
                row.technology,
                row.manager,
                row.project_id,
                row.project,
                row.daily_hours,
                row.estimated_hours,
                _yes_no(row.chargeable, row.has_rule),
                _yes_no(row.billable, row.has_rule),
                _yes_no(row.affects_capacity, row.has_rule),
            ),
        )

    return buffer.getvalue()


def _yes_no(value: bool, has_rule: bool) -> str:
    """Si/No, o vacio cuando el concepto no tiene regla."""
    if not has_rule:
        return ""

    return "Si" if value else "No"


def _counts_as_assigned(row: CapacityRow) -> bool:
    """Las horas cuentan salvo en conceptos que no afectan capacidad."""
    return row.affects_capacity or not row.has_rule


def _matches(row: CapacityRow, filters: CapacityFilters) -> bool:
    """Indica si una fila cumple los filtros."""
    if filters.technology and row.technology != filters.technology:
        return False

    if filters.concept and row.concept != filters.concept:
        return False

    search = normalize_capacity_text(filters.search)

    if not search:
        return True

    haystack = normalize_capacity_text(
        " ".join(
            (row.resource, row.project, row.project_id, row.manager),
        ),
    )

    return search in haystack


def _read_rows(raw_rows: object) -> list[CapacityRow]:
    """Convierte las filas activas del resultado de apps/capacidad."""
    if not isinstance(raw_rows, list):
        return []

    return [
        _read_row(raw)
        for raw in raw_rows
        if isinstance(raw, dict) and raw.get("activo") is not False
    ]


def _read_row(raw: Mapping[str, Any]) -> CapacityRow:
    """Convierte una fila del resultado en CapacityRow."""
    rule = raw.get("regla")
    rule_data = rule if isinstance(rule, dict) else {}

    return CapacityRow(
        resource=_text(raw.get("recurso")),
        band=_text(raw.get("banda")),
        concept=_text(raw.get("concepto")),
        technology=_text(raw.get("tecnologia")),
        manager=_text(raw.get("manager")),
        project_id=_text(raw.get("idProyecto")),
        project=_text(raw.get("proyecto")),
        daily_hours=_number(raw.get("horasDiarias")),
        estimated_hours=_number(raw.get("horasEstimadas")),
        has_rule=bool(rule_data),
        chargeable=rule_data.get("cargabilidad") == "Cargable",
        billable=rule_data.get("facturable") == "Facturable",
        affects_capacity=rule_data.get("afecta") is True,
    )


def _text(value: object) -> str:
    """Texto sin espacios; vacio cuando no hay valor."""
    return "" if value is None else str(value).strip()


def _number(value: object) -> float:
    """Numero de la hoja; cero cuando no es numerico."""
    if isinstance(value, bool) or not isinstance(value, int | float):
        return 0.0

    return float(value)
