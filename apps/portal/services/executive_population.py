"""Poblacion anual de Operations con las fuentes corregidas del portal."""

from datetime import date, datetime
from typing import Any

from django.core.cache import cache
from django.utils import timezone

from apps.datastore.models import EvaExtraction, EvaScopeSnapshot
from apps.ejecutivo.services.mpb_values import parse_mpb_number
from apps.portal.services.executive_period import bounds, cache_suffix, current
from apps.portal.services.kpi_sources import load_kpi_sources
from core.sheets.factory import build_sheet_repository
from core.sheets.protocols import SheetReader


def azure_scopes():
    """Read the last published Azure inventory, including closed scopes."""
    run = (
        EvaExtraction.objects.filter(
            published=True, metrics__kind="summary_inventory"
        )
        .order_by("-pk")
        .first()
    )
    if run is not None:
        yield from EvaScopeSnapshot.objects.filter(
            source__extraction=run
        ).values_list("row", flat=True)


def population(reader: SheetReader | None = None) -> list[dict[str, Any]]:
    """Incluye proyectos que tuvieron actividad en 2026, aun si ya cerraron."""
    today = timezone.localdate()
    cache_key = (
        "portal:executive-operations:population:v4:"
        + today.isoformat()
        + cache_suffix()
    )
    cached: list[dict[str, Any]] | None = cache.get(cache_key)
    if cached is not None:
        return cached
    reader = reader or build_sheet_repository()
    selected_start, selected_end = bounds()
    sources = load_kpi_sources(reader, today, include_history=False)
    projects: dict[str, dict[str, Any]] = {}

    def add(
        pid: str,
        service: str,
        budget: Any,
        start: date | None,
        end: date | None,
        source: str,
    ) -> None:
        end = min(end or today, today)
        if (
            not start
            or start > end
            or end < selected_start
            or start > selected_end
        ):
            return
        if current():
            start, end = max(start, selected_start), min(end, selected_end)
        projects[pid.casefold()] = {
            "id": pid,
            "service": service,
            "budget": budget,
            "start": start.isoformat(),
            "end": end.isoformat(),
            "source": source,
        }

    for versions in sources.mpb.values():
        eligible = [
            p
            for p in versions
            if p.start_date
            and p.end_date
            and p.start_date.date() <= today
            and p.end_date.date() >= selected_start
            and p.start_date.date() <= selected_end
        ]
        if not eligible:
            continue
        project = max(eligible, key=lambda p: p.start_date or datetime.min)
        if project.start_date is None or project.end_date is None:
            continue  # ya filtrado en eligible; lo pide el tipo
        add(
            project.project_id,
            str(project.service).upper(),
            project.budget_hours,
            project.start_date.date(),
            project.end_date.date(),
            "MPB",
        )

    for row in azure_scopes():
        fields = row.get("fields") or {}
        service = str(fields.get("service") or "").strip().upper()
        if service not in {"IXB", "RAAS", "SAAS"}:
            continue
        pid = str(row.get("project_id") or "").strip()
        start = row.get("iteration_start")
        finish = row.get("iteration_finish")
        if not pid or not start:
            continue
        add(
            pid,
            service,
            parse_mpb_number(row.get("budget")),
            date.fromisoformat(start),
            date.fromisoformat(finish) if finish else None,
            "Azure DevOps",
        )
    result = list(projects.values())
    cache.set(cache_key, result, 300)
    return result
