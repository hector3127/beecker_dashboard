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
        "portal:executive-operations:burn:v2:"
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
    if result is not None:
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
    result = {"id": project["id"], "burn": burn}
    cache.set(
        burn_key(project),
        result,
        86400 if project["end"] < timezone.localdate().isoformat() else 21600,
    )
    return result


def operations_summary():
    """Compone presupuesto, avance y ETC desde consumos preparados."""
    projects = population()
    budget = 0
    burn = 0
    paired_budget = 0
    pending = []
    known = 0
    missing_budget = 0
    for project in projects:
        planned = project["budget"]
        if planned is None:
            missing_budget += 1
        else:
            budget += planned
        consumption = cache.get(burn_key(project))
        if consumption is None:
            pending.append(project["id"])
        elif planned is not None:
            known += 1
            paired_budget += planned
            burn += consumption["burn"]
    result = {
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
        "partial": bool(pending or missing_budget),
        "year": bounds()[0].year,
    }
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
    summary = operations_summary()
    previous = cached_operations_snapshot()
    if not summary["partial"] or not previous or previous.get("partial"):
        cache.set(operations_snapshot_key(), summary, 86400)
        cache.set(operations_snapshot_key() + ":fresh", True, 300)
    return {"ok": not failures, "error": "; ".join(failures)}


def operations_snapshot_key():
    """Clave del ultimo resumen ejecutivo preparado del dia."""
    return (
        "portal:executive-operations:snapshot:v2:"
        + timezone.localdate().isoformat()
        + cache_suffix()
    )


def cached_operations_snapshot():
    """Devuelve el corte preparado sin leer Sheets ni Clockify."""
    return cache.get(operations_snapshot_key()) or {}
