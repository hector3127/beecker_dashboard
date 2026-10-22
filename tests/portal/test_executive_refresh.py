"""Refreshes return quickly, coalesce work and preserve the selected period."""

from unittest.mock import Mock

import pytest
from django.core.cache import cache
from django.test import Client, override_settings

from apps.portal.services import executive_refresh as refresh
from apps.portal.services.executive_period import _current, parse


@pytest.fixture(autouse=True)
def isolated(monkeypatch):
    cache.clear()
    refresh._pending.clear()
    executor = Mock()
    monkeypatch.setattr(refresh, "_executor", executor)
    # These unit tests execute a captured worker in the test thread, which
    # may still have another test's transaction-bound connection attached.
    monkeypatch.setattr(refresh, "close_old_connections", Mock())
    yield executor
    refresh._pending.clear()
    cache.clear()


def test_duplicate_refreshes_submit_once_and_preserve_period(
    isolated, monkeypatch
):
    period = parse({"periodo": "mes", "anio": "2026", "mes": "9"})
    token = _current.set(period)
    try:
        assert refresh.request_refresh()["state"] == "queued"
        refresh.request_refresh()
        key = refresh.status_key()
    finally:
        _current.reset(token)
    isolated.submit.assert_called_once()
    observed = []
    monkeypatch.setattr(
        refresh,
        "_prepare",
        lambda query: observed.append((_current.get(), query)) or False,
    )
    # Run precisely the captured worker context after the HTTP context ended.
    call = isolated.submit.call_args
    call.args[0](*call.args[1:])
    assert observed[0][0] == period
    assert "mes=9" in observed[0][1]
    assert _current.get() is None
    assert cache.get(key) == {"state": "ready", "partial": False}
    assert key not in refresh._pending


def test_queue_is_bounded_and_failure_releases_slot(isolated, monkeypatch):
    refresh._pending.update({"one", "two"})
    assert refresh.request_refresh() == {"state": "busy"}
    isolated.submit.assert_not_called()
    refresh._pending.clear()
    refresh.request_refresh()
    key = refresh.status_key()
    cache.set("valid-cut", {"total": 100})
    monkeypatch.setattr(
        refresh, "_prepare", Mock(side_effect=ValueError("offline"))
    )
    call = isolated.submit.call_args
    call.args[0](*call.args[1:])
    assert refresh.refresh_status() == {"state": "failed"}
    assert key not in refresh._pending
    assert cache.get("valid-cut") == {"total": 100}


def test_refresh_get_only_reads_status_and_post_requires_csrf(isolated):
    client = Client(enforce_csrf_checks=True)
    assert client.get("/ejecutiva/actualizacion/").json() == {
        "state": "idle",
        "has_financial_cut": False,
        "has_commercial_cut": False,
        "has_operations_cut": False,
    }
    assert client.post("/ejecutiva/actualizacion/").status_code == 403
    isolated.submit.assert_not_called()


@override_settings(PORTAL_LOGIN_REQUIRED=True)
def test_refresh_obeys_login_policy(isolated):
    assert Client().get("/ejecutiva/actualizacion/").status_code == 401
    isolated.submit.assert_not_called()


def test_refresh_worker_preserves_partial_state(monkeypatch):
    financial = Mock(return_value={"ok": True})
    operations = Mock(return_value={"ok": False})
    commercial = Mock(return_value={"ok": True})
    monkeypatch.setattr(
        "apps.portal.services.financial_cache.warm_financial", financial
    )
    monkeypatch.setattr(
        "apps.portal.services.executive_operations.warm_operations", operations
    )
    monkeypatch.setattr(
        "apps.portal.services.executive_commercial.warm_commercial_summary",
        commercial,
    )
    assert refresh._prepare("periodo=mes&anio=2026&mes=9") is True
    financial.assert_called_once_with(only_stale=True)
    operations.assert_called_once_with(only_stale=True)


def test_explicit_refresh_bypasses_source_caches_only_inside_its_worker(
    isolated, monkeypatch
):
    from core.utils.source_refresh import force_sources

    observed = []
    monkeypatch.setattr(
        refresh,
        "_prepare",
        lambda query: observed.append((force_sources.get(), query)) or False,
    )
    refresh.request_refresh(force=True)
    call = isolated.submit.call_args
    call.args[0](*call.args[1:])
    assert observed[0][0] is True and "forzar_fuentes=1" in observed[0][1]
    assert force_sources.get() is False
