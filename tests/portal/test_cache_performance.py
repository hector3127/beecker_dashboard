"""Reutilizacion de calculos y entrega del ultimo corte durante el refresco."""

from concurrent.futures import ThreadPoolExecutor
from datetime import date
from unittest.mock import Mock

import pytest
from django.core.cache import cache
from django.test import RequestFactory, override_settings
from django.utils import timezone

from apps.portal import views
from apps.portal.services import eva4_index, financial_cache, revenue_costs
from apps.portal.services.eva4_hours import build_hour_index, index_month
from tests.portal.test_eva4 import BASE_HEADER
from tests.portal.test_eva4_hours import entry
from tests.portal.test_financial_integration import repository, revenue_row


@pytest.fixture(autouse=True)
def isolated_cache():
    cache.clear()
    yield
    cache.clear()


def test_year_index_reuses_scan_between_months_and_concurrent_requests():
    reader = Mock()
    reader.read_values.return_value = [
        BASE_HEADER,
        entry(2),
        entry(3, day="2026-09-01", eid="e2"),
    ]
    with ThreadPoolExecutor(max_workers=4) as pool:
        indexes = list(
            pool.map(
                lambda _: eva4_index.load_hour_index(reader, 2026), range(4)
            )
        )
    assert index_month(indexes[0], date(2026, 10, 1))[0]["reporte"] == 2
    assert index_month(indexes[1], date(2026, 9, 1))[0]["reporte"] == 3
    reader.read_values.assert_called_once_with("08.Base Clockify 2026")
    eva4_index.invalidate_year(2026)
    reader.read_values.return_value = [BASE_HEADER, entry(8)]
    updated = eva4_index.load_hour_index(reader, 2026)
    assert index_month(updated, date(2026, 10, 1))[0]["reporte"] == 8


def test_invalid_hours_only_block_the_affected_month():
    index = build_hour_index(
        [
            BASE_HEADER,
            entry(2),
            entry("invalid", day="2026-09-01", eid="e2"),
        ],
        2026,
    )
    assert index_month(index, date(2026, 10, 1))[0]["reporte"] == 2
    with pytest.raises(ValueError, match="no numericas"):
        index_month(index, date(2026, 9, 1))


def test_indexes_are_separated_by_spreadsheet():
    first = eva4_index.index_key(2026)
    with override_settings(GOOGLE_SPREADSHEET_ID="another-sheet"):
        assert eva4_index.index_key(2026) != first


@pytest.mark.parametrize(
    "name,path,prefix",
    [
        ("comercial", "/comercial/", "commercial"),
    ],
)
def test_stale_page_returns_saved_cut_without_source_calls(
    monkeypatch, name, path, prefix
):
    key = f"portal:{prefix}:context:v1:" + timezone.localdate().isoformat()
    cache.set(key, {"active": name, "marker": "saved"}, 86400)
    monkeypatch.setattr(
        views, "load_portfolio", lambda: pytest.fail("External read")
    )
    monkeypatch.setattr(
        "apps.portal.services.commercial_view.build_commercial_context",
        lambda _: pytest.fail("External read"),
    )
    html = getattr(views, name)(RequestFactory().get(path)).content
    assert b"cached_page.js" in html
    assert b'data-portal-ready="true"' in html
    assert cache.get(key)["marker"] == "saved"


def test_failed_refresh_preserves_commercial_cut(monkeypatch):
    key = "portal:commercial:context:v1:" + timezone.localdate().isoformat()
    cache.set(key, {"active": "comercial", "marker": "saved"}, 86400)
    monkeypatch.setattr(
        "apps.portal.services.commercial_view.build_commercial_context",
        lambda _: {"error": "Sheets unavailable"},
    )
    response = views.comercial(
        RequestFactory().get("/comercial/", {"actualizar": "1"})
    )
    assert b'data-portal-ready="false"' in response.content
    assert cache.get(key)["marker"] == "saved"
    assert not cache.get(key + ":fresh")


def test_finance_prepares_one_context_for_multiple_projects(monkeypatch):
    reader = repository([revenue_row(pid="A"), revenue_row(pid="B")])
    monkeypatch.setattr(
        financial_cache, "build_sheet_repository", lambda: reader
    )
    monkeypatch.setattr(financial_cache, "load_revenue", lambda: {})
    roster = Mock(wraps=revenue_costs.read_roster_sheet)
    rates = Mock(wraps=revenue_costs.read_rate_by_band)
    monkeypatch.setattr(revenue_costs, "read_roster_sheet", roster)
    monkeypatch.setattr(revenue_costs, "read_rate_by_band", rates)
    contexts = []

    def calculate(pid, context):
        contexts.append(context)
        assert context.bands["ana"][0] == "B1"
        assert context.rates["B1"] == 10
        return {"complete": True}

    monkeypatch.setattr(financial_cache, "calculate_project_cost", calculate)
    monkeypatch.setattr(
        financial_cache, "cost_summary", lambda **kwargs: {"complete": True}
    )
    monkeypatch.setattr(
        financial_cache,
        "load_monthly_profitability",
        lambda **kwargs: {"complete": True},
    )
    monkeypatch.setattr(
        revenue_costs.timezone, "localdate", lambda: date(2026, 10, 14)
    )
    assert financial_cache.warm_financial()["ok"]
    assert len(contexts) == 2 and contexts[0] is contexts[1]
    assert roster.call_count == rates.call_count == 1
    cache.delete(financial_cache.snapshot_key() + ":fresh")
    assert financial_cache.cached_financial_snapshot()["costs"]["complete"]
    assert financial_cache.cached_financial_snapshot()["loaded_at"]


def test_finance_does_not_prepare_tariffs_when_every_cost_is_cached(
    monkeypatch,
):
    reader = repository([revenue_row(pid="A")])
    cache.set(
        revenue_costs.key("A"),
        {"complete": True, "sprints": [], "financial_grouping_version": 2},
    )
    monkeypatch.setattr(
        financial_cache, "build_sheet_repository", lambda: reader
    )
    monkeypatch.setattr(financial_cache, "load_revenue", lambda: {})
    monkeypatch.setattr(
        financial_cache,
        "prepare_cost_context",
        Mock(side_effect=AssertionError("Roster read")),
    )
    monkeypatch.setattr(
        financial_cache,
        "calculate_project_cost",
        Mock(side_effect=AssertionError("Cost recalculated")),
    )
    monkeypatch.setattr(
        financial_cache, "cost_summary", lambda **kw: {"complete": True}
    )
    monkeypatch.setattr(
        financial_cache,
        "load_monthly_profitability",
        lambda **kw: {"complete": True},
    )
    monkeypatch.setattr(
        financial_cache, "account_profitability", lambda **kw: {}
    )
    assert financial_cache.warm_financial()["ok"]


def test_operations_resolves_population_once_per_phase_not_per_project(
    monkeypatch,
):
    from apps.portal.services import executive_operations as operations

    projects = [
        {"id": pid, "budget": 100, "start": "2026-01-01", "end": "2026-09-30"}
        for pid in ("A", "B", "C")
    ]
    population = Mock(return_value=projects)
    monkeypatch.setattr(operations, "population", population)
    for project in projects:
        cache.set(operations.burn_key(project), {"burn": 20})
    monkeypatch.setattr(
        operations,
        "build_sheet_repository",
        Mock(side_effect=AssertionError("Source read")),
    )
    assert operations.warm_operations()["ok"]
    assert population.call_count == 2  # Work plan and final summary.
