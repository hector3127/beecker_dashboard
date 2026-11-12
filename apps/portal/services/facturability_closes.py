"""Cierres publicados y agregación por especialidad."""

from collections.abc import Iterable
from dataclasses import replace
from datetime import date

from django.db import transaction

from apps.datastore.models import FacturabilityClose
from apps.portal.schemas import SpecialtyRow
from apps.portal.services.facturability import (
    build_month_facturability,
    role_key,
)

GENERAL = "general"
SPECIALTY = "especialidad"
QUARTER_HOURS = {"2026-01": 488, "2026-04": 488, "2026-07": 480}
LAB_START = "2026-08"
LAB_KEYS = frozenset(role_key(name) for name in ("Lab IA", "R&D"))


def published_months(view: str, months: Iterable[str]) -> dict:
    """Obtiene la última revisión publicada de cada mes en una consulta."""
    result = {}
    starts = [date.fromisoformat(f"{month}-01") for month in months]
    for row in FacturabilityClose.objects.filter(
        view=view, month__in=starts
    ).order_by("month", "revision"):
        result[row.month.isoformat()[:7]] = row.metrics
    return result


@transaction.atomic
def publish(month: str, view: str, metrics, source: str, *, revision=False):
    """Publica de forma idempotente y conserva cada versión anterior."""
    key = {"month": date.fromisoformat(f"{month}-01"), "view": view}
    previous = (
        FacturabilityClose.objects.select_for_update()
        .filter(**key)
        .order_by("-revision")
        .first()
    )
    if previous and (previous.metrics == metrics or not revision):
        return False
    FacturabilityClose.objects.create(
        **key,
        metrics=metrics,
        source=source,
        revision=previous.revision + 1 if previous else 1,
    )
    return True


def general_metric(month: str, metrics: dict):
    """Reconstruye el indicador general desde el cierre."""
    return replace(
        build_month_facturability(month, {}),
        **{**metrics, "service_hours": tuple(metrics["service_hours"])},
    )


def percentage(hours: float, capacity: float) -> float | None:
    """Calcula el porcentaje sin redondear."""
    return hours * 100 / capacity if capacity else None


def specialty_metric(name, capacity, headcount, fixed, variable, divisor):
    """Calcula los indicadores equivalentes con el divisor del periodo."""
    fixed_hc = fixed / divisor if divisor else 0
    variable_hc = variable / divisor if divisor else 0
    return SpecialtyRow(
        name=name,
        capacity=capacity,
        headcount=headcount,
        fixed_hours=fixed,
        variable_hours=variable,
        fixed_percent=percentage(fixed, capacity),
        variable_percent=percentage(variable, capacity - fixed),
        fixed_hc=fixed_hc,
        variable_hc=variable_hc,
        free_fte=headcount - fixed_hc - variable_hc,
    )


def specialty_rows(month: str, metrics: list[dict], roles=None):
    """Recupera las especialidades publicadas que pide la vista."""
    rows = []
    for metric in metrics:
        row = SpecialtyRow(**metric)
        if roles is not None and role_key(row.name) not in roles:
            continue
        if month >= LAB_START and role_key(row.name) in LAB_KEYS:
            row = replace(
                row,
                capacity=0,
                headcount=0,
                fixed_hours=0,
                variable_hours=0,
                fixed_percent=0,
                variable_percent=0,
                fixed_hc=0,
                variable_hc=0,
                free_fte=0,
            )
        rows.append(row)
    return tuple(rows)


def specialty_total(rows, divisor, months_count=1, name="Total"):
    """Suma horas y calcula equivalentes del grupo."""
    return specialty_metric(
        name,
        sum(row.capacity for row in rows),
        sum(row.headcount for row in rows) / months_count,
        sum(row.fixed_hours for row in rows),
        sum(row.variable_hours for row in rows),
        divisor,
    )


def aggregate_specialties(monthly, divisor):
    """Agrupa los cierres mensuales conservando su precisión."""
    groups = {}
    for rows in monthly:
        for row in rows:
            groups.setdefault(row.name, []).append(row)
    return tuple(
        specialty_zero_lab()
        if role_key(name) in LAB_KEYS
        and all(
            row.capacity
            == row.headcount
            == row.fixed_hours
            == row.variable_hours
            == 0
            for row in rows
        )
        else specialty_total(rows, divisor, len(monthly), name)
        for name, rows in groups.items()
    )


def specialty_zero_lab():
    """Presenta Lab IA con cero aportaciones a Operaciones."""
    return replace(
        specialty_metric("Lab IA", 0, 0, 0, 0, 1),
        fixed_percent=0,
        variable_percent=0,
    )


def specialty_selected(keys, monthly, label):
    """Totales de la vista por especialidad con sus propios cierres."""
    from apps.portal.services.facturability import (
        combine_months,
        person_month_hours,
    )

    metrics = []
    for key in keys:
        divisor = person_month_hours(key)
        total = specialty_total(monthly[key], divisor)
        free = total.capacity - total.fixed_hours - total.variable_hours
        metrics.append(
            replace(
                build_month_facturability(key, {}),
                capacity=total.capacity,
                fixed_hours=total.fixed_hours,
                variable_hours=total.variable_hours,
                fixed_percent=total.fixed_percent,
                variable_percent=total.variable_percent,
                fixed_hc=total.fixed_hc,
                variable_hc=total.variable_hc,
                variable_capacity=total.capacity - total.fixed_hours,
                free_hours=free,
                free_fte=free / divisor if divisor else 0,
                resources=total.headcount,
            )
        )
    return combine_months(metrics, label, label)


def parse_specialty_range(params, today: date) -> list[str]:
    """Rango inclusivo de meses completos o en curso."""
    import re

    first, last = params.get("desde", ""), params.get("hasta", "")
    if not all(
        re.fullmatch(r"[0-9]{4}-(0[1-9]|1[0-2])", value)
        for value in (first, last)
    ):
        return []
    if not "2025-12" <= first <= last <= today.isoformat()[:7]:
        return []
    result = []
    year, month = int(first[:4]), int(first[5:])
    while (key := f"{year:04d}-{month:02d}") <= last:
        result.append(key)
        year, month = (year + 1, 1) if month == 12 else (year, month + 1)
    return result
