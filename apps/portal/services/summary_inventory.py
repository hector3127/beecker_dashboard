"""Local Summary inventory, independent of EVA eligibility and cuts."""

import time
from typing import Any

from django.db import transaction
from django.utils import timezone

from apps.azure_devops.gateway import AzureDevOpsGateway
from apps.datastore.models import (
    EvaAzureSource,
    EvaExtraction,
    EvaScopeSnapshot,
)
from apps.portal.services.eva_azure_source import BUSINESS_ID, candidate_rows
from core.utils.parallel import map_in_parallel


def extract_summaries() -> EvaExtraction:
    """Store every PAT-visible project, without service or closure filters."""
    started = time.perf_counter()
    run = EvaExtraction.objects.create(
        cut=timezone.localdate(),
        started_at=timezone.now(),
        full_inventory=False,
        metrics={"kind": "summary_inventory"},
    )
    try:
        gateway = AzureDevOpsGateway()
        catalog = gateway.create_client().list_summary_projects()

        def read(
            project: dict[str, Any],
        ) -> tuple[dict[str, Any], dict[str, Any], list[dict[str, Any]]]:
            summary = (
                project
                if "description" in project
                else gateway.create_client().get_project_summary(project["id"])
            )
            name = str(project["name"])
            match = BUSINESS_ID.match(name.upper())
            base = match[0].split("_", 1)[0] if match else name
            rows = candidate_rows(base, str(summary.get("description") or ""))
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
                "projects": len(results),
                "blocks": sum(len(r[2]) for r in results),
                "total_seconds": round(time.perf_counter() - started, 3),
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
) -> tuple[EvaExtraction | None, list[dict[str, Any]]]:
    """Read only persisted data; searching never calls Azure."""
    run = (
        EvaExtraction.objects.filter(
            published=True, metrics__kind="summary_inventory"
        )
        .order_by("-pk")
        .first()
    )
    rows = []
    if run:
        for block in (
            EvaScopeSnapshot.objects.filter(source__extraction=run)
            .select_related("source")
            .order_by("source__name", "pk")
        ):
            row = dict(block.row)
            row["azure_name"] = block.source.name
            row["azure_state"] = block.source.payload["summary"].get(
                "state", ""
            )
            row["display_id"] = block.project_id
            if row.get("scope") != "BASE" and not block.project_id.endswith(
                "_" + row["scope"]
            ):
                row["display_id"] = block.project_id + "_" + row["scope"]
            if not query or query.casefold() in str(row).casefold():
                rows.append(row)
    return run, rows
