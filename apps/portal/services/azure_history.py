"""Complete revision download and local reconstruction of any past day."""

import hashlib
import time
from collections.abc import Callable
from datetime import date, datetime, timedelta
from datetime import time as day_time
from typing import Any
from zoneinfo import ZoneInfo

from django.conf import settings
from django.db import transaction
from django.db.models import OuterRef, Subquery
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from apps.azure_devops.exceptions import AzureDevOpsRequestError
from apps.azure_devops.gateway import AzureDevOpsGateway
from apps.datastore.models import (
    AzureHistoricalCut,
    AzureHistoryFeed,
    AzureWorkItemRevision,
    EvaAzureSource,
)
from apps.portal.services.summary_eva_metrics import metric_rows


def feed_identity() -> str:
    """Isolate retained history from another configured organization/token."""
    return hashlib.sha256(
        (
            settings.AZURE_DEVOPS_ORGANIZATION + ":" + settings.AZURE_DEVOPS_PAT
        ).encode()
    ).hexdigest()


def download_history(
    progress: Callable[[str], Any] = print, *, reports: bool = False
) -> dict[str, Any]:
    """Checkpoint each validated batch; publish coverage only at the end."""
    started = time.perf_counter()
    watermark = timezone.now()
    base_feed, _ = AzureHistoryFeed.objects.get_or_create(
        identity=feed_identity()
    )
    feed = base_feed
    if reports:
        feed, _ = AzureHistoryFeed.objects.get_or_create(
            identity=hashlib.sha256(
                (feed_identity() + ":reports").encode()
            ).hexdigest()
        )
    client = AzureDevOpsGateway().create_client()
    token, seen = feed.cursor, set()
    pages = revisions = 0
    try:
        while True:
            if token in seen:
                raise ValueError("Repeated revision cursor")
            seen.add(token)
            for attempt in range(5):
                try:
                    page = (
                        client.revision_page("", token, reports=True)
                        if reports
                        else client.revision_page("", token)
                    )
                    break
                except AzureDevOpsRequestError as error:
                    if attempt == 4 or error.provider_status not in (
                        None,
                        429,
                        500,
                        502,
                        503,
                        504,
                    ):
                        raise
                    progress(
                        "Azure temporalmente no disponible; reintentando lote."
                    )
                    time.sleep(2 ** (attempt + 1))
            if not isinstance(page.get("values"), list) or not isinstance(
                page.get("isLastBatch"), bool
            ):
                raise ValueError("Invalid history batch")
            records = []
            for row in page["values"]:
                fields = row.get("fields") or {}
                changed = parse_datetime(
                    str(fields.get("System.ChangedDate", ""))
                )
                if changed is None or timezone.is_naive(changed):
                    raise ValueError("Invalid revision date")
                if (
                    int(row["id"]) <= 0
                    or int(row["rev"]) <= 0
                    or not fields.get("System.TeamProject")
                ):
                    raise ValueError("Invalid revision identity")
                records.append(
                    AzureWorkItemRevision(
                        feed=base_feed,
                        work_item_id=int(row["id"]),
                        revision=int(row["rev"]),
                        project_name=fields.get("System.TeamProject", ""),
                        changed_at=changed,
                        deleted=fields.get("System.IsDeleted")
                        in (True, "True", "true"),
                        fields=fields,
                    )
                )
            next_token = str(page.get("continuationToken") or "")
            if not page["isLastBatch"] and not next_token:
                raise ValueError("Missing revision cursor")
            with transaction.atomic():
                if reports:
                    AzureWorkItemRevision.objects.bulk_create(
                        records,
                        update_conflicts=True,
                        update_fields=["fields"],
                        unique_fields=["feed", "work_item_id", "revision"],
                        batch_size=500,
                    )
                else:
                    AzureWorkItemRevision.objects.bulk_create(
                        records, ignore_conflicts=True, batch_size=500
                    )
                feed.cursor = next_token or token
                feed.updated_at = timezone.now()
                feed.error = ""
                if page["isLastBatch"]:
                    feed.complete_through = watermark
                feed.save()
                if reports and records:
                    AzureHistoricalCut.objects.filter(feed=base_feed).delete()
            pages += 1
            revisions += len(records)
            progress(
                f"Histórico Azure: {pages} lotes, "
                f"{revisions} revisiones leídas."
            )
            if page["isLastBatch"]:
                break
            token = next_token
        return {
            "pages": pages,
            "revisions": revisions,
            "seconds": round(time.perf_counter() - started, 3),
        }
    except Exception as error:
        feed.error = type(error).__name__
        feed.save(update_fields=["error"])
        raise


def end_of_cut(cut: date) -> datetime:
    """Exclusive next midnight in the portal's Mexico timezone."""
    return datetime.combine(
        cut + timedelta(days=1), day_time.min, ZoneInfo(settings.TIME_ZONE)
    )


def attach_history(
    source: EvaAzureSource,
    rows: list[dict[str, Any]],
    cut: date,
    feed: AzureHistoryFeed | None,
) -> None:
    """Fill past counts from persisted revisions; never contact Azure."""
    end = end_of_cut(cut)
    if feed and feed.complete_through and cut == timezone.localdate():
        end = min(end, feed.complete_through)
    if not feed or not feed.complete_through or end > feed.complete_through:
        return
    cached = AzureHistoricalCut.objects.filter(
        feed=feed, source=source, cut=cut, feed_through=feed.complete_through
    ).first()
    if cached and all(
        value.get("rules_version") == 3 for value in cached.metrics.values()
    ):
        metrics = cached.metrics
    else:
        latest = (
            AzureWorkItemRevision.objects.filter(
                feed=feed,
                work_item_id=OuterRef("work_item_id"),
                changed_at__lt=end,
            )
            .order_by("-revision")
            .values("revision")[:1]
        )
        revisions = AzureWorkItemRevision.objects.filter(
            feed=feed,
            project_name=source.name,
            changed_at__lt=end,
            revision=Subquery(latest),
            deleted=False,
        )
        items = [{"id": r.work_item_id, "fields": r.fields} for r in revisions]
        projected = metric_rows(
            rows,
            items,
            source.payload["summary"].get("iteration_tree", {}),
            cut,
        )
        metrics = {
            r["scope"]: {
                "rules_version": 3,
                **{
                    k: r[k]
                    for k in (
                        "wi",
                        "riesgos",
                        "azure_pending",
                        "status",
                        "closed",
                        "suspension_work_items",
                    )
                },
            }
            for r in projected
        }
        AzureHistoricalCut.objects.update_or_create(
            feed=feed,
            source=source,
            cut=cut,
            defaults={
                "feed_through": feed.complete_through,
                "metrics": metrics,
            },
        )
    for row in rows:
        if row["scope"] in metrics:
            row.setdefault("eva_metrics", {}).update(metrics[row["scope"]])
            row["azure_unavailable_label"] = (
                "Sin datos" if metrics[row["scope"]]["azure_pending"] else ""
            )
            row["azure_unavailable_reason"] = (
                "No se pudo relacionar este bloque con una etapa verificable."
                if metrics[row["scope"]]["azure_pending"]
                else ""
            )
            row["azure_history_asof"] = cut.isoformat()
            row["business_status"] = metrics[row["scope"]].get("status", "")
