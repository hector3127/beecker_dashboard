"""Personas vigentes del mes de Bandas/rol sobre las horas de GSE."""

from collections.abc import Mapping, Sequence
from datetime import date
from typing import Any

from django.conf import settings
from django.db.models import Max

from apps.capacidad.services.capacity_text import normalize_capacity_text
from apps.datastore.models import ClockifyMonthSync, ClockifyTimeEntry
from apps.gse.constants import BILLABLE
from apps.gse.services.cells import cell_at, norm, trimmed
from apps.gse.services.roster import find_band_column, read_roster_sheet
from apps.portal.services.capacity_adjustments import (
    PERMANENT,
    apply_capacity_adjustments,
)
from apps.portal.services.capacity_reference import (
    reference_note,
    reference_people,
)
from apps.portal.services.holidays import count_business_days
from core.sheets.protocols import SheetReader

"""BKD.120.025 - Plantilla del mes para Facturabilidad
Capacidad inicial por banda vigente. Las horas facturables de servicios se
conservan aunque una persona no aporte capacidad. Los consumidores anteriores
mantienen la selección de personas con horas.
"""

NO_ROLE = "Sin rol"
ZERO_CAPACITY_BANDS = {"becario", "residente", "producto"}
ZERO_CAPACITY_CODES = {"r", "p"}


def excluded_capacity_rows(sheet: Any, band_column: int) -> set[str]:
    """Personas con tipo explícito de becario, residente o Producto."""
    type_columns = [
        sheet.headers.index(key)
        for key in (
            "tipo recurso",
            "tipo de recurso",
            "tipo",
            "area",
            "departamento",
        )
        if key in sheet.headers
    ]
    name_column = sheet.headers.index("nombre")
    return {
        normalize_capacity_text(cell_at(row, name_column))
        for row in sheet.data_rows
        if norm(cell_at(row, band_column))
        in ZERO_CAPACITY_BANDS | ZERO_CAPACITY_CODES
        or any(
            word in norm(cell_at(row, type_column)).split()
            for type_column in type_columns
            for word in ZERO_CAPACITY_BANDS
        )
    }


def attach_month_roster(
    gse: dict[str, Any],
    reader: SheetReader,
    month: str,
) -> dict[str, Any]:
    """Adjunta la plantilla de Bandas/rol sin depender de Recursos o MPB."""
    sheet = read_roster_sheet(reader, "Bandas/rol requiere Nombre y ROL.")
    column = find_band_column(sheet.headers, int(month[5:7]), month[:4])
    name_column = sheet.headers.index("nombre")
    reference = reference_people(month) if gse.get("capacidadInicial") else None
    if reference is not None:
        included = {
            norm(person["nombre"])
            for person in reference
            if person["capacidad_horas"] > 0
        }
        excluded = {
            person["nombre"]
            for person in reference
            if person["capacidad_horas"] == 0
        }
        excluded.update(
            name
            for row in sheet.data_rows
            if (name := trimmed(cell_at(row, name_column)))
            and norm(name) not in included
        )
        # Preserve Clockify hours for Bandas/rol people absent from GSE.
        known = {norm(person["nombre"]) for person in reference}
        reference.extend(
            {
                "nombre": name,
                "rol": trimmed(cell_at(row, sheet.role_column)),
                "capacidad_horas": 0,
            }
            for row in sheet.data_rows
            if (name := trimmed(cell_at(row, name_column)))
            and norm(name) not in known
        )
        return {
            **gse,
            "plantilla": reference,
            "capacidadHistorica": True,
            "capacidadExcluidos": sorted(excluded, key=str.casefold),
            "plantillaAviso": reference_note(month),
            "plantillaBajas": [],
        }
    if column < 0 and gse.get("capacidadInicial"):
        return {
            **gse,
            "plantilla": [],
            "plantillaAviso": (
                f"Bandas/rol no tiene banda para {month}; "
                "no se puede confirmar la capacidad."
            ),
        }
    if column < 0:
        return {
            **gse,
            "plantillaAviso": (
                f"Bandas/rol no tiene banda para {month}. "
                "Se usan las personas con horas de GSE; "
                "no se conoce la plantilla vigente de ese mes."
            ),
        }
    name_column = sheet.headers.index("nombre")
    role_column = sheet.headers.index("rol")
    people: list[dict[str, Any]] = [
        {
            "nombre": trimmed(cell_at(row, name_column)),
            "rol": trimmed(cell_at(row, role_column)),
        }
        for row in sheet.data_rows
        if norm(cell_at(row, column)) not in ("", "baja", "na", "n a")
        and trimmed(cell_at(row, name_column))
        and trimmed(cell_at(row, role_column))
    ]
    bajas = [
        trimmed(cell_at(row, name_column))
        for row in sheet.data_rows
        if norm(cell_at(row, column)) == "baja"
        and trimmed(cell_at(row, name_column))
    ]
    # Solo una baja explicita del mes siguiente permite inferir un corte.
    year, number = int(month[:4]), int(month[5:])
    next_year, next_month = (
        (year + 1, 1) if number == 12 else (year, number + 1)
    )
    next_column = find_band_column(sheet.headers, next_month, str(next_year))
    if (
        next_year != year
        and next_column >= 0
        and str(next_year) not in sheet.headers[next_column]
    ):
        next_column = -1
    previous_year, previous_month = (
        (year - 1, 12) if number == 1 else (year, number - 1)
    )
    previous_column = find_band_column(
        sheet.headers, previous_month, str(previous_year)
    )
    if (
        previous_year != year
        and previous_column >= 0
        and str(previous_year) not in sheet.headers[previous_column]
    ):
        previous_column = -1
    departures = {
        normalize_capacity_text(cell_at(row, name_column))
        for row in sheet.data_rows
        if next_column >= 0
        and norm(cell_at(row, next_column)) == "baja"
        and norm(cell_at(row, column)) not in ("", "baja", "na", "n a")
    }
    current_departures = {
        normalize_capacity_text(cell_at(row, name_column))
        for row in sheet.data_rows
        if norm(cell_at(row, column)) == "baja"
        and previous_column >= 0
        and norm(cell_at(row, previous_column)) not in ("", "baja", "na", "n a")
    }
    estimates = departure_estimates(
        sheet, month, departures | current_departures
    )
    people.extend(
        {
            "nombre": trimmed(cell_at(row, name_column)),
            "rol": trimmed(cell_at(row, role_column)),
        }
        for row in sheet.data_rows
        if normalize_capacity_text(cell_at(row, name_column))
        in current_departures
        and estimates.get(normalize_capacity_text(cell_at(row, name_column)), 0)
        > 0
    )
    people = [
        {
            **person,
            **(
                {
                    "capacidad_horas": estimates[
                        normalize_capacity_text(person["nombre"])
                    ]
                }
                if normalize_capacity_text(person["nombre"]) in estimates
                else {}
            ),
        }
        for person in people
    ]
    if gse.get("capacidadInicial"):
        excluded = excluded_capacity_rows(sheet, column)
        people = [
            {**person, "capacidad_horas": 0}
            if normalize_capacity_text(person["nombre"]) in excluded
            else person
            for person in people
        ]
    if gse.get("capacidadInicial"):
        people = apply_capacity_adjustments(people, month)
    result = {**gse, "plantilla": people, "plantillaBajas": bajas}
    if gse.get("capacidadInicial"):
        from apps.portal.services.facturability import (
            OPERATIONAL_KEYS,
            role_key,
        )

        included = {
            norm(p["nombre"])
            for p in people
            if role_key(p["rol"]) in OPERATIONAL_KEYS
            and p.get("capacidad_horas", 1) > 0
        }
        result["capacidadExcluidos"] = sorted(
            {
                name
                for row in sheet.data_rows
                if (name := trimmed(cell_at(row, name_column)))
                and norm(name) not in included
            },
            key=str.casefold,
        )
    if (
        gse.get("capacidadInicial")
        and month in ("2026-04", "2026-07")
        and estimates
    ):
        result["plantillaAviso"] = (
            "El calendario mensual está confirmado, pero faltan las fechas "
            "de los descansos internos. "
            "La capacidad de bajas en este mes es provisional."
        )
    return result


def departure_estimates(
    sheet: Any, month: str, departures: set[str]
) -> dict[str, float]:
    """Prorratea bajas confirmadas con el ultimo registro del mes local."""
    if not departures or not settings.CLOCKIFY_STORE_ENABLED:
        return {}
    if not ClockifyMonthSync.objects.filter(
        month=date.fromisoformat(month + "-01")
    ).exists():
        return {}
    rows = (
        ClockifyTimeEntry.objects.filter(
            month=month + "-01", duration_seconds__gt=0
        )
        .exclude(project_id="61d5aa2596aafe5141cd7413")
        .values("user_id", "user_name")
        .annotate(last=Max("entry_date"))
    )
    by_id: dict[str, date] = {}
    by_name: dict[str, date] = {}
    for row in rows:
        if not row["last"]:
            continue
        if row["user_id"]:
            by_id[row["user_id"]] = max(
                by_id.get(row["user_id"], row["last"]), row["last"]
            )
        key = normalize_capacity_text(row["user_name"])
        by_name[key] = max(by_name.get(key, row["last"]), row["last"])
    id_column = (
        sheet.headers.index("id clockify")
        if "id clockify" in sheet.headers
        else -1
    )
    result: dict[str, float] = {}
    for row in sheet.data_rows:
        key = normalize_capacity_text(
            cell_at(row, sheet.headers.index("nombre"))
        )
        if key not in departures:
            continue
        user_id = trimmed(cell_at(row, id_column))
        last = by_id.get(user_id) if user_id else by_name.get(key)
        result[key] = count_business_days(month, last) * 8 if last else 0
    return result


def apply_roster(
    gse: Mapping[str, Any],
    people: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """
    Rehace las areas y el detalle de GSE con las personas vigentes.

    Args:
        gse: Resultado de gseObtenerMes.
        people: Personas vigentes de Bandas/rol (nombre y rol).

    Returns:
        Una copia de GSE con personas vigentes que registraron horas,
        incluidas las no facturables, y su detalle.
    """
    roster: dict[str, tuple[str, str]] = {}

    for person in people:
        name = _text(person.get("nombre"))

        if name:
            roster[normalize_capacity_text(name)] = (
                name,
                _text(person.get("rol")) or NO_ROLE,
            )

    zero_capacity: set[str] = set()
    detail: list[dict[str, Any]] = []
    hours: dict[str, float] = {}
    raw = gse.get("detalle")

    for item in raw if isinstance(raw, list) else []:
        if not isinstance(item, dict):
            continue

        key = normalize_capacity_text(item.get("recurso"))

        if key not in roster:
            categories = item.get("categorias") or []
            if gse.get("capacidadInicial") and BILLABLE in categories:
                detail.append(dict(item))
                zero_capacity.add(key)
            continue

        area = roster[key][1]
        if gse.get("capacidadHistorica"):
            # Clockify detail already uses the role resolved from Bandas/rol.
            override = PERMANENT.get(norm(item.get("recurso")), {}).get("rol")
            area = override or _text(item.get("area")) or NO_ROLE
        detail.append({**item, "area": area})
        amount = item.get("horas")
        hours[key] = hours.get(key, 0.0) + (
            float(amount) if isinstance(amount, int | float) else 0.0
        )

    estimates = {
        normalize_capacity_text(person.get("nombre")): float(
            person["capacidad_horas"]
        )
        for person in people
        if person.get("capacidad_horas") is not None
    }
    estimates.update({key: 0.0 for key in zero_capacity})
    areas: dict[str, dict[str, Any]] = {}

    for key, (name, role) in roster.items():
        if (
            not gse.get("capacidadInicial") and hours.get(key, 0.0) <= 0
        ) or estimates.get(key) == 0:
            continue
        area = areas.setdefault(
            role,
            {"area": role, "recursos": 0, "personas": [], "categorias": []},
        )
        area["recursos"] += 1
        area["personas"].append({"nombre": name, "horas": hours.get(key, 0.0)})

    return {
        **gse,
        "areas": list(areas.values()),
        "detalle": detail,
        "capacidadPorPersona": estimates,
    }


def _text(value: object) -> str:
    """Texto sin espacios; vacio cuando no hay valor."""
    return "" if value is None else str(value).strip()
