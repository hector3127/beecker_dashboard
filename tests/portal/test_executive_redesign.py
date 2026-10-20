import pytest
from django.core.cache import cache
from django.test import RequestFactory, override_settings

from apps.portal.services import executive_period as period
from apps.portal.services.account_profitability import account_profitability
from apps.portal.services.monthly_profitability import (
    load_monthly_profitability,
)
from apps.portal.services.revenue import load_revenue
from apps.portal.services.revenue_costs import key
from apps.portal.templatetags.executive_numbers import money_k
from tests.fakes import InMemorySheetRepository


def source():
    return InMemorySheetRepository(
        {
            "DataRevenue": [
                ["Status", "Account", "", "", "ID", "", "Date", "USD"],
                ["Collected", "Tiny", "", "", "A", "", "2026-05-01", 100],
                ["Invoiced", "Large", "", "", "B", "", "2026-05-01", 1000000],
                ["Confirmed", "Large", "", "", "C", "", "2026-05-01", 5000000],
            ]
        }
    )


def test_format_uses_thousands_without_cents():
    assert money_k(1897644.14) == "1,897K"
    assert money_k(None) == "Pendiente"
    assert money_k(-2413.59) == "-2K"


def test_ranking_weights_margin_by_invoice_volume():
    cache.clear()
    cache.set(key("A"), {"complete": True, "entries": {"a": 0}})
    cache.set(key("B"), {"complete": True, "entries": {"b": 800000}})
    result = account_profitability(source())
    accounts = {a["name"]: a for a in result["accounts"]}
    assert accounts["Large"]["revenue"] == 1000000
    assert (
        accounts["Large"]["weighted_score"] > accounts["Tiny"]["weighted_score"]
    )
    assert result["healthy"][0]["name"] == "Large"
    assert set(a["name"] for a in result["healthy"]).isdisjoint(
        a["name"] for a in result["unhealthy"]
    )
    cache.clear()


def test_monthly_invoice_excludes_confirmed_and_is_scoped():
    token = period._current.set(
        period.parse(
            {"periodo": "rango", "desde": "2026-05-01", "hasta": "2026-10-31"}
        )
    )
    try:
        data = load_monthly_profitability(source(), ids=[])
        assert len(data["months"]) == 6
        assert data["months"][0]["revenue"] == 1000100
        assert data["months"][-1]["month"] == "2026-10"
    finally:
        period._current.reset(token)


def test_collections_includes_factoring_and_excludes_confirmed_from_denominator(
    monkeypatch,
):
    from apps.portal.services import revenue

    cache.clear()
    reader = InMemorySheetRepository(
        {
            "DataRevenue": [
                ["Status", "", "", "", "", "", "Date", "Amount"],
                ["Collected Factoring", "", "", "", "", "", "2026-05-01", 100],
                ["Invoiced", "", "", "", "", "", "2026-05-01", 200],
                ["Confirmed", "", "", "", "", "", "2026-05-01", 900],
            ]
        }
    )
    monkeypatch.setattr(revenue, "build_sheet_repository", lambda: reader)
    result = load_revenue()
    assert (
        result["invoiced"] == "300.00"
        and result["collections_percent"] == 33.33
    )
    cache.clear()


@override_settings(PORTAL_LOGIN_REQUIRED=False)
def test_overview_uses_prepared_cut_without_source_calls(monkeypatch):
    from apps.portal import views
    from apps.portal.services import (
        executive_operations,
        executive_refresh,
        financial_cache,
    )

    monkeypatch.setattr(
        financial_cache,
        "cached_financial_snapshot",
        lambda: {
            "loaded_at": "2026-10-19T12:00:00",
            "revenue": {"invoiced": "100"},
        },
    )
    monkeypatch.setattr(
        executive_operations,
        "cached_operations_snapshot",
        lambda: {"partial": False, "etc": 360},
    )
    monkeypatch.setattr(
        views,
        "load_portfolio",
        lambda: pytest.fail("No portfolio call on opening"),
    )
    monkeypatch.setattr(
        executive_refresh,
        "request_refresh",
        lambda: pytest.fail("No refresh on prepared cut"),
    )
    response = views.ejecutiva(
        RequestFactory().get(
            "/ejecutiva/",
            {"periodo": "rango", "desde": "2026-05-01", "hasta": "2026-10-31"},
        )
    )
    assert response.status_code == 200
    html = response.content.decode()
    assert "01/05/2026 - 31/10/2026" in html
    assert "executive_report.js" in html
    assert "financial-costs-updated" not in html
    assert "Crear seguimiento" not in html


@pytest.mark.django_db
@override_settings(PORTAL_LOGIN_REQUIRED=False)
def test_agreements_keep_account_and_session(client):
    from django.urls import reverse

    response = client.post(
        reverse("portal:acuerdos_ejecutivos"),
        {
            "title": "Validar capacidad",
            "account": "Acme",
            "meeting_source": "board",
            "meeting_date": "2026-10-19",
            "kind": "agreement",
            "status": "open",
        },
    )
    assert response.status_code == 200
    row = response.json()["items"][0]
    assert (
        row["account"] == "Acme"
        and row["meeting_source"] == "board"
        and row["meeting_date"] == "2026-10-19"
    )


def test_monthly_margin_is_available_with_partial_costs():
    cache.clear()
    cache.set(
        key("A"),
        {
            "complete": False,
            "entries": {"a": 25},
            "entry_months": {"a": "2026-05"},
        },
    )
    result = load_monthly_profitability(source(), ids=["A", "MISSING"])
    may = next(x for x in result["months"] if x["month"] == "2026-05")
    assert (
        may["cost"] == 25
        and may["margin"] is not None
        and may["partial"] is True
    )
    assert result["complete"] is False
    cache.clear()


def test_directors_example_two_monetary_indicators():
    from apps.portal.services.account_profitability import (
        rank_financial_accounts,
    )

    result = rank_financial_accounts(
        [
            {
                "name": "Un peso",
                "revenue": 1,
                "cost": 0,
                "gross_profit": 1,
                "margin": 100,
                "pending": 0,
            },
            {
                "name": "Un millon",
                "revenue": 1000000,
                "cost": 800000,
                "gross_profit": 200000,
                "margin": 20,
                "pending": 0,
            },
        ]
    )
    assert result["healthy"][0]["name"] == "Un millon"
    assert result["healthy"][0]["profit_points"] == 70
    assert result["healthy"][0]["invoice_points"] == 30
    assert result["healthy"][0]["weighted_score"] == 100
    assert result["unhealthy"][0]["weighted_score"] < 0.01


def test_ranking_includes_accounts_with_partial_and_no_costs():
    from apps.portal.services.account_profitability import (
        rank_financial_accounts,
    )

    result = rank_financial_accounts(
        [
            {
                "name": "Heineken",
                "revenue": 428560.33,
                "cost": 213041.31,
                "gross_profit": 215519.02,
                "pending": 7,
            },
            {
                "name": "Complete",
                "revenue": 53950,
                "cost": 11050,
                "gross_profit": 42900,
                "pending": 0,
            },
            {
                "name": "No cost yet",
                "revenue": 100,
                "cost": 0,
                "gross_profit": 100,
                "pending": 1,
            },
            {
                "name": "No activity",
                "revenue": 0,
                "cost": 0,
                "gross_profit": 0,
                "pending": 1,
            },
        ]
    )
    assert result["healthy"][0]["name"] == "Heineken"
    assert result["healthy"][0]["partial"] is True
    assert all(a["weighted_score"] is not None for a in result["accounts"])
    assert result["pending_accounts"] == 3
