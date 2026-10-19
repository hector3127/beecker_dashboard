from datetime import date
from unittest.mock import Mock

import pytest

from apps.clockify.exceptions import ClockifyRequestError
from apps.datastore.models import ClockifyMonthSync, SyncRun
from apps.datastore.services import change_detection as detection
from apps.datastore.services.clockify_sync import save_month, sync_months
from tests.datastore.test_clockify_sync import entry, response

pytestmark = pytest.mark.django_db
TODAY = date(2026, 10, 19)


def ok(payload, status=200):
    return Mock(status_code=status, json=Mock(return_value=payload))


def summary(count, seconds):
    return ok({"totals": [{"entriesCount": count, "totalTime": seconds}]})


def saved_month(month, entries):
    run = SyncRun.objects.create(kind="test")
    save_month(month, entries, run)


def test_normal_lock_only_checks_the_open_window():
    months, notes = detection.months_open_by_lock(
        "2026-10-09T06:00:00Z", TODAY, [date(2026, 1, 1)]
    )
    assert months == [date(2026, 10, 1)]
    assert notes == []


def test_an_old_lock_reopens_every_month_since_that_day():
    months, notes = detection.months_open_by_lock(
        "2026-01-01T06:00:00Z", TODAY, []
    )
    assert months[0] == date(2026, 1, 1)
    assert months[-1] == date(2026, 10, 1)
    assert len(months) == 10
    assert "Bloqueo en 2026-01-01" in notes[0]


def test_no_lock_reviews_every_saved_month():
    synced = [date(2025, 3, 1), date(2026, 9, 1)]
    months, notes = detection.months_open_by_lock("", TODAY, synced)
    assert months == [date(2025, 3, 1), date(2026, 9, 1), date(2026, 10, 1)]
    assert "no tiene bloqueo" in notes[0]


def test_unreadable_lock_falls_back_to_the_window():
    months, notes = detection.months_open_by_lock(None, TODAY, [])
    assert months == [date(2026, 10, 1)]
    assert "No se pudo leer" in notes[0]


def test_read_lock_returns_none_instead_of_failing():
    client = Mock()
    client.get.return_value = ok({}, 500)
    assert detection.read_lock(client, "ws") is None
    client.get.side_effect = ClockifyRequestError("offline")
    assert detection.read_lock(client, "ws") is None
    client.get.side_effect = None
    client.get.return_value = ok(
        {"workspaceSettings": {"lockTimeEntries": None}}
    )
    assert detection.read_lock(client, "ws") == ""


def test_month_with_different_totals_is_flagged_and_equal_ones_are_not():
    saved_month(date(2026, 8, 1), [entry("a", "2026-08-10T15:00:00Z")])
    saved_month(
        date(2026, 9, 1),
        [
            entry("b", "2026-09-10T15:00:00Z"),
            entry("c", "2026-09-11T15:00:00Z"),
        ],
    )
    client = Mock()
    client.post_workspace_summary.side_effect = [
        summary(1, 3600),  # agosto cuadra
        summary(2, 9000),  # septiembre: una duracion cambio
    ]
    changed, notes = detection.find_changed_months(client, "ws", set())
    assert changed == [date(2026, 9, 1)]
    assert "2026-09" in notes[0] and "2.50 h" in notes[0]
    payload = client.post_workspace_summary.call_args.args[1]
    assert "detailedFilter" not in payload
    assert payload["dateRangeEnd"] == "2026-09-30T23:59:59.999"


def test_months_already_scheduled_are_not_compared_again():
    saved_month(date(2026, 10, 1), [entry("a", "2026-10-05T15:00:00Z")])
    client = Mock()
    changed, _ = detection.find_changed_months(
        client, "ws", {date(2026, 10, 1)}
    )
    assert changed == []
    client.post_workspace_summary.assert_not_called()


def test_a_month_that_cannot_be_checked_is_reported_not_redownloaded():
    saved_month(date(2026, 8, 1), [entry("a", "2026-08-10T15:00:00Z")])
    client = Mock()
    client.post_workspace_summary.return_value = ok({}, 500)
    changed, notes = detection.find_changed_months(client, "ws", set())
    assert changed == []
    assert "no se pudo verificar" in notes[0]


def test_daily_plan_redownloads_the_month_edited_while_unlocked():
    saved_month(date(2026, 3, 1), [entry("old", "2026-03-10T15:00:00Z")])
    client = Mock()
    client.get.return_value = ok(
        {"workspaceSettings": {"lockTimeEntries": "2026-10-09T06:00:00Z"}}
    )
    # Marzo ya no cuadra: alguien lo edito y lo bloqueo de nuevo.
    client.post_workspace_summary.return_value = summary(1, 7200)
    plan = detection.plan_daily(client, "ws", TODAY)
    assert plan.months == [date(2026, 3, 1), date(2026, 10, 1)]
    assert plan.lock_seen == "2026-10-09T06:00:00Z"

    client.post_workspace_report.side_effect = [
        response([entry("new", "2026-03-10T15:00:00Z", duration=7200)]),
        response([entry("oct", "2026-10-05T15:00:00Z")]),
    ]
    run = sync_months(
        plan.months,
        client,
        "ws",
        "daily",
        sleep=lambda _: None,
        lock_seen=plan.lock_seen,
        notes=plan.notes,
    )
    assert run.status == "ok" and run.lock_seen == plan.lock_seen
    assert "2026-03" in run.notes
    march = ClockifyMonthSync.objects.get(month=date(2026, 3, 1))
    assert (march.entries_count, march.total_seconds) == (1, 7200)


def test_plan_notes_when_the_lock_moves_back_and_skips_verification():
    SyncRun.objects.create(kind="daily", lock_seen="2026-10-09T06:00:00Z")
    client = Mock()
    client.get.return_value = ok(
        {"workspaceSettings": {"lockTimeEntries": "2026-09-01T06:00:00Z"}}
    )
    plan = detection.plan_daily(client, "ws", TODAY, verify=False)
    assert plan.months == [date(2026, 9, 1), date(2026, 10, 1)]
    assert any("retrocedio" in note for note in plan.notes)
    client.post_workspace_summary.assert_not_called()
