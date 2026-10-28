"""Facturabilidad con la logica de GSE · Horas por area."""

import re
from collections.abc import Iterable, Mapping, Sequence
from datetime import date
from typing import Any

from apps.capacidad.services.capacity_text import normalize_capacity_text
from apps.portal.constants import (
    DEFAULT_WORKDAY_HOURS,
    FIXED_SERVICE,
    OPERATIONAL_ROLES,
    VARIABLE_SERVICES,
)
from apps.portal.schemas import (
    MonthFacturability,
    ResourceRow,
    SpecialtyRow,
)
from apps.portal.services.capacity import format_month
from apps.portal.services.holidays import count_business_days
from apps.portal.services.periods import MONTH_ABBREVIATIONS
from apps.portal.services.time_cost import average
from core.utils.numbers import round_half_up_int

"""BKD.120.023 - Facturabilidad
Misma logica que la pestana GSE · Horas por area (gseObtenerMes):
- Horas: registros de Clockify con la categoria "Facturable" de GSE.
- Fijo: las facturables del servicio AER; variable: el resto de las
  facturables (TYM, IXB, SaaS, RaaS y, si las hay, otras).
- Capacidad: personas vigentes con horas x dias habiles (lunes a viernes
  sin festivos de Mexico) x 8 h, por area (ROL de Bandas/rol).
- % fijo = fijo / capacidad; % variable = variable / (capacidad - fijo);
  global = facturables / capacidad; HC = horas / horas de una persona.
- Por recurso: facturables de la persona / (dias habiles x 8 h).
Solo las areas operativas: Dev, QA, ROC, Arq, BA y SM en las vistas.
"""

NON_ALNUM = re.compile(r"[^A-Z0-9]")
SERVICE_ALIASES = {"TM": "TYM", "TANDM": "TYM", "TIMEANDMATERIAL": "TYM"}
BILLABLE_KEY = "facturable"
NO_ROLE = "Sin rol"
PERCENT_DECIMALS = 2
BAR_SCALE = 110.0

OPERATIONAL_DISPLAY = {
    normalize_capacity_text(name): label
    for name, label in OPERATIONAL_ROLES.items()
}
OPERATIONAL_KEYS = frozenset(OPERATIONAL_DISPLAY)

Roles = frozenset[str] | None
Scope = tuple[Roles, date | None]


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


def person_month_hours(month: str, today: date | None = None) -> float:
    """
    Horas disponibles de una persona en el mes.

    Args:
        month: Mes YYYY-MM.
        today: Fecha de hoy para contar el mes en curso hasta hoy; None
            cuenta el mes completo (como GSE).

    Returns:
        Dias habiles sin festivos por 8 h.
    """
    return count_business_days(month, today) * DEFAULT_WORKDAY_HOURS


def role_key(role: str) -> str:
    """Clave normalizada de un rol; vacio se toma como "Sin rol"."""
    return normalize_capacity_text(role or NO_ROLE)


def list_roles(months: Iterable[Mapping[str, Any]]) -> tuple[str, ...]:
    """
    Roles (areas de GSE) que aparecen en uno o varios meses.

    Args:
        months: Resultados de gseObtenerMes.

    Returns:
        Los nombres, sin repetir, en orden alfabetico.
    """
    names: dict[str, str] = {}

    for gse in months:
        for area in _areas(gse):
            names.setdefault(role_key(area["name"]), area["name"] or NO_ROLE)

        for row in _detail_rows(gse):
            names.setdefault(role_key(row["role"]), row["role"] or NO_ROLE)

    return tuple(sorted(names.values(), key=str.lower))


def default_role_keys(roles: Iterable[str]) -> frozenset[str]:
    """
    Areas operativas: Dev, QA, ROC, Arq, BA y SM.

    Args:
        roles: Nombres de las areas disponibles.

    Returns:
        Las claves de las areas que se muestran por defecto.
    """
    return frozenset(
        role_key(name) for name in roles if role_key(name) in OPERATIONAL_KEYS
    )


def display_role(name: str) -> str:
    """
    Nombre con el que se muestra un area.

    Args:
        name: Area tal como viene de GSE (QA, R&D...).

    Returns:
        "Dev" para DEV, "Arq" para ARQ, etc.; el mismo nombre si no
        es un area operativa.
    """
    return OPERATIONAL_DISPLAY.get(role_key(name), name or NO_ROLE)


def build_month_facturability(
    month: str,
    gse: Mapping[str, Any],
    error: str = "",
    scope: Scope = (None, None),
) -> MonthFacturability:
    """
    Calcula la facturabilidad de un mes.

    Args:
        month: Mes YYYY-MM.
        gse: Resultado de gseObtenerMes.
        error: Motivo si GSE no se pudo leer.
        scope: (roles a incluir o None para todos, fecha de hoy).

    Returns:
        Capacidad, horas, porcentajes, HC y libre del mes.
    """
    roles, today = scope
    month_hours = person_month_hours(month, today)
    resources = sum(area["resources"] for area in _areas(gse, roles))
    capacity = resources * month_hours
    by_service = _billable_by_service(_detail_rows(gse, roles))
    fixed = by_service.pop(FIXED_SERVICE, 0.0)
    services = tuple(by_service.pop(name, 0.0) for name in VARIABLE_SERVICES)
    other = sum(by_service.values())
    variable = sum(services) + other
    variable_capacity = max(capacity - fixed, 0.0)
    global_percent = _percent(fixed + variable, capacity)

    return MonthFacturability(
        month=month,
        label=format_month(month).split(" ")[0],
        short_label=MONTH_ABBREVIATIONS[int(month[5:7]) - 1].capitalize(),
        person_hours=month_hours,
        capacity=capacity,
        fixed_hours=fixed,
        fixed_percent=_percent(fixed, capacity),
        fixed_hc=_headcount(fixed, month_hours),
        variable_capacity=variable_capacity,
        variable_hours=variable,
        variable_percent=_percent(variable, variable_capacity),
        variable_hc=_headcount(variable, month_hours),
        service_hours=services,
        free_hours=variable_capacity - variable,
        free_fte=_headcount(variable_capacity - variable, month_hours),
        global_percent=global_percent,
        bar_height=_bar_height(global_percent),
        error=error,
        other_hours=other,
        resources=resources,
        notice=_text(gse.get("plantillaAviso")),
    )


def build_specialties(
    gse: Mapping[str, Any],
    month: str,
    scope: Scope = (None, None),
) -> tuple[SpecialtyRow, ...]:
    """
    Facturabilidad del mes por area (ROL de Bandas/rol).

    Args:
        gse: Resultado de gseObtenerMes.
        month: Mes YYYY-MM.
        scope: (roles a incluir o None para todos, fecha de hoy).

    Returns:
        Una fila por area, la de mas personas primero.
    """
    roles, today = scope
    month_hours = person_month_hours(month, today)
    names: dict[str, str] = {}
    people: dict[str, int] = {}
    fixed: dict[str, float] = {}
    variable: dict[str, float] = {}

    for area in _areas(gse, roles):
        key = _register(names, area["name"])
        people[key] = people.get(key, 0) + area["resources"]

    for row in _detail_rows(gse, roles):
        if not row["billable"]:
            continue

        key = _register(names, row["role"])
        target = fixed if row["service"] == FIXED_SERVICE else variable
        target[key] = target.get(key, 0.0) + row["hours"]

    rows = []

    for key, name in names.items():
        capacity = people.get(key, 0) * month_hours
        fixed_hours = fixed.get(key, 0.0)
        variable_hours = variable.get(key, 0.0)
        variable_capacity = max(capacity - fixed_hours, 0.0)
        rows.append(
            SpecialtyRow(
                name=name,
                headcount=people.get(key, 0),
                capacity=capacity,
                fixed_hours=fixed_hours,
                fixed_percent=_percent(fixed_hours, capacity),
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
    months: Sequence[tuple[str, Mapping[str, Any]]],
    scope: Scope = (None, None),
) -> tuple[ResourceRow, ...]:
    """
    Facturabilidad de cada persona en cada mes.

    Igual que la hoja Facturabilidad Mensual: horas facturables de la
    persona entre los dias laborables del mes por 8 h. Una persona vigente
    sin horas tiene 0%; sin datos o fuera de la plantilla queda en blanco.

    Args:
        months: (mes, resultado de gseObtenerMes) de cada mes, en orden.
        scope: (roles a incluir o None para todos, fecha de hoy).

    Returns:
        Una fila por persona con su porcentaje por mes y su promedio.
    """
    roles, today = scope
    names: dict[str, tuple[str, str]] = {}
    by_month: list[tuple[float, dict[str, float]]] = []

    for month, gse in months:
        billed: dict[str, float] = {}

        for area in _areas(gse, roles):
            for person in area["people"]:
                key = normalize_capacity_text(person)
                names.setdefault(key, (person, display_role(area["name"])))
                billed.setdefault(key, 0.0)

        for row in _detail_rows(gse, roles):
            if row["billable"]:
                key = normalize_capacity_text(row["name"])
                names.setdefault(key, (row["name"], display_role(row["role"])))
                billed[key] = billed.get(key, 0.0) + row["hours"]

        by_month.append((person_month_hours(month, today), billed))

    # Solo una baja explícita del mes seleccionado marca el nombre.
    # Ausencia de horas o de banda no significa baja.
    bajas = (
        {
            normalize_capacity_text(name)
            for name in (months[-1][1].get("plantillaBajas") or [])
        }
        if months
        else set()
    )
    roster = months[-1][1].get("plantilla") if months else None
    active = {
        normalize_capacity_text(person.get("nombre"))
        for person in (roster if isinstance(roster, list) else [])
        if isinstance(person, dict) and person.get("nombre")
    }

    rows = [
        ResourceRow(
            name=name,
            role=role,
            percents=(
                percents := tuple(
                    _percent(billed[key], hours) if key in billed else None
                    for hours, billed in by_month
                )
            ),
            average=average(percents),
            inactive=key in bajas,
            roster_status=(
                "baja"
                if key in bajas
                else "activo"
                if key in active
                else "sin_confirmar"
            ),
        )
        for key, (name, role) in names.items()
    ]

    return tuple(sorted(rows, key=lambda row: (row.role, row.name)))


def combine_months(
    months: Sequence[MonthFacturability],
    key: str,
    label: str,
) -> MonthFacturability:
    """
    Junta varios meses (trimestre o ano) en una sola cifra.

    Las horas y la capacidad se suman y los porcentajes se calculan sobre
    esas sumas; el headcount es el promedio de los meses.

    Args:
        months: Meses del periodo, en orden.
        key: Clave del periodo (se guarda en ``month``).
        label: Nombre del periodo (por ejemplo "T3 2026").

    Returns:
        El mismo mes si el periodo es uno solo; si no, el acumulado.
    """
    if len(months) == 1:
        return months[0]

    count = max(len(months), 1)
    capacity = sum(item.capacity for item in months)
    fixed = sum(item.fixed_hours for item in months)
    variable = sum(item.variable_hours for item in months)
    variable_capacity = sum(item.variable_capacity for item in months)
    global_percent = _percent(fixed + variable, capacity)
    errors = dict.fromkeys(item.error for item in months if item.error)
    width = max((len(item.service_hours) for item in months), default=0)

    return MonthFacturability(
        month=key,
        label=label,
        short_label=label,
        person_hours=sum(item.person_hours for item in months) / count,
        capacity=capacity,
        fixed_hours=fixed,
        fixed_percent=_percent(fixed, capacity),
        fixed_hc=_mean_int(item.fixed_hc for item in months),
        variable_capacity=variable_capacity,
        variable_hours=variable,
        variable_percent=_percent(variable, variable_capacity),
        variable_hc=_mean_int(item.variable_hc for item in months),
        service_hours=tuple(
            sum(item.service_hours[index] for item in months)
            for index in range(width)
        ),
        free_hours=sum(item.free_hours for item in months),
        free_fte=_mean_int(item.free_fte for item in months),
        global_percent=global_percent,
        bar_height=_bar_height(global_percent),
        error=" · ".join(errors),
        other_hours=sum(item.other_hours for item in months),
        resources=_mean_int(item.resources for item in months),
    )


def merge_specialties(
    per_month: Sequence[tuple[SpecialtyRow, ...]],
) -> tuple[SpecialtyRow, ...]:
    """
    Junta las especialidades de varios meses.

    Args:
        per_month: Filas por especialidad de cada mes del periodo.

    Returns:
        Una fila por especialidad: capacidad y horas sumadas, porcentajes
        sobre esas sumas y headcount y FTE libre promedio.
    """
    if len(per_month) == 1:
        return per_month[0]

    grouped: dict[str, list[SpecialtyRow]] = {}

    for rows in per_month:
        for row in rows:
            grouped.setdefault(row.name, []).append(row)

    merged = []

    for name, group in grouped.items():
        capacity = sum(row.capacity for row in group)
        fixed = sum(row.fixed_hours for row in group)
        variable = sum(row.variable_hours for row in group)
        variable_capacity = sum(
            max(row.capacity - row.fixed_hours, 0.0) for row in group
        )
        merged.append(
            SpecialtyRow(
                name=name,
                headcount=_mean_int(row.headcount for row in group),
                capacity=capacity,
                fixed_hours=fixed,
                fixed_percent=_percent(fixed, capacity),
                variable_hours=variable,
                variable_percent=_percent(variable, variable_capacity),
                free_fte=_mean_int(row.free_fte for row in group),
            ),
        )

    return tuple(sorted(merged, key=lambda row: (-row.headcount, row.name)))


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
    """Clave normalizada de un area, guardando el nombre que se muestra."""
    key = role_key(role)
    names.setdefault(key, display_role(role))

    return key


def _billable_by_service(rows: Iterable[dict[str, Any]]) -> dict[str, float]:
    """Horas facturables por servicio normalizado."""
    totals: dict[str, float] = {}

    for row in rows:
        if row["billable"]:
            totals[row["service"]] = (
                totals.get(row["service"], 0.0) + row["hours"]
            )

    return totals


def _areas(
    gse: Mapping[str, Any],
    roles: Roles = None,
) -> list[dict[str, Any]]:
    """Areas de GSE: nombre, personas con horas y sus nombres."""
    raw = gse.get("areas")

    if not isinstance(raw, list):
        return []

    areas = []

    for item in raw:
        if not isinstance(item, dict):
            continue

        name = _text(item.get("area"))

        if roles is not None and role_key(name) not in roles:
            continue

        people = item.get("personas")
        areas.append(
            {
                "name": name,
                "resources": int(_number(item.get("recursos"))),
                "people": [
                    _text(person.get("nombre"))
                    for person in (people if isinstance(people, list) else [])
                    if isinstance(person, dict) and _text(person.get("nombre"))
                ],
            },
        )

    return areas


def _detail_rows(
    gse: Mapping[str, Any],
    roles: Roles = None,
) -> list[dict[str, Any]]:
    """Detalle de GSE: persona, area, servicio, si es facturable y horas."""
    raw = gse.get("detalle")

    if not isinstance(raw, list):
        return []

    rows = []

    for item in raw:
        if not isinstance(item, dict):
            continue

        role = _text(item.get("area"))

        if roles is not None and role_key(role) not in roles:
            continue

        categories = item.get("categorias")
        labels = categories if isinstance(categories, list) else []
        rows.append(
            {
                "name": _text(item.get("recurso")),
                "role": role,
                "service": normalize_service(item.get("servicio")),
                "billable": any(
                    normalize_capacity_text(label) == BILLABLE_KEY
                    for label in labels
                ),
                "hours": _number(item.get("horas")),
            },
        )

    return rows


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


def _mean_int(values: Iterable[int]) -> int:
    """Promedio entero (media hacia arriba) de los valores."""
    numbers = list(values)

    if not numbers:
        return 0

    return round_half_up_int(sum(numbers) / len(numbers))


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
