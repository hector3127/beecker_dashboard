from datetime import date
from unittest.mock import Mock

import pytest

from apps.clockify.exceptions import ClockifyRequestError
from apps.datastore.models import ClockifyMonthSync, SyncRun
from apps.datastore.services import change_detection as detection
from apps.datastore.services import retry
from apps.datastore.services.clockify_sync import download_month, save_month
from apps.datastore.services.retry import with_retries
from tests.datastore.test_clockify_sync import entry, response

pytestmark = pytest.mark.django_db


def offline():
    return ClockifyRequestError("No hubo conexion con Clockify.")


def flaky(*outcomes):
    """Llamada que devuelve o lanza lo indicado, en orden."""
    calls = Mock(side_effect=list(outcomes))
    return calls


def test_a_connection_error_is_retried_with_growing_waits():
    waits = []
    call = flaky(offline(), offline(), "listo")
    assert with_retries(call, waits.append) == "listo"
    assert call.call_count == 3
    assert waits == [5, 20]


def test_it_gives_up_after_the_last_attempt_and_raises_the_connection_error():
    waits = []
    call = flaky(offline(), offline(), offline())
    with pytest.raises(ClockifyRequestError, match="No hubo conexion"):
        with_retries(call, waits.append)
    assert call.call_count == retry.ATTEMPTS
    assert waits == [5, 20]


def test_an_http_error_is_not_retried_because_clockify_did_answer():
    waits = []
    call = flaky(
        ClockifyRequestError("Clockify respondio 403", status_code=403)
    )
    with pytest.raises(ClockifyRequestError, match="403"):
        with_retries(call, waits.append)
    assert call.call_count == 1 and waits == []


def test_a_month_download_survives_a_dropped_connection():
    client = Mock()
    client.post_workspace_report.side_effect = [
        offline(),
        response([entry("a", "2026-09-01T15:00:00Z")]),
    ]
    waits = []
    rows, requests = download_month(
        client, "ws", date(2026, 9, 1), sleep=waits.append
    )
    assert [r["_id"] for r in rows] == ["a"]
    assert requests == 1
    assert waits == [5]


def test_a_month_download_that_never_connects_saves_nothing():
    client = Mock()
    client.post_workspace_report.side_effect = offline()
    with pytest.raises(ClockifyRequestError):
        download_month(client, "ws", date(2026, 9, 1), sleep=lambda _: None)


def saved_months(*months):
    run = SyncRun.objects.create(kind="test")
    for month in months:
        save_month(month, [entry(f"e{month}", f"{month}T15:00:00Z")], run)


def ok_summary(count=1, seconds=3600):
    return Mock(
        status_code=200,
        json=Mock(
            return_value={
                "totals": [{"entriesCount": count, "totalTime": seconds}]
            }
        ),
    )


def months_2026():
    return [date(2026, m, 1) for m in range(1, 7)]


def test_verification_stops_after_three_connection_failures_in_a_row():
    saved_months(*months_2026())
    client = Mock()
    client.post_workspace_summary.side_effect = offline()
    changed, notes = detection.find_changed_months(
        client, "ws", set(), sleep=lambda _: None
    )
    assert changed == []
    # 3 meses intentados (3 intentos cada uno); el resto se omite.
    assert client.post_workspace_summary.call_count == 3 * retry.ATTEMPTS
    assert sum("no se pudo verificar" in n for n in notes) == 3
    assert "Clockify no responde" in notes[-1]


def test_a_success_in_between_resets_the_failure_count():
    saved_months(*months_2026())
    client = Mock()
    client.post_workspace_summary.side_effect = (
        [offline()] * 3  # mes 1 falla
        + [offline()] * 3  # mes 2 falla
        + [ok_summary()]  # mes 3 responde: reinicia la cuenta
        + [offline()] * 3  # mes 4 falla
        + [ok_summary(), ok_summary()]
    )
    changed, notes = detection.find_changed_months(
        client, "ws", set(), sleep=lambda _: None
    )
    assert not any("Clockify no responde" in n for n in notes)
    # 3 + 3 intentos fallidos, 1 acierto, 3 fallidos y 2 aciertos.
    assert client.post_workspace_summary.call_count == 12
    assert ClockifyMonthSync.objects.count() == 6


def test_http_errors_do_not_trip_the_connection_breaker():
    saved_months(*months_2026())
    client = Mock()
    client.post_workspace_summary.return_value = Mock(status_code=500)
    _, notes = detection.find_changed_months(
        client, "ws", set(), sleep=lambda _: None
    )
    assert not any("Clockify no responde" in n for n in notes)
    assert client.post_workspace_summary.call_count == 6
