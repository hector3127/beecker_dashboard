"""Los nuevos periodos conservan sus caches y las consultas en paralelo."""

from unittest.mock import Mock

import pytest
from django.core.cache import cache
from django.test import RequestFactory

from apps.portal.services import executive_commercial as commercial
from apps.portal.services import executive_operations as operations
from apps.portal.services import executive_period as period
from apps.portal.services.account_profitability import (
    load_account_profitability,
)
from apps.portal.services.financial_cache import snapshot_key
from apps.portal.services.revenue_costs import key
from core.utils.parallel import map_in_parallel


@pytest.fixture(autouse=True)
def isolated_cache():
    cache.clear()
    yield
    cache.clear()


def selected_month(month):
    return period.parse({"periodo": "mes", "anio": "2026", "mes": month})


def test_parallel_queries_keep_period_and_isolate_worker_mutations():
    token = period._current.set(selected_month("4"))
    expected_key = key("AIN.002 CR")

    def query(index):
        result = (period.bounds(), key("AIN.002 CR"))
        period._current.set(selected_month("5"))
        return result

    try:
        results = map_in_parallel(query, list(range(4)), max_workers=2)
        assert all(
            result == (period.bounds(), expected_key) for result in results
        )
        assert period.current().start.month == 4
    finally:
        period._current.reset(token)
    assert period.current() is None
    assert key("AIN.002 CR") != expected_key


def test_operations_summary_for_a_month_cannot_replace_annual_snapshot(
    monkeypatch,
):
    annual_key = operations.operations_snapshot_key()
    cache.set(annual_key, {"budget": 900, "marker": "annual"})
    token = period._current.set(selected_month("4"))
    project = {
        "id": "P1",
        "budget": 100,
        "start": "2026-04-01",
        "end": "2026-04-30",
    }
    try:
        monthly_key = operations.operations_snapshot_key()
        assert monthly_key != annual_key
        cache.set(operations.burn_key(project), {"burn": 20})
        monkeypatch.setattr(operations, "population", lambda: [project])
        assert operations.operations_summary()["advance"] == 20
        assert cache.get(monthly_key)["budget"] == 100
    finally:
        period._current.reset(token)
    assert operations.cached_operations_snapshot()["marker"] == "annual"


def test_selected_period_reuses_its_prepared_financial_accounts(monkeypatch):
    token = period._current.set(selected_month("4"))
    try:
        prepared = {
            "accounts": [{"name": "Acme", "revenue": 200, "gross_profit": 100}],
            "year": 2026,
        }
        cache.set(snapshot_key(), {"accounts": prepared})
        monkeypatch.setattr(
            "apps.portal.services.account_profitability.account_profitability",
            lambda: pytest.fail("Unexpected source read"),
        )
        loaded = load_account_profitability()
        assert [a["name"] for a in loaded["accounts"]] == ["Acme"]
    finally:
        period._current.reset(token)
    assert cache.get(snapshot_key()) is None


def test_commercial_precache_adds_real_data_without_losing_financial_cut(
    monkeypatch,
):
    snapshot = {"revenue": {"total": "100"}, "costs": {"cost": 20}}
    cache.set(snapshot_key(), snapshot)
    summary = {"won": 100, "open": 200}
    monkeypatch.setattr(
        commercial, "commercial_summary", Mock(return_value=summary)
    )
    assert commercial.warm_commercial_summary()["ok"]
    assert cache.get(snapshot_key()) == {**snapshot, "commercial": summary}


def test_context_is_restored_when_a_view_raises():
    @period.period_view
    def broken(request):
        assert period.current().start.month == 4
        raise RuntimeError("Failure")

    request = RequestFactory().get(
        "/", {"periodo": "mes", "anio": "2026", "mes": "4"}
    )
    with pytest.raises(RuntimeError):
        broken(request)
    assert period.current() is None
