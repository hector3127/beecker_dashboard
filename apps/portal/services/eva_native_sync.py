"""Timed, bounded extraction from Azure/Clockify with atomic publication."""

import calendar
import re
import time
from datetime import date
from typing import Any

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from apps.azure_devops.gateway import AzureDevOpsGateway
from apps.clockify.constants import REPORT_TIMEZONE
from apps.clockify.services.clockify_client import ClockifyClient
from apps.datastore.models import (
    EvaAzureSource,
    EvaExtraction,
    EvaScopeSnapshot,
)
from apps.datastore.services.clockify_store import read_month_rows, store_state
from apps.portal.services.eva_azure_source import candidate_rows
from apps.portal.services.eva_native_rows import (
    assign_hours,
    build_row,
    resolve_scope,
)
from core.data_cache import bump_revision
from core.exceptions import DashboardError
from core.utils.parallel import map_in_parallel

Json = dict[str, Any]
BASE_ID = re.compile(r"^([A-Z]{2,8}(?:\.[A-Z])?\.\d+)(?=$|[^A-Z0-9.])", re.I)
CLOCK_ID = re.compile(
    r"^([A-Z]{2,8}(?:\.[A-Z])?\.\d+(?:_(?:S\d+|CR\d*(?:_S\d+)?))?)"
    r"(?=$|[^A-Z0-9._])",
    re.I,
)
SERVICES = {"IXB", "RAAS", "RAAS+", "SAAS", "POC", "IXB Y RAAS"}


def _azure(project: Json, gateway: AzureDevOpsGateway, cut: date) -> Json:
    started = time.perf_counter()
    name = str(project["name"])
    client = gateway.create_client()
    try:
        summary = (
            project
            if "description" in project
            else client.get_project_summary(name)
        )
        match = BASE_ID.match(name)
        assert match is not None
        candidates = candidate_rows(
            match[1], str(summary.get("description") or "")
        )
        candidates = [
            c
            for c in candidates
            if not c["fields"].get("service")
            or c["fields"]["service"].upper() in SERVICES
        ]
        if not candidates:
            return {
                "project": project,
                "skip": True,
                "seconds": time.perf_counter() - started,
            }
        # A missing service cannot place a block in this EVA family. Keep
        # its Summary as evidence; avoid downloading years of unrelated WIs.
        confirmed_family = any(
            c["fields"].get("service", "").upper() in SERVICES
            for c in candidates
        )
        items = client.list_eva_work_items(name) if confirmed_family else []
        iterations = client.list_iterations(name) if confirmed_family else []
        resolved = [
            resolve_scope(c, iterations, candidates) for c in candidates
        ]
        rows = []
        for candidate, scope in zip(candidates, resolved, strict=True):
            if {
                "invalid_project_id",
                "scope_id_mismatch",
                "identity_mismatch",
            } & set(candidate["issues"]):
                scope = ""
            if scope and resolved.count(scope) > 1:
                scope = ""
                candidate["issues"].append("scope_mapping_conflict")
            row = build_row(candidate, scope, items, iterations, cut)
            if scope and candidate["scope"] != "BASE":
                row["idProyecto"] = f"{match[1].upper()}_{scope}"
            row["business_base"] = match[1].upper()
            rows.append(row)
        return {
            "project": project,
            "summary": summary,
            "rows": rows,
            "items": items,
            "iterations": iterations,
            "seconds": time.perf_counter() - started,
            "work_items_requested": confirmed_family,
        }
    except DashboardError:
        return {
            "project": project,
            "failure": "azure_extraction_failed",
            "seconds": time.perf_counter() - started,
        }


def _clockify(
    data: Json,
    projects: list[Any],
    workspace: str,
    synced: frozenset[date],
    cut: date,
) -> Json:
    started = time.perf_counter()
    rows = [
        r
        for r in data["rows"]
        if not r["closed"]
        and r["servicio"] in SERVICES
        and (not r["fechaInicio"] or r["fechaInicio"] <= cut.isoformat())
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
                if r not in selected and r["scope"]
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


def extract_eva(project_names: list[str] | None = None) -> EvaExtraction:
    """Publish a current observed cut; never backdate current Azure states."""
    started = time.perf_counter()
    cut = timezone.localdate()
    run = EvaExtraction.objects.create(
        cut=cut, started_at=timezone.now(), full_inventory=project_names is None
    )
    try:
        gateway = AzureDevOpsGateway()
        catalog_started = time.perf_counter()
        catalog = gateway.create_client().list_summary_projects()
        catalog_seconds = time.perf_counter() - catalog_started
        selected = [
            p
            for p in catalog
            if BASE_ID.match(str(p.get("name", "")))
            and (project_names is None or p["name"] in project_names)
        ]
        if project_names and set(project_names) - {p["name"] for p in selected}:
            raise ValueError("Proyectos solicitados no disponibles en Azure.")
        if not selected:
            raise ValueError(
                "El catálogo Azure no contiene proyectos verificables."
            )
        azure_started = time.perf_counter()
        outcomes = map_in_parallel(
            lambda p: _azure(p, gateway, cut), selected, 4
        )
        azure_seconds = time.perf_counter() - azure_started
        failures = [
            f"{d['project']['name']}: Azure"
            for d in outcomes
            if d.get("failure")
        ]
        usable = [
            d for d in outcomes if not d.get("failure") and not d.get("skip")
        ]
        clock_started = time.perf_counter()
        client = ClockifyClient(settings.CLOCKIFY_API_KEY)
        workspace = settings.CLOCKIFY_WORKSPACE_ID
        if not workspace:
            raise ValueError("Falta configurar el workspace de Clockify.")
        projects = client.list_projects(workspace)
        stamp, months = store_state()
        # Do not treat an old copy of the current month as a live extraction.
        today_month = cut.replace(day=1)
        months = frozenset(m for m in months if m < today_month)
        usable = map_in_parallel(
            lambda d: _clockify(d, projects, workspace, months, cut), usable, 4
        )
        clock_seconds = time.perf_counter() - clock_started
        failures.extend(
            f"{d['project']['name']}: Clockify"
            for d in usable
            if d["clockify_failures"]
        )
        issues = [
            f"{r['idProyecto']}: {', '.join(r['source_issues'])}"
            for d in usable
            for r in d["rows"]
            if r["source_issues"] and not r["closed"]
        ]
        metrics = {
            "azure_work_item_projects": sum(
                bool(d.get("work_items_requested")) for d in usable
            ),
            "quarantined_summary_projects": sum(
                not d.get("work_items_requested", False) for d in usable
            ),
            "catalog_seconds": round(catalog_seconds, 3),
            "azure_seconds": round(azure_seconds, 3),
            "clockify_seconds": round(clock_seconds, 3),
            "projects": len(selected),
            "scopes": sum(len(d["rows"]) for d in usable),
            "clockify_report_requests": sum(
                d["clockify_requests"] for d in usable
            ),
            "clockify_local_months": sum(d["local_months"] for d in usable),
            "clockify_store_stamp": stamp,
        }
        persist_started = time.perf_counter()
        with transaction.atomic():
            for data in usable:
                source = EvaAzureSource.objects.create(
                    extraction=run,
                    azure_id=str(
                        data["project"].get("id") or data["project"]["name"]
                    ),
                    name=data["project"]["name"],
                    payload={
                        "summary": data["summary"],
                        "iterations": data["iterations"],
                        "work_items": data["items"],
                        "clockify": data["clockify_evidence"],
                    },
                    metrics={
                        "azure_seconds": round(data["seconds"], 3),
                        "clockify_seconds": round(data["clockify_seconds"], 3),
                    },
                )
                EvaScopeSnapshot.objects.bulk_create(
                    [
                        EvaScopeSnapshot(
                            source=source,
                            project_id=r["idProyecto"],
                            scope=r["summary_scope"],
                            closed=r["closed"],
                            row=r,
                        )
                        for r in data["rows"]
                    ]
                )
            metrics["persist_seconds"] = round(
                time.perf_counter() - persist_started, 3
            )
            metrics["total_seconds"] = round(time.perf_counter() - started, 3)
            run.metrics, run.issues, run.finished_at = (
                metrics,
                failures + issues,
                timezone.now(),
            )
            run.published = not failures
            run.save()
            if run.published and run.full_inventory:
                bump_revision()
        return run
    except Exception as error:
        run.finished_at = timezone.now()
        run.issues = ["Extracción interrumpida: " + type(error).__name__]
        run.metrics = {"total_seconds": round(time.perf_counter() - started, 3)}
        run.save(update_fields=["finished_at", "issues", "metrics"])
        raise
