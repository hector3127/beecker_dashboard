from datetime import date
from unittest.mock import Mock
from zoneinfo import ZoneInfo

import pytest

from apps.clockify.exceptions import (
    ClockifyReportForbiddenError,
    ClockifyRequestError,
)
from apps.clockify.services.report_mapper import build_time_entry_from_report
from apps.clockify.services.time_entry_loader import ReportPlan
from apps.datastore.models import ClockifyMonthSync, ClockifyTimeEntry, SyncRun
from apps.datastore.services import clockify_sync
from apps.datastore.services.clockify_store import read_month_rows
from tests.clockify.test_time_entry_loader import build_loader

pytestmark = pytest.mark.django_db
TZ = ZoneInfo("America/Mexico_City")


def entry(entry_id, start, project="c1", duration=3600, **extra):
    return {
        "_id": entry_id,
        "projectId": project,
        "projectName": "AMK.008 Proyecto",
        "userId": "u1",
        "userName": "Ana Ruiz",
        "billable": True,
        "description": "Pruebas",
        "taskId": "t1",
        "taskName": "Desarrollo CR",
        "tags": [{"name": "INV_OPERATIVA"}],
        "timeInterval": {
            "start": start,
            "end": start,
            "duration": duration,
        },
        **extra,
    }


def response(rows, status=200):
    return Mock(
        status_code=status, json=Mock(return_value={"timeentries": rows})
    )


def client_with(*pages):
    client = Mock()
    client.post_workspace_report.side_effect = list(pages)
    return client


def test_window_covers_the_unlocked_days():
    assert clockify_sync.window_months(date(2026, 10, 19)) == [
        date(2026, 10, 1)
    ]
    assert clockify_sync.window_months(date(2026, 10, 5)) == [
        date(2026, 9, 1),
        date(2026, 10, 1),
    ]


def test_download_month_reads_every_page_of_1000(monkeypatch):
    monkeypatch.setattr(clockify_sync, "PAGE_SIZE", 2)
    client = client_with(
        response(
            [
                entry("a", "2026-09-01T15:00:00Z"),
                entry("b", "2026-09-02T15:00:00Z"),
            ]
        ),
        response([entry("c", "2026-09-03T15:00:00Z")]),
    )
    rows, requests = clockify_sync.download_month(
        client, "ws", date(2026, 9, 1), sleep=lambda _: None
    )
    assert [r["_id"] for r in rows] == ["a", "b", "c"]
    assert requests == 2
    payload = client.post_workspace_report.call_args_list[0].args[1]
    assert payload["detailedFilter"]["pageSize"] == 2
    assert payload["dateRangeEnd"] == "2026-09-30T23:59:59.999"
    assert "projects" not in payload


def test_download_month_never_returns_a_partial_month():
    with pytest.raises(ClockifyReportForbiddenError):
        clockify_sync.download_month(
            client_with(response([], 403)), "ws", date(2026, 9, 1)
        )
    with pytest.raises(ClockifyRequestError, match="500"):
        clockify_sync.download_month(
            client_with(response([], 500)), "ws", date(2026, 9, 1)
        )


def test_save_month_replaces_the_month_and_keeps_others():
    run = SyncRun.objects.create(kind="test")
    clockify_sync.save_month(
        date(2026, 8, 1), [entry("aug", "2026-08-10T15:00:00Z")], run
    )
    clockify_sync.save_month(
        date(2026, 9, 1), [entry("old", "2026-09-10T15:00:00Z")], run
    )
    saved = clockify_sync.save_month(
        date(2026, 9, 1),
        [
            entry("new", "2026-09-10T15:00:00Z", duration=1800),
            # 1 de octubre en UTC, 30 de septiembre en la Ciudad de Mexico.
            entry("edge", "2026-10-01T01:00:00Z"),
            # Inicia en octubre: pertenece a la sincronizacion de octubre.
            entry("oct", "2026-10-02T15:00:00Z"),
        ],
        run,
    )
    assert saved == 2
    assert set(
        ClockifyTimeEntry.objects.values_list("entry_id", flat=True)
    ) == {"aug", "new", "edge"}
    month = ClockifyMonthSync.objects.get(month=date(2026, 9, 1))
    assert (month.entries_count, month.total_seconds) == (2, 5400)


def test_failed_month_does_not_touch_the_saved_one():
    run = SyncRun.objects.create(kind="test")
    clockify_sync.save_month(
        date(2026, 9, 1), [entry("keep", "2026-09-10T15:00:00Z")], run
    )
    result = clockify_sync.sync_months(
        [date(2026, 9, 1)], client_with(response([], 500)), "ws", "daily"
    )
    assert result.status == "failed"
    assert "2026-09" in result.error
    assert ClockifyTimeEntry.objects.get().entry_id == "keep"


def test_stored_rows_map_exactly_like_the_report():
    raw = entry("e1", "2026-09-30T23:30:00Z", duration=5400)
    clockify_sync.save_month(
        date(2026, 9, 1), [raw], SyncRun.objects.create(kind="test")
    )
    assert read_month_rows("c1", date(2026, 10, 1)) is None
    [stored] = read_month_rows("c1", date(2026, 9, 1))
    rates = {"ana ruiz": 15.0}
    assert build_time_entry_from_report(
        stored, "AMK.008", rates, TZ
    ) == build_time_entry_from_report(raw, "AMK.008", rates, TZ)


def test_loader_reads_synced_months_without_calling_clockify(settings):
    settings.CLOCKIFY_STORE_ENABLED = True
    clockify_sync.save_month(
        date(2026, 9, 1),
        [
            entry("e1", "2026-09-10T15:00:00Z"),
            entry("x", "2026-09-11T15:00:00Z", project="c2"),
        ],
        SyncRun.objects.create(kind="test"),
    )
    client = Mock()
    client.fetch_detailed_report_counted.return_value = ([], 1)
    loader = build_loader(client)  # hoy: 2026-10-02
    entries = loader._fetch_report(
        ReportPlan("AMK.008", "c1", date(2026, 9, 1), date(2026, 10, 2)), {}
    )
    assert [e.entry_id for e in entries] == ["e1"]
    # Septiembre sale de la base; octubre aun no esta sincronizado.
    assert [
        c.args[2] for c in client.fetch_detailed_report_counted.call_args_list
    ] == [date(2026, 10, 1)]
