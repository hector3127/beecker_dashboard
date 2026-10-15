"""Poblacion anual de Operations con las fuentes corregidas del portal."""

from datetime import datetime

from django.core.cache import cache
from django.utils import timezone

from apps.ejecutivo.services.ixb_rules import (
    HISTORY_START_COLUMNS,
    read_history_date,
    read_history_status,
)
from apps.ejecutivo.services.mpb_values import parse_mpb_number
from apps.portal.services.executive_period import bounds, cache_suffix, current
from apps.portal.services.kpi_sources import (
    load_kpi_sources,
    operational_period,
    value,
)
from core.sheets.factory import build_sheet_repository
from core.sheets.project_year import mpb_previous_year_ids


def population(reader=None):
    """Incluye proyectos que tuvieron actividad en 2026, aun si ya cerraron."""
    today = timezone.localdate()
    cache_key = (
        "portal:executive-operations:population:v3:"
        + today.isoformat()
        + cache_suffix()
    )
    cached = cache.get(cache_key)
    if cached is not None:
        return cached
    reader = reader or build_sheet_repository()
    selected_start, selected_end = bounds()
    sources = load_kpi_sources(reader, today)
    projects = {}

    def add(pid, service, budget, start, end, source):
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
        add(
            project.project_id,
            str(project.service).upper(),
            project.budget_hours,
            project.start_date.date(),
            project.end_date.date(),
            "MPB",
        )

    for pid, rows in sources.events.items():
        meta = sources.metadata[pid.casefold()]
        service = str(value(meta, "Service", "Servicio")).upper().strip()
        if service not in {"IXB", "RAAS", "SAAS"}:
            continue
        starts = [
            day
            for row in rows
            if read_history_status(row) == "DISCOVERY OP"
            and (day := read_history_date(row, HISTORY_START_COLUMNS))
        ]
        if not starts:
            starts = [
                day
                for row in rows
                if read_history_status(row)
                in {"DISCOVERY", "DEVELOPMENT", "DEPLOYMENT"}
                and (day := read_history_date(row, HISTORY_START_COLUMNS))
            ]
        if not starts:
            continue
        period = operational_period(rows, pid, min(starts))
        if period.active and period.start:
            add(
                pid,
                service,
                parse_mpb_number(value(meta, "Budget_Hrs")),
                period.start.date(),
                period.finish.date() if period.finish else today,
                "Historico_Proyectos A:J",
            )
    excluded = (
        mpb_previous_year_ids(reader, selected_start.year)
        if selected_start.year == selected_end.year
        else set()
    )
    result = [p for pid, p in projects.items() if pid not in excluded]
    cache.set(cache_key, result, 300)
    return result
