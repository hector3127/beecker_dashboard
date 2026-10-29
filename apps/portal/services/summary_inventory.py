"""Local Summary inventory, independent of EVA eligibility and cuts."""

import re
import time
from datetime import date
from typing import Any

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from apps.azure_devops.gateway import AzureDevOpsGateway
from apps.clockify.services.clockify_client import ClockifyClient
from apps.datastore.models import (
    AzureHistoryFeed,
    EvaAzureSource,
    EvaExtraction,
    EvaScopeSnapshot,
)
from apps.datastore.services.clockify_store import store_state
from apps.portal.services.azure_history import attach_history, feed_identity
from apps.portal.services.eva_azure_source import BUSINESS_ID, candidate_rows
from apps.portal.services.summary_eva_metrics import at_cut, enrich
from apps.portal.services.summary_iterations import (
    calendar_fields,
    iteration_blocks,
)
from core.exceptions import DashboardError
from core.utils.parallel import map_in_parallel


def extract_summaries(
    *, from_local: bool = False, with_eva: bool = True
) -> EvaExtraction:
    """Store every PAT-visible project, without service or closure filters."""
    started = time.perf_counter()
    previous = (
        EvaExtraction.objects.filter(
            published=True, metrics__kind="summary_inventory"
        )
        .order_by("-pk")
        .first()
        if from_local
        else None
    )
    if from_local and previous is None:
        raise ValueError("No hay un inventario local para reprocesar.")
    run = EvaExtraction.objects.create(
        cut=timezone.localdate(),
        started_at=timezone.now(),
        metrics={"kind": "summary_inventory"},
    )
    try:
        gateway = None if from_local else AzureDevOpsGateway()
        if from_local:
            catalog = [
                s.payload["summary"]
                for s in EvaAzureSource.objects.filter(extraction=previous)
            ]
        else:
            assert gateway is not None
            catalog = gateway.create_client().list_summary_projects()
        clock_context = None
        if with_eva and not from_local:
            try:
                workspace = settings.CLOCKIFY_WORKSPACE_ID
                client = ClockifyClient(settings.CLOCKIFY_API_KEY)
                _, months = store_state()
                clock_context = (
                    client.list_projects(workspace),
                    workspace,
                    frozenset(m for m in months if m < run.cut.replace(day=1)),
                )
            except DashboardError:
                pass

        def read(
            project: dict[str, Any],
        ) -> tuple[dict[str, Any], dict[str, Any], list[dict[str, Any]]]:
            summary = project
            if "description" not in project and gateway is not None:
                summary = gateway.create_client().get_project_summary(
                    project["id"]
                )
            name = str(project["name"])
            match = BUSINESS_ID.match(name.upper())
            base = match[0].split("_", 1)[0] if match else name
            rows = candidate_rows(base, str(summary.get("description") or ""))
            # User rule: / SPRNT 1 (or SPRINT 1) on a change-request
            # heading is redundant. Preserve its original parsed identity.
            for row in rows:
                if match_scope := re.fullmatch(r"(CR\d*)_S1", row["scope"]):
                    row.update(
                        summary_scope=row["scope"],
                        scope=match_scope[1],
                        project_id=f"{base}_{match_scope[1]}",
                        scope_link_evidence="user_rule_ignore_cr_sprint1",
                    )
            try:
                if from_local:
                    tree = project.get("iteration_tree", {})
                    iteration_error = project.get("iteration_error", "")
                else:
                    assert gateway is not None
                    tree = gateway.create_client().get_iteration_tree(
                        project["id"]
                    )
                    iteration_error = ""
            except DashboardError:
                tree, iteration_error = {}, "iteration_extraction_failed"
            summary = {
                **summary,
                "iteration_tree": tree,
                "iteration_error": iteration_error,
            }
            blocks = iteration_blocks(tree)
            # Some trees call the first change request CR, while Summary
            # calls it CR1. Require matching dates and no competing identity.
            first_cr = [r for r in rows if r["scope"] == "CR1"]
            if (
                len(first_cr) == 1
                and "CR" in blocks
                and "CR1" not in blocks
                and not any(r["scope"] == "CR" for r in rows)
            ):
                dates = calendar_fields(blocks["CR"], run.cut)
                row = first_cr[0]
                if (
                    row.get("start")
                    and row.get("finish")
                    and row["start"] == dates["iteration_start"]
                    and row["finish"] == dates["iteration_finish"]
                ):
                    row.setdefault("summary_scope", row["scope"])
                    row.update(
                        scope="CR",
                        project_id=f"{base}_CR",
                        scope_link_evidence="unique_first_cr_matching_dates",
                    )
            known = {r["scope"] for r in rows}
            for code in blocks.keys() - known:
                candidate = candidate_rows(base, "")[0]
                candidate.update(
                    scope=code,
                    project_id=f"{base}_{code}" if code != "BASE" else base,
                )
                candidate["issues"].append("iteration_only_block")
                rows.append(candidate)
            for row in rows:
                row.update(
                    calendar_fields(blocks.get(row["scope"], []), run.cut)
                )
                if iteration_error:
                    row["iteration_issues"].append(iteration_error)
                if (
                    row.get("start")
                    and row.get("iteration_start")
                    and row["start"] != row["iteration_start"]
                ):
                    row["iteration_issues"].append(
                        "summary_iteration_start_difference"
                    )
                if (
                    row.get("finish")
                    and row.get("iteration_finish")
                    and row["finish"] != row["iteration_finish"]
                ):
                    row["iteration_issues"].append(
                        "summary_iteration_finish_difference"
                    )
            if not rows:
                rows = [
                    {
                        "project_id": base,
                        "scope": "BASE",
                        "fields": {},
                        "issues": ["empty_summary"],
                        "ready": False,
                    }
                ]
            if with_eva:
                old_evidence = summary.get("eva_evidence") or {}
                if from_local:
                    items = old_evidence.get("work_items", [])
                    azure_ok = old_evidence.get("azure_ok", False)
                else:
                    assert gateway is not None
                    try:
                        items = gateway.create_client().list_eva_work_items(
                            name
                        )
                        azure_ok = True
                    except DashboardError:
                        items, azure_ok = [], False
                evidence = enrich(
                    rows, summary, items, azure_ok, clock_context, run.cut
                )
                if from_local:
                    for row in rows:
                        metric = row["eva_metrics"]
                        provider = old_evidence.get("clockify_mapping", {}).get(
                            row["scope"]
                        )
                        if provider:
                            metric["clockify_project_id"] = provider
                            metric["clockify_dedicated_scope"] = (
                                old_evidence.get("clockify_dedicated", {}).get(
                                    row["scope"], False
                                )
                            )
                        row["metrics_observed_date"] = old_evidence.get(
                            "observed_date", ""
                        )
                    at_cut(rows, old_evidence, run.cut)
                    evidence = old_evidence
                else:
                    evidence["observed_date"] = run.cut.isoformat()
                    evidence["clockify_mapping"] = {
                        r["scope"]: r["eva_metrics"].get("clockify_project_id")
                        for r in rows
                    }
                summary["eva_evidence"] = evidence
            return project, summary, rows

        results = map_in_parallel(read, catalog, 4)
        with transaction.atomic():
            for project, summary, rows in results:
                source = EvaAzureSource.objects.create(
                    extraction=run,
                    azure_id=project["id"],
                    name=project["name"],
                    payload={"summary": summary},
                )
                # Keep storage identities distinct if candidate scopes repeat.
                # Parser conflicts remain pending, with raw Summary evidence.
                seen: dict[str, int] = {}
                for row in rows:
                    code = row["scope"]
                    seen[code] = seen.get(code, 0) + 1
                    storage_code = (
                        code if seen[code] == 1 else f"{code}#{seen[code]}"
                    )
                    EvaScopeSnapshot.objects.create(
                        source=source,
                        project_id=row["project_id"][:100],
                        scope=storage_code,
                        row=row,
                    )
            run.published = True
            run.finished_at = timezone.now()
            run.metrics = {
                "kind": "summary_inventory",
                "reprocessed_from": previous.pk if previous else None,
                "source_observed_at": (
                    previous.metrics.get("source_observed_at")
                    or (previous.finished_at or previous.started_at).isoformat()
                    if previous
                    else run.started_at.isoformat()
                ),
                "projects": len(results),
                "blocks": sum(len(r[2]) for r in results),
                "iteration_failures": sum(
                    bool(r[1]["iteration_error"]) for r in results
                ),
                "total_seconds": round(time.perf_counter() - started, 3),
                "eva_enriched": with_eva,
                "clockify_requests": sum(
                    r[1].get("eva_evidence", {}).get("clockify_requests", 0)
                    for r in results
                ),
                "azure_metric_failures": sum(
                    not r[1].get("eva_evidence", {}).get("azure_ok", False)
                    for r in results
                )
                if with_eva
                else 0,
                "hours_pending_blocks": sum(
                    r.get("eva_metrics", {}).get("hours_pending", True)
                    for _, _, project_rows in results
                    for r in project_rows
                ),
                "azure_pending_blocks": sum(
                    r.get("eva_metrics", {}).get("azure_pending", True)
                    for _, _, project_rows in results
                    for r in project_rows
                ),
            }
            run.save()
        return run
    except Exception as error:
        run.finished_at = timezone.now()
        run.issues = [type(error).__name__]
        run.save(update_fields=["finished_at", "issues"])
        raise


def inventory_rows(
    query: str = "",
    cut: date | None = None,
    *,
    source_run: EvaExtraction | None = None,
    use_closes: bool = True,
) -> tuple[EvaExtraction | None, list[dict[str, Any]]]:
    """Read only persisted data; searching never calls Azure."""
    if cut is not None and use_closes:
        from apps.portal.services.eva_monthly_closes import read_monthly_close

        closed = read_monthly_close(cut)
        if closed is not None:
            run, rows = closed
            return run, [
                r
                for r in rows
                if not query or query.casefold() in str(r).casefold()
            ]
    run = source_run or (
        EvaExtraction.objects.filter(
            published=True, metrics__kind="summary_inventory"
        )
        .order_by("-pk")
        .first()
    )
    rows = []
    if run:
        history_feed = AzureHistoryFeed.objects.filter(
            identity=feed_identity()
        ).first()
        # Group sibling scopes so one billable entry cannot fill two rows.
        source_rows: dict[int, list[dict[str, Any]]] = {}
        scope_query = EvaScopeSnapshot.objects.filter(source__extraction=run)
        source_query = EvaAzureSource.objects.filter(extraction=run)
        if cut is not None:
            eligible_sources = scope_query.filter(
                row__iteration_start__lte=cut.isoformat(),
                row__iteration_finish__gte=cut.isoformat(),
            ).values("source_id")
            source_query = source_query.filter(pk__in=eligible_sources)
            scope_query = scope_query.filter(source_id__in=eligible_sources)
        sources = {s.pk: s for s in source_query}
        blocks = list(scope_query.order_by("source__name", "pk"))
        for block in blocks:
            source_rows.setdefault(block.source_id, []).append(dict(block.row))
        for source_id, grouped in source_rows.items():
            source = sources[source_id]
            updated_blocks = iteration_blocks(
                source.payload["summary"].get("iteration_tree", {})
            )
            for row in grouped:
                if updated_blocks.get(row["scope"]):
                    row["stages"] = updated_blocks[row["scope"]]
            at_cut(
                grouped,
                source.payload["summary"].get("eva_evidence", {}),
                cut or timezone.localdate(),
            )
            if cut is not None:
                attach_history(source, grouped, cut, history_feed)
        for block in blocks:
            source = sources[block.source_id]
            row = source_rows[block.source_id].pop(0)
            wi = row.get("eva_metrics", {}).get("wi", {})
            row["metric_stages"] = [
                wi.get(stage, {})
                for stage in (
                    "discovery",
                    "development",
                    "deployment",
                    "general",
                )
            ]
            row.update(
                calendar_fields(
                    row.get("stages", []), cut or timezone.localdate()
                )
            )
            if row.get("business_status") == "Suspendido":
                row["calendar_stage"] = "Suspendido"
            start, finish = row["iteration_start"], row["iteration_finish"]
            if cut is not None and not (
                start and finish and start <= cut.isoformat() <= finish
            ):
                continue
            row["deviation_days"] = (
                (
                    (cut or timezone.localdate()) - date.fromisoformat(finish)
                ).days
                if finish
                else None
            )
            row["azure_name"] = source.name
            row["azure_state"] = source.payload["summary"].get("state", "")
            row["display_id"] = block.project_id
            if row.get("scope") != "BASE" and not block.project_id.endswith(
                "_" + row["scope"]
            ):
                row["display_id"] = block.project_id + "_" + row["scope"]
            if not query or query.casefold() in str(row).casefold():
                rows.append(row)
    return run, rows
