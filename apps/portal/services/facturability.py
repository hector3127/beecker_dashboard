"""Facturabilidad: horas de GSE contra la capacidad de Recursos."""

import re
from collections.abc import Iterable, Mapping, Sequence
from typing import Any

from apps.capacidad.services.capacity_text import normalize_capacity_text
from apps.portal.constants import (
    DEFAULT_WORKDAY_HOURS,
    FIXED_SERVICE,
    VARIABLE_SERVICES,
)
from apps.portal.schemas import (
    MonthFacturability,
    ResourceRow,
    SpecialtyRow,
)
from apps.portal.services.capacity import count_workdays, format_month
from apps.portal.services.periods import MONTH_ABBREVIATIONS
from apps.portal.services.time_cost import average
from core.utils.numbers import round_half_up_int

"""BKD.120.023 - Facturabilidad
Formula confirmada por el equipo:
- Horas de trabajo fijo: total de horas con servicio AER en GSE.
- Capacidad: total de horas estimadas de todos los recursos (Recursos).
- % fijo: horas AER entre la capacidad.
- HC: horas AER entre las horas facturables de una persona en el mes
  (dias habiles por jornada de 8 h).
Trabajo variable (TYM, IXB, SaaS, RaaS) usa la capacidad que queda
despues del trabajo fijo; lo que sobra es tiempo libre.
"""

NON_ALNUM = re.compile(r"[^A-Z0-9]")
SERVICE_ALIASES = {"TM": "TYM", "TANDM": "TYM", "TIMEANDMATERIAL": "TYM"}
NO_ROLE = "Sin rol"
PERCENT_DECIMALS = 2
BAR_SCALE = 110.0


def normalize_service(value: object) -> str:
    """
    Lleva el servicio a una clave: "T&M" -> "TYM", "RaaS" -> "RAAS".

    Args:
        value: Servicio tal como viene del catalogo de GSE.

    Returns:
        La clave en mayusculas, sin espacios ni simbolos.
    """
    key = NON_ALNUM.sub("", str(value or "").upper())

    return SERVICE_ALIASES.get(key, key)


def person_month_hours(month: str) -> float:
    """Horas facturables de una persona en el mes (dias habiles x 8)."""
    return count_workdays(month) * DEFAULT_WORKDAY_HOURS


def build_month_facturability(
    month: str,
    gse: Mapping[str, Any],
    capacity: Mapping[str, Any],
    error: str = "",
) -> MonthFacturability:
    """
    Calcula la facturabilidad de un mes.

    Args:
        month: Mes YYYY-MM.
        gse: Resultado de gseObtenerMes (base en Sheets).
        capacity: Resultado de capacidadInstaladaBase.
        error: Motivo si alguna fuente no se pudo leer.

    Returns:
        Capacidad, horas, porcentajes, HC y libre del mes.
    """
    hours = _hours_by_service(_detail_rows(gse))
    total_capacity = sum(row["hours"] for row in _capacity_rows(capacity))
    month_hours = person_month_hours(month)
    fixed = hours.get(FIXED_SERVICE, 0.0)
    services = tuple(hours.get(name, 0.0) for name in VARIABLE_SERVICES)
    variable = sum(services)
    variable_capacity = max(total_capacity - fixed, 0.0)
    free = variable_capacity - variable
    global_percent = _percent(fixed + variable, total_capacity)

    return MonthFacturability(
        month=month,
        label=format_month(month).split(" ")[0],
        short_label=MONTH_ABBREVIATIONS[int(month[5:7]) - 1].capitalize(),
        person_hours=month_hours,
        capacity=total_capacity,
        fixed_hours=fixed,
        fixed_percent=_percent(fixed, total_capacity),
        fixed_hc=_headcount(fixed, month_hours),
        variable_capacity=variable_capacity,
        variable_hours=variable,
        variable_percent=_percent(variable, variable_capacity),
        variable_hc=_headcount(variable, month_hours),
        service_hours=services,
        free_hours=free,
        free_fte=_headcount(free, month_hours),
        global_percent=global_percent,
        bar_height=_bar_height(global_percent),
        error=error,
    )


def build_specialties(
    gse: Mapping[str, Any],
    capacity: Mapping[str, Any],
    month: str,
) -> tuple[SpecialtyRow, ...]:
    """
    Facturabilidad del mes por especialidad (ROL de Bandas/rol).

    Args:
        gse: Resultado de gseObtenerMes.
        capacity: Resultado de capacidadInstaladaBase.
        month: Mes YYYY-MM.

    Returns:
        Una fila por especialidad, la de mas personas primero.
    """
    month_hours = person_month_hours(month)
    names: dict[str, str] = {}
    people: dict[str, set[str]] = {}
    caps: dict[str, float] = {}
    fixed: dict[str, float] = {}
    variable: dict[str, float] = {}

    for row in _capacity_rows(capacity):
        key = _register(names, row["role"])
        people.setdefault(key, set()).add(normalize_capacity_text(row["name"]))
        caps[key] = caps.get(key, 0.0) + row["hours"]

    for row in _detail_rows(gse):
        key = _register(names, row["role"])
        target = _target(row["service"], fixed, variable)

        if target is not None:
            target[key] = target.get(key, 0.0) + row["hours"]

    rows = []

    for key, name in names.items():
        capacity_hours = caps.get(key, 0.0)
        fixed_hours = fixed.get(key, 0.0)
        variable_hours = variable.get(key, 0.0)
        variable_capacity = max(capacity_hours - fixed_hours, 0.0)
        rows.append(
            SpecialtyRow(
                name=name,
                headcount=len(people.get(key, set())),
                capacity=capacity_hours,
                fixed_hours=fixed_hours,
                fixed_percent=_percent(fixed_hours, capacity_hours),
                variable_hours=variable_hours,
                variable_percent=_percent(variable_hours, variable_capacity),
                free_fte=_headcount(
                    variable_capacity - variable_hours,
                    month_hours,
                ),
            ),
        )

    return tuple(sorted(rows, key=lambda row: (-row.headcount, row.name)))


def build_resources(
    months: Sequence[tuple[Mapping[str, Any], Mapping[str, Any]]],
) -> tuple[ResourceRow, ...]:
    """
    Facturabilidad de cada persona en cada mes.

    Cada celda es horas facturadas (AER y variable) entre la capacidad de
    la persona (sus horas estimadas en Recursos).

    Args:
        months: (gse, capacidad) de cada mes, en orden.

    Returns:
        Una fila por persona con su porcentaje por mes y su promedio.
    """
    names: dict[str, tuple[str, str]] = {}
    capacity_by_month: list[dict[str, float]] = []
    billed_by_month: list[dict[str, float]] = []

    for gse, capacity in months:
        caps: dict[str, float] = {}
        billed: dict[str, float] = {}

        for row in _capacity_rows(capacity):
            key = normalize_capacity_text(row["name"])
            names.setdefault(key, (row["name"], row["role"]))
            caps[key] = caps.get(key, 0.0) + row["hours"]

        for row in _detail_rows(gse):
            if _is_billable(row["service"]):
                key = normalize_capacity_text(row["name"])
                names.setdefault(key, (row["name"], row["role"]))
                billed[key] = billed.get(key, 0.0) + row["hours"]

        capacity_by_month.append(caps)
        billed_by_month.append(billed)

    rows = []

    for key, (name, role) in names.items():
        percents = tuple(
            _percent(billed.get(key, 0.0), caps.get(key, 0.0))
            for caps, billed in zip(
                capacity_by_month,
                billed_by_month,
                strict=True,
            )
        )
        rows.append(
            ResourceRow(
                name=name,
                role=role,
                percents=percents,
                average=average(percents),
            ),
        )

    return tuple(sorted(rows, key=lambda row: (row.role, row.name)))


def team_averages(
    rows: Sequence[ResourceRow],
    month_count: int,
) -> tuple[tuple[float | None, ...], float | None]:
    """
    Promedio del equipo por mes y promedio general.

    Args:
        rows: Filas por persona.
        month_count: Cantidad de meses.

    Returns:
        (promedio por mes, promedio de los promedios).
    """
    by_month = tuple(
        average(row.percents[index] for row in rows)
        for index in range(month_count)
    )

    return by_month, average(row.average for row in rows)


def _register(names: dict[str, str], role: str) -> str:
    """Clave normalizada de una especialidad, guardando su nombre."""
    label = role or NO_ROLE
    key = normalize_capacity_text(label) or normalize_capacity_text(NO_ROLE)
    names.setdefault(key, label)

    return key


def _target(
    service: str,
    fixed: dict[str, float],
    variable: dict[str, float],
) -> dict[str, float] | None:
    """Acumulador que corresponde al servicio, o None si no se factura."""
    if service == FIXED_SERVICE:
        return fixed

    if service in VARIABLE_SERVICES:
        return variable

    return None


def _is_billable(service: str) -> bool:
    """AER o servicio variable."""
    return service == FIXED_SERVICE or service in VARIABLE_SERVICES


def _hours_by_service(rows: Iterable[dict[str, Any]]) -> dict[str, float]:
    """Suma de horas por servicio normalizado."""
    totals: dict[str, float] = {}

    for row in rows:
        totals[row["service"]] = totals.get(row["service"], 0.0) + row["hours"]

    return totals


def _detail_rows(gse: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Filas de detalle de GSE: persona, area, servicio y horas."""
    raw = gse.get("detalle")

    if not isinstance(raw, list):
        return []

    return [
        {
            "name": _text(item.get("recurso")),
            "role": _text(item.get("area")),
            "service": normalize_service(item.get("servicio")),
            "hours": _number(item.get("horas")),
        }
        for item in raw
        if isinstance(item, dict)
    ]


def _capacity_rows(capacity: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Asignaciones activas de Recursos: persona, rol y horas estimadas."""
    raw = capacity.get("filas")

    if not isinstance(raw, list):
        return []

    return [
        {
            "name": _text(item.get("recurso")),
            "role": _text(item.get("rol")) or _text(item.get("tecnologia")),
            "hours": _number(item.get("horasEstimadas")),
        }
        for item in raw
        if isinstance(item, dict) and item.get("activo") is not False
    ]


def _percent(part: float, total: float) -> float | None:
    """Porcentaje con dos decimales; None si no hay total."""
    if total <= 0:
        return None

    return round(part * 100 / total, PERCENT_DECIMALS)


def _bar_height(percent: float | None) -> float:
    """Alto de la barra (0 a 100) en una escala de 0 a 110%."""
    if percent is None:
        return 0.0

    return round(min(max(percent, 0.0), BAR_SCALE) * 100 / BAR_SCALE, 1)


def _headcount(hours: float, month_hours: float) -> int:
    """Personas equivalentes: horas entre las horas de una persona."""
    if month_hours <= 0:
        return 0

    return round_half_up_int(hours / month_hours)


def _text(value: object) -> str:
    """Texto sin espacios; vacio cuando no hay valor."""
    return "" if value is None else str(value).strip()


def _number(value: object) -> float:
    """Numero; cero cuando no es numerico."""
    if isinstance(value, bool) or not isinstance(value, int | float):
        return 0.0

    return float(value)
