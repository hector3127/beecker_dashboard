"""Correcciones mensuales sobre los registros de facturabilidad."""

from dataclasses import asdict
from datetime import date

from django.db import transaction

from apps.capacidad.services.capacity_text import (
    normalize_capacity_text as norm,
)
from apps.datastore.models import ClockifyMonthSync, FacturabilityCorrection
from apps.gse.constants import BILLABLE
from apps.portal.services.facturability import (
    OPERATIONAL_KEYS,
    _bar_height,
    _headcount,
    _percent,
    build_month_facturability,
    build_specialties,
    normalize_service,
    person_month_hours,
    role_key,
)
from apps.portal.services.facturability_closes import (
    GENERAL,
    SPECIALTY,
    publish,
    published_months,
)
from apps.portal.services.roster import apply_roster


def project_key(row):
    """Identifica el grupo que se presenta en el modal."""
    return [
        norm(row.get("recurso")),
        str(row.get("proyecto") or "Sin proyecto"),
        normalize_service(row.get("servicio")),
        role_key(row.get("area") or ""),
        BILLABLE in (row.get("categorias") or []),
    ]


def corrected_source(gse, month, *, strict=False):
    """Aplica las correcciones guardadas en orden de captura."""
    changes = list(
        FacturabilityCorrection.objects.filter(
            month=date.fromisoformat(month + "-01")
        )
        .order_by("pk")
        .values_list("payload", flat=True)
    )
    if not changes:
        return gse
    people = {
        norm(row["nombre"]): dict(row) for row in gse.get("plantilla", [])
    }
    detail = list(gse.get("detalle") or [])
    capacity_changes = {}
    for index, change in enumerate(changes):
        person = change["person"]
        key = norm(person)
        target = change.get("target")
        if change["kind"] == "capacity":
            if strict and index == len(changes) - 1 and key not in people:
                raise ValueError(
                    "La persona no existe en la plantilla del mes."
                )
            if key in people:
                previous = change.get(
                    "previous_hours",
                    people[key].get(
                        "capacidad_horas", person_month_hours(month)
                    ),
                )
                current = change["hours"]
                if previous != current:
                    entry = {"before": previous, "after": current}
                    if change["action"] == "reset":
                        entry["reset"] = True
                    capacity_changes.setdefault(key, []).append(entry)
                people[key]["capacidad_horas"] = current
            continue
        if target:
            remaining = [row for row in detail if project_key(row) != target]
            if (
                strict
                and index == len(changes) - 1
                and len(remaining) == len(detail)
            ):
                raise ValueError(
                    "El registro cambió. Vuelve a consultar el mes."
                )
            detail = remaining
        if change["action"] != "delete":
            people.setdefault(
                key,
                {"nombre": person, "rol": change["role"], "capacidad_horas": 0},
            )
            detail.append(
                {
                    "recurso": person,
                    "area": change["role"],
                    "proyecto": change["project"],
                    "servicio": change["service"],
                    "horas": change["hours"],
                    "categorias": [BILLABLE] if change["billable"] else [],
                }
            )
    roster = list(people.values())
    return {
        **gse,
        "plantilla": roster,
        "detalle": detail,
        "cambiosCapacidad": capacity_changes,
    }


def _metrics(row, divisor, capacity, fixed, variable):
    remaining = max(capacity - fixed, 0)
    return {
        **row,
        "capacity": capacity,
        "fixed_hours": fixed,
        "variable_hours": variable,
        "fixed_percent": _percent(fixed, capacity),
        "variable_percent": _percent(variable, remaining),
        "fixed_hc": _headcount(fixed, divisor),
        "variable_hc": _headcount(variable, divisor),
        "free_fte": _headcount(remaining - variable, divisor),
    }


@transaction.atomic
def save_correction(month, change, author):
    """Registra un cambio y publica la revisión de los cierres afectados."""
    from apps.portal.services.facturability_loader import read_gse_month

    if (
        not ClockifyMonthSync.objects.select_for_update()
        .filter(month=month)
        .first()
    ):
        raise ValueError("El mes requiere una descarga local de Clockify.")
    key = month.isoformat()[:7]
    raw = read_gse_month(key, from_store=True)
    if not raw.get("ok"):
        raise ValueError("No se pudo obtener el detalle del mes.")
    if not isinstance(raw.get("plantilla"), list):
        raise ValueError("No se pudo verificar la plantilla del mes.")
    if (
        change["kind"] == "capacity"
        and change["action"] == "save"
        and not raw.get("capacidadHistorica")
        and change["hours"] > person_month_hours(key)
    ):
        raise ValueError("La capacidad supera las horas laborables del mes.")
    before = corrected_source(raw, key)
    if change["kind"] == "capacity":
        person_key = norm(change["person"])
        person = next(
            (
                row
                for row in before["plantilla"]
                if norm(row["nombre"]) == person_key
            ),
            None,
        )
        if person is None:
            raise ValueError("La persona no existe en la plantilla del mes.")
        previous = person.get("capacidad_horas", person_month_hours(key))
        change = {**change, "previous_hours": previous}
        if change["action"] == "reset":
            history = before.get("cambiosCapacidad", {}).get(person_key, [])
            if not history or history[0]["before"] == previous:
                raise ValueError("La capacidad ya tiene su valor original.")
            change["hours"] = history[0]["before"]
    FacturabilityCorrection.objects.create(
        month=month,
        payload=change,
        author=author,
    )
    after = corrected_source(raw, key, strict=True)
    before, after = (
        apply_roster(source, source.get("plantilla") or [])
        for source in (before, after)
    )
    scope = (OPERATIONAL_KEYS, None)
    old, new = (
        build_month_facturability(key, source, scope=scope)
        for source in (before, after)
    )
    source = "Corrección manual de Facturabilidad"
    general = published_months(GENERAL, [key]).get(key)
    if general:
        capacity = general["capacity"] + new.capacity - old.capacity
        fixed = general["fixed_hours"] + new.fixed_hours - old.fixed_hours
        variable = (
            general["variable_hours"] + new.variable_hours - old.variable_hours
        )
        divisor = general["person_hours"]
        result = _metrics(general, divisor, capacity, fixed, variable)
        remaining = max(capacity - fixed, 0)
        result.update(
            service_hours=[
                value + current - prior
                for value, current, prior in zip(
                    general["service_hours"],
                    new.service_hours,
                    old.service_hours,
                    strict=True,
                )
            ],
            other_hours=general["other_hours"]
            + new.other_hours
            - old.other_hours,
            resources=general["resources"] + new.resources - old.resources,
            variable_capacity=remaining,
            free_hours=remaining - variable,
            global_percent=_percent(fixed + variable, capacity),
            bar_height=_bar_height(_percent(fixed + variable, capacity)),
        )
        publish(key, GENERAL, result, source, revision=True)
    specialty = published_months(SPECIALTY, [key]).get(key)
    if specialty is not None:
        old_rows, new_rows = (
            {
                role_key(row.name): row
                for row in build_specialties(item, key, scope)
            }
            for item in (before, after)
        )
        rows = {role_key(row["name"]): row for row in specialty}
        for role in old_rows.keys() | new_rows.keys():
            prior, current = old_rows.get(role), new_rows.get(role)
            if prior == current:
                continue
            if role not in rows:
                if current:
                    rows[role] = asdict(current)
                continue
            row = rows[role]

            def adjusted(field, row=row, current=current, prior=prior):
                return (
                    row[field]
                    + getattr(current, field, 0)
                    - getattr(prior, field, 0)
                )

            rows[role] = _metrics(
                row,
                new.person_hours,
                adjusted("capacity"),
                adjusted("fixed_hours"),
                adjusted("variable_hours"),
            )
            rows[role]["headcount"] = adjusted("headcount")
        publish(key, SPECIALTY, list(rows.values()), source, revision=True)
