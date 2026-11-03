"""Pantalla EVA 1 sin petición ni plantilla: lo que recibe y lo que entrega."""

from datetime import date, datetime
from typing import Any

from django.utils.dateparse import parse_datetime

from apps.datastore.models import EvaExtraction
from apps.portal.services import eva_inventory_view
from apps.portal.services.eva_cut import select_view
from apps.portal.services.summary_dm_totals import dm_totals

SAVED_CUTS_LIMIT = 60


def card_metrics(projects: Any) -> dict[str, Any]:
    """T = en tiempo / TP; C = sobrecosto (avance > 100 %) / TP."""
    total = len(projects)
    in_time = sum(
        p.deviation_days is not None and p.deviation_days <= 0 for p in projects
    )
    over_budget = sum(
        not (p.progress_pending or p.hours_pending or p.budget_pending)
        and p.budget > 0
        and p.progress > 100
        for p in projects
    )
    return {
        "total": total,
        "time_percent": 100 * in_time / total if total else None,
        "cost_percent": 100 * over_budget / total if total else None,
        "in_time": in_time,
        "over_budget": over_budget,
    }


def source_stamp(run: EvaExtraction | None) -> datetime | None:
    """Fecha de observación de la fuente; si falta, cuándo terminó."""
    if run is None:
        return None
    observed = run.metrics.get("source_observed_at")
    return parse_datetime(observed) if observed else run.finished_at


def build_eva1_screen(cut: date, manager: str, service: str) -> dict[str, Any]:
    """Datos de EVA 1 al corte, filtrados por Delivery Manager y servicio."""
    data = eva_inventory_view.load_inventory_eva(cut)
    available = data["eva"]
    selected = select_view(available, manager, service)
    projects = selected.projects
    run = data.get("extraction")
    selected_ids = {p.project_id for p in projects}
    saved_cuts = list(
        EvaExtraction.objects.filter(
            published=True, metrics__kind="summary_inventory"
        )
        .order_by("-cut")
        .values_list("cut", flat=True)
        .distinct()[:SAVED_CUTS_LIMIT]
    )
    return {
        "eva": selected,
        "eva_card_metrics": card_metrics(projects),
        "eva_cost_pending": sum(
            p.progress_pending
            or p.hours_pending
            or p.budget_pending
            or p.budget <= 0
            for p in projects
        ),
        "inventory_totals": dm_totals(
            [
                r
                for r in data["inventory_rows"]
                if r["display_id"] in selected_ids
            ]
        ),
        "monthly_close_state": data.get("monthly_close_state", ""),
        "eva_empty_text": data.get("eva_empty_text", ""),
        "error": "" if run else data.get("error", ""),
        "eva_source_notice": data.get("error", "") if run else "",
        "eva_managers": available.service_rows,
        "eva_services": available.services,
        "eva_available_total": available.total_projects,
        "eva_source_stamp": source_stamp(run),
        "eva_saved_cuts": saved_cuts,
    }
