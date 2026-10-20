from datetime import date
from unittest.mock import Mock

import pytest
from django.core.cache import cache
from django.test import RequestFactory, override_settings

from apps.portal import views
from apps.portal.services import (
    account_profitability,
    monthly_profitability,
    revenue,
    revenue_costs,
)
from apps.portal.services import executive_period as period
from tests.fakes import InMemorySheetRepository


def reader():
    return InMemorySheetRepository(
        {
            "DataRevenue": [
                ["Status", "Account", "", "", "ID", "", "Date", "USD"],
                ["Collected", "Acme", "", "", "A", "", "2026-03-31", 100],
                ["Invoiced", "Acme", "", "", "A", "", "2026-04-01", 200],
                ["Confirmed", "Acme", "", "", "A", "", "2025-04-01", 999],
            ]
        }
    )


@pytest.mark.parametrize(
    "query,start,end",
    [
        (
            {"periodo": "trimestre", "anio": "2026", "trimestre": "2"},
            date(2026, 4, 1),
            date(2026, 6, 30),
        ),
        (
            {"periodo": "anio", "anio": "2025"},
            date(2025, 1, 1),
            date(2025, 12, 31),
        ),
        (
            {"periodo": "mes", "anio": "2024", "mes": "2"},
            date(2024, 2, 1),
            date(2024, 2, 29),
        ),
        (
            {"periodo": "rango", "desde": "2026-03-31", "hasta": "2026-04-01"},
            date(2026, 3, 31),
            date(2026, 4, 1),
        ),
    ],
)
def test_period_bounds(query, start, end):
    parsed = period.parse(query)
    assert (parsed.start, parsed.end) == (start, end)


def test_income_rankings_months_and_cache_use_exact_dates(monkeypatch):
    cache.clear()
    r = reader()
    monkeypatch.setattr(revenue, "build_sheet_repository", lambda: r)
    assert revenue.load_revenue()["total"] == "300.00"
    annual_key = revenue_costs.key("A")
    token = period._current.set(
        period.parse(
            {"periodo": "rango", "desde": "2026-04-01", "hasta": "2026-04-01"}
        )
    )
    try:
        assert revenue.load_revenue()["total"] == "200.00"
        assert revenue_costs.key("A") != annual_key
        cache.set(
            revenue_costs.key("A"),
            {
                "complete": True,
                "entries": {"x": 20},
                "entry_months": {"x": "2026-04"},
            },
        )
        a = account_profitability.account_profitability(r)["accounts"][0]
        assert a["revenue"] == 200 and a["cost"] == 20 and a["margin"] == 90
        months = monthly_profitability.load_monthly_profitability(r, ["A"])[
            "months"
        ]
        assert (
            len(months) == 1
            and months[0]["revenue"] == 200
            and months[0]["cost"] == 20
        )
    finally:
        period._current.reset(token)
    assert revenue.load_revenue()["total"] == "300.00"
    cache.clear()


@override_settings(PORTAL_LOGIN_REQUIRED=False)
def test_invalid_range_returns_400_and_does_not_leak_context():
    response = views.ingresos(
        RequestFactory().get(
            "/ejecutiva/ingresos/",
            {"periodo": "rango", "desde": "2026-06-01", "hasta": "2026-01-01"},
        )
    )
    assert response.status_code == 400
    assert period.current() is None


def test_project_cost_query_clips_clockify_dates(monkeypatch):
    from types import SimpleNamespace

    cache.clear()
    token = period._current.set(
        period.parse(
            {"periodo": "rango", "desde": "2026-04-10", "hasta": "2026-04-15"}
        )
    )
    loader = Mock()
    loader.load_project.return_value = []
    monkeypatch.setattr(
        revenue_costs, "build_clockify_loader", lambda r: loader
    )
    context = SimpleNamespace(
        reader=reader(),
        ids=["A"],
        allowed_ids={"a"},
        today=date(2026, 10, 14),
        rates={},
        bands={},
    )
    try:
        result = revenue_costs.calculate_project_cost("A", context)
        loader.load_project.assert_called_once_with(
            "A", (date(2026, 4, 10), date(2026, 4, 15))
        )
        assert result["hours"] == 0 and result["complete"]
    finally:
        period._current.reset(token)
    cache.clear()


def test_default_annual_and_explicit_full_year_share_financial_cache():
    default_key = revenue_costs.key("AER.NEM.001")
    for query in [
        {"periodo": "anio", "anio": "2026"},
        {"periodo": "rango", "desde": "2026-01-01", "hasta": "2026-12-31"},
    ]:
        token = period._current.set(period.parse(query))
        try:
            assert revenue_costs.key("AER.NEM.001") == default_key
        finally:
            period._current.reset(token)
