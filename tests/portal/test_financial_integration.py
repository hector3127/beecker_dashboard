"""Finanzas integra fuentes reales, precarga y las reglas CR existentes."""

from datetime import date, datetime
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from django.core.cache import cache
from django.test import RequestFactory, override_settings

from apps.portal import views
from apps.portal.services import (
    financial_cache,
    monthly_profitability,
    revenue,
    revenue_costs,
)
from apps.portal.services.portfolio_loader import PortfolioLoad
from core.time_entries.models import TimeEntry
from tests.clockify.test_cr_shared_project import client, entry, sheets
from tests.clockify.test_time_entry_loader import build_loader
from tests.fakes import InMemorySheetRepository

TODAY = date(2026, 10, 14)


def revenue_row(
    pid="AIN.002 CR", amount=100, status="Collected", day="2026-09-01"
):
    return [status, "", "", "", pid, "", day, amount]


@pytest.fixture(autouse=True)
def isolated_cache(monkeypatch):
    cache.clear()
    monkeypatch.setattr(revenue_costs.timezone, "localdate", lambda: TODAY)
    yield
    cache.clear()


def repository(rows=None):
    return InMemorySheetRepository(
        {
            "DataRevenue": [
                ["Status", "", "", "", "ID", "", "Date", "USD"],
                *(rows or [revenue_row()]),
            ],
            "Bandas/rol": [
                ["Nombre", "ROL", "septiembre 2026", "octubre 2026"],
                ["Ana", "Dev", "B1", "Baja"],
            ],
            "Master rates": [["Banda", "", "", "Tarifa"], ["B1", "", "", 10]],
        }
    )


def test_revenue_collections_and_invalid_rows_are_handled(monkeypatch):
    reader = repository(
        [
            revenue_row(amount="$1,000.00"),
            revenue_row(amount=200, status="Collected factoring"),
            revenue_row(amount=300, status="Invoiced"),
            revenue_row(amount=400, status="Invoiced factoring"),
            revenue_row(amount=500, status="Forecast"),
            revenue_row(amount=9000, day="2025-09-01"),
            revenue_row(pid="Total", amount=99999),
            revenue_row(amount="NaN"),
            revenue_row(amount="invalid"),
        ]
    )
    factory = Mock(return_value=reader)
    monkeypatch.setattr(revenue, "build_sheet_repository", factory)
    result = revenue.load_revenue()
    assert result["total"] == "1900.00"  # Forecast no forma parte del revenue.
    assert result["invoiced"] == "1900.00"
    assert result["collected"] == "1200.00"
    assert result["collections_percent"] == 63.16
    assert revenue.load_revenue() == result
    assert factory.call_count == 1


@pytest.mark.parametrize("pid", ["AIN.002 CR", "CCO.001 | CR"])
def test_financial_costs_use_existing_cr_history_and_task_rules(
    monkeypatch, pid
):
    reader = repository([revenue_row(pid=pid)])
    base = pid.split()[0]
    history = sheets(pid)
    history = {
        name: [
            [
                cell.replace("AIN.002", base) if isinstance(cell, str) else cell
                for cell in row
            ]
            for row in rows
        ]
        for name, rows in history.items()
    }
    api = client(
        [
            entry("correct", 15, "CR"),
            entry("base", 15, "General"),
            entry("outside", 25, "CR"),
        ]
    )
    api.projects = [type(api.projects[0])("c1", base)]
    loader = build_loader(api, history)
    monkeypatch.setattr(revenue_costs, "build_sheet_repository", lambda: reader)
    monkeypatch.setattr(
        revenue_costs, "build_clockify_loader", lambda repo: loader
    )
    result = revenue_costs.calculate_project_cost(pid)
    assert result["cost"] == 10
    assert result["hours"] == 1
    assert result["complete"] is True
    assert result["people"][0]["band_month"] == "septiembre 2026"
    assert cache.get(revenue_costs.key(pid))["entries"] == {"correct": 10}
    revenue_costs.calculate_project_cost(pid)
    assert len(api.report_calls) == 1


def test_missing_rate_is_partial_and_duplicate_hours_count_once(monkeypatch):
    reader = repository()
    records = [
        TimeEntry(
            "e1", "AIN.002 CR", "Unknown", datetime(2026, 9, 1), 2, False, 0
        )
    ]
    loader = Mock()
    loader.load_project.return_value = records * 2
    monkeypatch.setattr(revenue_costs, "build_sheet_repository", lambda: reader)
    monkeypatch.setattr(
        revenue_costs, "build_clockify_loader", lambda repo: loader
    )
    result = revenue_costs.calculate_project_cost("AIN.002 CR")
    assert result["hours"] == result["missing_hours"] == 2
    assert result["cost"] == 0
    assert result["complete"] is False


def test_summary_and_monthly_costs_do_not_double_count_shared_entries(
    monkeypatch,
):
    reader = repository([revenue_row("A", 100), revenue_row("B", 50)])
    monkeypatch.setattr(revenue_costs, "build_sheet_repository", lambda: reader)
    monkeypatch.setattr(
        monthly_profitability, "build_sheet_repository", lambda: reader
    )
    for pid in ["A", "B"]:
        cache.set(
            revenue_costs.key(pid),
            {
                "cost": 20,
                "hours": 2,
                "complete": True,
                "entries": {"shared": 20},
                "entry_months": {"shared": "2026-09"},
            },
        )
    assert revenue_costs.cost_summary()["cost"] == 20
    result = monthly_profitability.load_monthly_profitability()
    september = next(
        row for row in result["months"] if row["month"] == "2026-09"
    )
    assert september["revenue"] == 150
    assert september["cost"] == 20
    assert september["gross_profit"] == 130
    assert september["margin"] == 86.67
    # El ultimo corte conocido sobrevive a la expiracion: se borra tambien.
    cache.delete(revenue_costs.key("B"))
    cache.delete(revenue_costs.key("B") + ":last-known")
    assert (
        next(
            row
            for row in monthly_profitability.load_monthly_profitability()[
                "months"
            ]
            if row["month"] == "2026-09"
        )["partial"]
        is True
    )


def test_main_page_reads_financial_snapshot_without_source_queries(monkeypatch):
    monkeypatch.setattr(
        views,
        "load_portfolio",
        lambda: PortfolioLoad((), "", datetime(2026, 10, 14)),
    )
    snapshot = {
        "revenue": {"total": "100.00"},
        "costs": {"complete": True, "projects": []},
    }
    cache.set(financial_cache.snapshot_key(), snapshot)
    monkeypatch.setattr(
        financial_cache, "load_revenue", lambda: pytest.fail("External read")
    )
    html = views.ejecutiva(RequestFactory().get("/")).content.decode()
    assert 'id="monthly-profit-chart"' in html
    assert "pages/executive/main.js" in html


@override_settings(PORTAL_LOGIN_REQUIRED=True)
@pytest.mark.parametrize("view", [views.ingresos, views.costos_revenue])
def test_financial_endpoints_require_login(view):
    request = RequestFactory().get("/")
    request.user = SimpleNamespace(is_authenticated=False)
    assert view(request).status_code == 401


def test_precache_preserves_valid_snapshot_when_costs_fail(monkeypatch):
    previous = {"costs": {"complete": True}, "marker": "saved"}
    cache.set(financial_cache.snapshot_key(), previous)
    monkeypatch.setattr(financial_cache, "load_revenue", lambda: {})
    monkeypatch.setattr(
        financial_cache, "build_sheet_repository", lambda: repository()
    )
    monkeypatch.setattr(
        financial_cache,
        "calculate_project_cost",
        lambda pid, **kwargs: (_ for _ in ()).throw(ValueError("No rate")),
    )
    monkeypatch.setattr(
        financial_cache, "cost_summary", lambda **kwargs: {"complete": False}
    )
    monkeypatch.setattr(
        financial_cache,
        "load_monthly_profitability",
        lambda **kwargs: {"complete": False},
    )
    assert financial_cache.warm_financial()["ok"] is False
    assert cache.get(financial_cache.snapshot_key()) == previous


def test_precache_fills_all_financial_components_and_reuses_costs(monkeypatch):
    reader = repository()
    records = [
        TimeEntry(
            "e1",
            "AIN.002 CR",
            "Ana",
            datetime(2026, 9, 1),
            2,
            True,
            0,
        )
    ]
    loader = Mock()
    loader.load_project.return_value = records
    for module in [
        revenue,
        revenue_costs,
        monthly_profitability,
        financial_cache,
    ]:
        monkeypatch.setattr(module, "build_sheet_repository", lambda: reader)
    monkeypatch.setattr(
        revenue_costs, "build_clockify_loader", lambda repo: loader
    )
    assert financial_cache.warm_financial() == {"ok": True, "error": ""}
    snapshot = financial_cache.cached_financial_snapshot()
    assert snapshot["revenue"]["total"] == "100.00"
    assert snapshot["costs"]["cost"] == 20
    assert (
        next(
            row
            for row in snapshot["profitability"]["months"]
            if row["month"] == "2026-09"
        )["margin"]
        == 80
    )
    financial_cache.warm_financial()
    assert loader.load_project.call_count == 1
