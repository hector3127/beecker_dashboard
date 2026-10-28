"""Retained revisions reconstruct past states without current-state leakage."""

from datetime import UTC, date, datetime
from unittest.mock import Mock, patch

import pytest
from django.utils import timezone

from apps.azure_devops.exceptions import AzureDevOpsRequestError
from apps.datastore.models import (
    AzureHistoricalCut,
    AzureHistoryFeed,
    AzureWorkItemRevision,
    EvaAzureSource,
    EvaExtraction,
)
from apps.portal.services.azure_history import (
    attach_history,
    download_history,
    end_of_cut,
    feed_identity,
)
from apps.portal.services.eva_azure_source import candidate_rows

pytestmark = pytest.mark.django_db


def record(
    item_id,
    rev=1,
    when="2026-09-01T12:00:00Z",
    state="Active",
    kind="Task",
    project="AMK.001",
    deleted=False,
):
    return {
        "id": item_id,
        "rev": rev,
        "fields": {
            "System.TeamProject": project,
            "System.ChangedDate": when,
            "System.State": state,
            "System.WorkItemType": kind,
            "System.Title": f"Item {item_id}",
            "System.IterationPath": f"{project}\\General_S1\\Discovery_S1",
            "System.IsDeleted": deleted,
        },
    }


def make_source():
    run = EvaExtraction.objects.create(
        cut=date(2026, 10, 28), started_at=timezone.now()
    )
    source = EvaAzureSource.objects.create(
        extraction=run, azure_id="p", name="AMK.001", payload={"summary": {}}
    )
    row = candidate_rows("AMK.001", "Sprint 1\nBudget: 2")[0]
    row.update(
        iteration_start="2026-09-01",
        iteration_finish="2026-10-31",
        stages=[{"stage": "Discovery"}],
    )
    return source, [row]


def download(records):
    gateway = Mock()
    gateway.create_client.return_value.revision_page.return_value = {
        "values": records,
        "continuationToken": "last",
        "isLastBatch": True,
    }
    with patch(
        "apps.portal.services.azure_history.AzureDevOpsGateway",
        return_value=gateway,
    ):
        download_history(lambda _: None)
    return AzureHistoryFeed.objects.get(identity=feed_identity())


def test_past_counts_deletions_moves_and_mexico_day_boundary():
    feed = download(
        [
            record(1),
            record(1, 2, "2026-10-01T12:00:00Z", "Closed"),
            record(2, kind="Risk"),
            record(2, 2, "2026-10-01T12:00:00Z", "Closed", "Risk"),
            record(3, when="2026-10-01T12:00:00Z"),
            record(4),
            record(4, 2, "2026-09-20T12:00:00Z", deleted=True),
            record(5),
            record(5, 2, "2026-09-20T12:00:00Z", project="OTHER"),
            record(6, when="2026-10-01T05:59:59.999Z"),
            record(7, when="2026-10-01T06:00:00Z"),
        ]
    )
    feed.complete_through = datetime(2026, 10, 28, tzinfo=UTC)
    feed.save()
    source, rows = make_source()
    attach_history(source, rows, date(2026, 9, 30), feed)
    assert rows[0]["eva_metrics"]["wi"]["general"] == {
        "total": 3,
        "cerrados": 0,
        "pendientes": 3,
    }
    assert rows[0]["eva_metrics"]["riesgos"] == ["Item 2"]
    assert not rows[0]["eva_metrics"]["azure_pending"]
    assert AzureHistoricalCut.objects.count() == 1
    # Cache reads do not query revisions or providers again.
    with patch(
        "apps.portal.services.azure_history.AzureWorkItemRevision.objects.filter",
        side_effect=AssertionError("revision reread"),
    ):
        attach_history(source, rows, date(2026, 9, 30), feed)
    attach_history(source, rows, date(2026, 10, 2), feed)
    assert rows[0]["eva_metrics"]["wi"]["general"]["total"] == 5
    assert rows[0]["eva_metrics"]["riesgos"] == []
    assert end_of_cut(date(2026, 9, 30)).astimezone(UTC).hour == 6


def test_partial_download_resumes_and_never_publishes_incomplete_coverage():
    gateway = Mock()
    error = AzureDevOpsRequestError("Forbidden")
    error.provider_status = 403
    gateway.create_client.return_value.revision_page.side_effect = [
        {
            "values": [record(1)],
            "continuationToken": "next",
            "isLastBatch": False,
        },
        error,
    ]
    with (
        patch(
            "apps.portal.services.azure_history.AzureDevOpsGateway",
            return_value=gateway,
        ),
        pytest.raises(AzureDevOpsRequestError),
    ):
        download_history(lambda _: None)
    feed = AzureHistoryFeed.objects.get()
    assert feed.cursor == "next"
    assert feed.complete_through is None
    source, rows = make_source()
    attach_history(source, rows, date(2026, 9, 30), feed)
    assert "eva_metrics" not in rows[0]
    gateway.create_client.return_value.revision_page.side_effect = None
    gateway.create_client.return_value.revision_page.return_value = {
        "values": [record(1), record(2)],
        "continuationToken": "last",
        "isLastBatch": True,
    }
    with patch(
        "apps.portal.services.azure_history.AzureDevOpsGateway",
        return_value=gateway,
    ):
        download_history(lambda _: None)
    assert gateway.create_client.return_value.revision_page.call_args.args == (
        "",
        "next",
    )
    assert AzureWorkItemRevision.objects.count() == 2
    feed.refresh_from_db()
    assert feed.complete_through


def test_token_isolation_and_transient_retry(settings):
    first = feed_identity()
    settings.AZURE_DEVOPS_PAT = "different-test-token"
    assert feed_identity() != first
    gateway = Mock()
    error = AzureDevOpsRequestError("Unavailable")
    error.provider_status = 503
    gateway.create_client.return_value.revision_page.side_effect = [
        error,
        {"values": [], "continuationToken": "end", "isLastBatch": True},
    ]
    with (
        patch(
            "apps.portal.services.azure_history.AzureDevOpsGateway",
            return_value=gateway,
        ),
        patch("apps.portal.services.azure_history.time.sleep") as sleep,
    ):
        download_history(lambda _: None)
    sleep.assert_called_once_with(2)


def test_invalid_batch_is_not_published_or_partially_saved():
    gateway = Mock()
    gateway.create_client.return_value.revision_page.return_value = {
        "values": [record(1), record(2, when="invalid")],
        "continuationToken": "bad",
        "isLastBatch": True,
    }
    with (
        patch(
            "apps.portal.services.azure_history.AzureDevOpsGateway",
            return_value=gateway,
        ),
        pytest.raises(ValueError),
    ):
        download_history(lambda _: None)
    assert AzureWorkItemRevision.objects.count() == 0
    assert AzureHistoryFeed.objects.get().complete_through is None
