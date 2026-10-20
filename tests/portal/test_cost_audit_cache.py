import pytest
from django.core.cache import cache
from django.test import RequestFactory, override_settings

from apps.portal import views
from apps.portal.services import revenue_costs
from apps.portal.services.cost_audit_cache import prepared_detail, remember
from apps.portal.services.revenue_costs import calculate_project_cost, key


def payload():
    return {
        "id": "P1",
        "cost": 20,
        "hours": 2,
        "complete": False,
        "people": [],
        "sprints": [],
        "financial_grouping_version": 2,
        "entries": {"e": 20},
        "entry_months": {"e": "2026-01"},
    }


@override_settings(PORTAL_LOGIN_REQUIRED=False)
def test_opening_prepared_detail_makes_no_source_calls(monkeypatch):
    cache.clear()
    cache.set(key("P1"), payload())
    remember({"projects": [{"id": "P1", "revenue": 100}]}, "Acme")
    monkeypatch.setattr(
        "core.sheets.factory.build_sheet_repository",
        lambda: pytest.fail("Unexpected Sheets read"),
    )
    monkeypatch.setattr(
        revenue_costs,
        "build_sheet_repository",
        lambda: pytest.fail("Unexpected inventory read"),
    )
    response = views.costos_revenue(
        RequestFactory().get(
            "/ejecutiva/costos/", {"id": "P1", "nombre": "Acme"}
        )
    )
    assert response.status_code == 200
    data = (
        response.json()
        if hasattr(response, "json")
        else __import__("json").loads(response.content)
    )
    assert (
        data["cost"] == 20 and data["revenue"] == 100 and data["margin"] == 80
    )
    assert data["margin_provisional"] and "entries" not in data
    assert prepared_detail("P1", "Other") is None
    cache.clear()


def test_prepared_cost_returns_before_loading_inventory(monkeypatch):
    cache.clear()
    cache.set(key("P1"), payload())
    monkeypatch.setattr(
        revenue_costs,
        "build_sheet_repository",
        lambda: pytest.fail("Unexpected source read"),
    )
    assert calculate_project_cost("P1")["hours"] == 2
    cache.clear()


@override_settings(PORTAL_LOGIN_REQUIRED=False)
def test_prepared_summary_reuses_details_without_reading_sources(monkeypatch):
    from apps.portal.services.cost_audit_cache import remember_summary

    cache.clear()
    cache.set(key("P1"), payload())
    remember_summary({"projects": [{"id": "P1", "revenue": 100}]}, "Acme")
    monkeypatch.setattr(
        "core.sheets.factory.build_sheet_repository",
        lambda: pytest.fail("Unexpected Sheets read"),
    )
    monkeypatch.setattr(
        revenue_costs,
        "cost_summary",
        lambda **kwargs: pytest.fail("Unexpected summary rebuild"),
    )
    response = views.costos_revenue(
        RequestFactory().get("/ejecutiva/costos/", {"nombre": "Acme"})
    )
    assert response.status_code == 200
    data = __import__("json").loads(response.content)
    assert data["prepared_details"]["p1"]["cost"] == 20
    assert data["prepared_details"]["p1"]["revenue"] == 100
    cache.clear()
