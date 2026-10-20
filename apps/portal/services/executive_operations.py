from core.utils.source_refresh import force_sources

"""Budget, avance y ETC de proyectos con actividad en 2026."""

import hashlib
import threading
from datetime import date

from django.core.cache import cache
from django.utils import timezone

from apps.clockify.provider import build_clockify_loader
from apps.clockify.services.cr_hours import canonical_cr_id
from apps.ejecutivo.services.ixb_rules import calculate_exact_burn
from apps.portal.services.executive_period import bounds, cache_suffix
from apps.portal.services.executive_population import population
from core.sheets.factory import build_sheet_repository

_WARM_LOCK = threading.Lock()

TERMINAL = {
    "completed",
    "completado",
    "finalizado",
    "finished",
    "cancelled",
    "canceled",
    "cancelado",
}


def burn_key(project):
    """Cache por ID exacto y periodo de ejecucion."""
    return (
        "portal:executive-operations:burn:v3:"
        + cache_suffix()
        + hashlib.sha256(
            str(
                (project["id"].casefold(), project["start"], project["end"])
            ).encode()
        ).hexdigest()
    )


def calculate_burn(pid):
    """Lee el consumo con el cargador y las reglas CR existentes."""
    project = next(
        (
            p
            for p in population()
            if p["id"].casefold() == pid.strip().casefold()
        ),
        None,
    )
    if project is None:
        raise ValueError("Proyecto fuera de la poblacion de 2026")
    return _project_burn(project)


def _project_burn(project):
    """Calcula el consumo de un proyecto ya resuelto en la poblacion."""
    result = cache.get(burn_key(project))
    if result is not None and not force_sources.get():
        return result
    reader = build_sheet_repository()
    entries = build_clockify_loader(reader).load_project(
        project["id"],
        (
            date.fromisoformat(project["start"]),
            date.fromisoformat(project["end"]),
        ),
    )
    burn = (
        calculate_exact_burn(entries, canonical_cr_id(project["id"]))
        if project["service"] in {"IXB", "RAAS", "SAAS"}
        else round(
            sum({e.entry_id: e.duration_hours for e in entries}.values()), 2
        )
    )
    metric_entries = {}
    for e in entries:
        identity = e.entry_id or str(
            (e.resource_name, e.started_at, e.duration_hours, e.task_name)
        )
        metric_entries[identity] = {
            "hours": e.duration_hours,
            "billable": e.is_billable,
            "operational": "INV_OPERATIVA"
            in {str(t).strip().upper() for t in e.tags},
        }
    result = {
        "id": project["id"],
        "burn": burn,
        "metric_entries": metric_entries,
    }
    cache.set(
        burn_key(project),
        result,
        86400 if project["end"] < timezone.localdate().isoformat() else 21600,
    )
    return result


def global_facturability(prepare=False):
    """Global billable hours / team capacity for the selected period."""
    from calendar import monthrange
    from apps.portal.services.facturability_loader import (
        load_month_sources,
        peek_month_sources,
    )
    from apps.portal.services.facturability import (
        build_month_facturability,
        default_role_keys,
        list_roles,
    )

    first, last = bounds()
    today = timezone.localdate()
    cutoff = min(last, today)
    months = (
        [
            f"{i // 12:04d}-{i % 12 + 1:02d}"
            for i in range(
                first.year * 12 + first.month - 1,
                cutoff.year * 12 + cutoff.month,
            )
        ]
        if first <= cutoff
        else []
    )
    sources = [
        (load_month_sources(m) if prepare else peek_month_sources(m))
        for m in months
    ]
    roles = default_role_keys(
        list_roles(item.gse for item in sources if item is not None)
    )
    capacity = billable = 0.0
    pending = []
    for month, item in zip(months, sources):
        # GSE aggregates a whole month; never present an exact daily slice from it.
        if (month == first.strftime("%Y-%m") and first.day != 1) or (
            month == cutoff.strftime("%Y-%m")
            and cutoff != today
            and cutoff.day != monthrange(cutoff.year, cutoff.month)[1]
        ):
            pending.append(month)
            continue
        if item is None or item.error or not item.gse:
            pending.append(month)
            continue
        metric = build_month_facturability(
            month, item.gse, item.error, (roles, cutoff)
        )
        capacity += metric.capacity
        billable += metric.fixed_hours + metric.variable_hours
    return {
        "facturability": round(billable / capacity * 100, 2)
        if capacity
        else None,
        "facturability_source": "global_capacity_period_v2",
        "facturability_period": f"{first:%d/%m/%Y} – {last:%d/%m/%Y}",
        "facturability_cutoff": cutoff.isoformat(),
        "facturability_pending_months": pending,
        "facturability_partial": bool(pending or last > today),
        "facturability_billable_hours": round(billable, 2),
        "facturability_capacity": round(capacity, 2),
    }


def operations_summary():
    """Compone presupuesto, avance y ETC desde consumos preparados."""
    projects = population()
    budget = 0
    burn = 0
    paired_budget = 0
    pending = []
    known = 0
    missing_budget = 0
    missing_budget_ids = []
    consumption_projects = 0
    metric_entries = {}
    for project in projects:
        planned = project["budget"]
        if planned is None:
            missing_budget += 1
            missing_budget_ids.append(project["id"])
        else:
            budget += planned
        consumption = cache.get(burn_key(project))
        if consumption is None:
            pending.append(project["id"])
        else:
            consumption_projects += 1
            metric_entries.update(consumption.get("metric_entries", {}))
        if consumption is not None and planned is not None:
            known += 1
            paired_budget += planned
            burn += consumption["burn"]
    total_hours = sum(e["hours"] for e in metric_entries.values())
    billable_hours = sum(
        e["hours"] for e in metric_entries.values() if e["billable"]
    )
    months = max(
        1,
        (bounds()[1].year - bounds()[0].year) * 12
        + bounds()[1].month
        - bounds()[0].month
        + 1,
    )
    result = {
        "facturability": round(billable_hours / total_hours * 100, 2)
        if total_hours and not pending
        else None,
        "investment_operational": round(
            sum(
                e["hours"] for e in metric_entries.values() if e["operational"]
            ),
            2,
        )
        if metric_entries and not pending
        else None,
        "fte": round((paired_budget - burn) / months / 360, 2)
        if known and not pending
        else None,
        "fte_months": months,
        "budget": round(budget, 2),
        "burn": round(burn, 2),
        "advance": round(burn / paired_budget * 100, 2)
        if paired_budget
        else None,
        "etc": round(paired_budget - burn, 2) if known else None,
        "projects": len(projects),
        "known_projects": known,
        "pending_ids": pending,
        "missing_budget": missing_budget,
        "missing_budget_ids": missing_budget_ids,
        "consumption_projects": consumption_projects,
        "partial": bool(pending or missing_budget),
        "year": bounds()[0].year,
    }
    result.update(global_facturability())
    if not result["partial"]:
        cache.set(operations_snapshot_key(), result, 86400)
        cache.set(operations_snapshot_key() + ":fresh", True, 300)
    return result


def warm_operations(only_stale=False):
    """Prepara el componente ejecutivo con dos consultas simultaneas."""
    with _WARM_LOCK:
        if only_stale and cache.get(operations_snapshot_key() + ":fresh"):
            return {"ok": True, "error": ""}
        return _prepare_operations()


def _prepare_operations():
    """Prepara consumos y conserva el ultimo resumen disponible."""
    from core.exceptions import DashboardError
    from core.utils.parallel import map_in_parallel

    def prepare(project):
        try:
            _project_burn(project)
        except (DashboardError, ValueError) as error:
            return project["id"] + ": " + str(error)
        return ""

    failures = [
        e for e in map_in_parallel(prepare, population(), max_workers=2) if e
    ]
    global_facturability(prepare=True)
    summary = operations_summary()
    previous = cached_operations_snapshot()
    if not summary["partial"] or not previous or previous.get("partial"):
        cache.set(operations_snapshot_key(), summary, 86400)
        cache.set(operations_snapshot_key() + ":fresh", True, 300)
    return {"ok": not failures, "error": "; ".join(failures)}


def operations_snapshot_key():
    """Clave del ultimo resumen ejecutivo preparado del dia."""
    return (
        "portal:executive-operations:snapshot:v3:"
        + timezone.localdate().isoformat()
        + cache_suffix()
    )


def cached_operations_snapshot():
    """Devuelve el corte preparado sin leer Sheets ni Clockify."""
    saved = cache.get(operations_snapshot_key()) or {}
    if (
        saved
        and saved.get("facturability_source") != "global_capacity_period_v2"
    ):
        saved = {**saved, **global_facturability()}
    return saved
