"""Clockify extraction for the Summary inventory; exact scopes only."""

import calendar
import re
import time
from datetime import date
from typing import Any

from django.conf import settings

from apps.clockify.constants import REPORT_TIMEZONE
from apps.clockify.services.clockify_client import ClockifyClient
from apps.datastore.services.clockify_store import read_month_rows
from apps.portal.services.inventory_metrics_core import assign_hours
from core.exceptions import DashboardError

Json = dict[str, Any]
CLOCK_ID = re.compile(
    r"^([A-Z]{2,8}(?:\.[A-Z]{1,8})?\.\d+(?:_(?:S\d+|CR\d*(?:_S\d+)?))?)"
    r"(?=$|[^A-Z0-9._])",
    re.I,
)


def extract_hours(
    data: Json,
    projects: list[Any],
    workspace: str,
    synced: frozenset[date],
    cut: date,
) -> Json:
    """Persist exact billable evidence for inventory scopes and date ranges."""
    started = time.perf_counter()
    rows = [
        r
        for r in data["rows"]
        if (not r["fechaInicio"] or r["fechaInicio"] <= cut.isoformat())
    ]
    groups: dict[str, list[Json]] = {}
    for row in rows:
        wanted = row["business_base"] + (
            f"_{row['scope']}" if row["scope"] not in {"", "BASE"} else ""
        )
        exact = [
            p
            for p in projects
            if (m := CLOCK_ID.match(p.name.strip()))
            and m[1].upper()
            in {
                wanted,
                row["idProyecto"],
                f"{row['business_base']}_{row['summary_scope']}",
            }
        ]
        if not exact:
            exact = [
                p
                for p in projects
                if (m := CLOCK_ID.match(p.name.strip()))
                and m[1].upper() == row["business_base"]
            ]
        if (
            len(exact) != 1
            or not row["scope"]
            or not row["fechaInicio"]
            or not row["fechaFin"]
            or row["fechaInicio"] > row["fechaFin"]
        ):
            row["source_issues"].append("clockify_mapping_or_range_pending")
            continue
        row["clockify_project_id"] = exact[0].project_id
        provider_match = CLOCK_ID.match(exact[0].name.strip())
        row["clockify_dedicated_scope"] = bool(
            provider_match and provider_match[1].upper() != row["business_base"]
        )
        groups.setdefault(exact[0].project_id, []).append(row)
    requests, local_months = 0, 0
    evidence: dict[str, list[Json]] = {}
    failures = []
    client = ClockifyClient(settings.CLOCKIFY_API_KEY)
    for provider, selected in groups.items():
        start = min(date.fromisoformat(r["fechaInicio"]) for r in selected)
        end = min(cut, max(date.fromisoformat(r["fechaFin"]) for r in selected))
        entries: list[Json] = []
        try:
            month = start.replace(day=1)
            while month <= end:
                finish = date(
                    month.year,
                    month.month,
                    calendar.monthrange(month.year, month.month)[1],
                )
                local = read_month_rows(provider, month, synced)
                if local is None:
                    fetched, count = client.fetch_detailed_report_counted(
                        workspace,
                        provider,
                        max(start, month),
                        min(end, finish),
                        REPORT_TIMEZONE,
                    )
                    requests += count
                    entries.extend(fetched)
                else:
                    local_months += 1
                    entries.extend(local)
                month = finish.fromordinal(finish.toordinal() + 1)
            if any(
                e.get("taskId")
                and not e.get("taskName")
                and not (e.get("task") or {}).get("name")
                for e in entries
            ):
                tasks = {
                    str(t["id"]): str(t.get("name", ""))
                    for t in client.list_project_tasks(workspace, provider)
                }
                for entry in entries:
                    if not entry.get("taskName"):
                        entry["taskName"] = tasks.get(
                            str(entry.get("taskId")), ""
                        )
            # Closed sibling scopes still prevent untagged hours being
            # attributed to an open scope with an overlapping date range.
            context = selected + [
                dict(r)
                for r in data["rows"]
                if r not in selected
                and r["scope"]
                and (
                    not all(s.get("clockify_dedicated_scope") for s in selected)
                )
            ]
            assign_hours(context, entries, cut)
            evidence[provider] = entries
        except DashboardError:
            failures.append(provider)
            for row in selected:
                row["source_issues"].append("clockify_extraction_failed")
    data.update(
        clockify_seconds=time.perf_counter() - started,
        clockify_requests=requests,
        local_months=local_months,
        clockify_evidence=evidence,
        clockify_failures=failures,
    )
    return data
