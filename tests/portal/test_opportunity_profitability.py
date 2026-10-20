from django.core.cache import cache
from apps.portal.services.opportunity_profitability import (
    build_opportunities,
    sold_percent,
)
from apps.portal.services.revenue_costs import key
from tests.fakes import InMemorySheetRepository

HEADER = [
    "Status",
    "Client",
    "Opportunity",
    "Service",
    "ID",
    "Hours",
    "Date",
    "USD",
    "Gross Margin",
]


def reader(*rows):
    return InMemorySheetRepository({"DataRevenue": [HEADER, *rows]})


def test_opportunity_combines_project_ids_and_all_finance_statuses():
    cache.clear()
    cache.set(
        key("DEV.1"),
        {"complete": True, "cost": 30, "hours": 3, "entries": {"a": 30}},
    )
    cache.set(
        key("ROC.1"),
        {"complete": True, "cost": 50, "hours": 5, "entries": {"b": 50}},
    )
    data = build_opportunities(
        reader(
            [
                "Collected",
                "Acme",
                "OP.1",
                "RaaS",
                "DEV.1",
                0,
                "2026-01-01",
                100,
                "60%",
            ],
            [
                "Confirmed",
                "Acme",
                "OP.1",
                "Support Desk",
                "ROC.1",
                0,
                "2026-02-01",
                100,
                0.6,
            ],
        )
    )
    row = data["opportunities"][0]
    assert row["revenue"] == 200 and row["invoiced"] == 100
    assert (
        row["cost"] == 80 and row["actual_margin"] == row["sold_margin"] == 60
    )
    assert row["deviation_pp"] == 0 and not row["partial"]
    assert row["ids"] == ["DEV.1", "ROC.1"]
    assert row["projects"][0]["revenue"] == 100
    assert row["projects"][0]["gross_profit"] == 70
    assert row["projects"][0]["margin"] == 70
    assert row["projects"][1]["margin"] == 50
    cache.clear()


def test_missing_cost_never_becomes_a_false_hundred_percent_margin():
    cache.clear()
    row = build_opportunities(
        reader(
            [
                "Confirmed",
                "Acme",
                "OP.1",
                "RaaS",
                "MISSING",
                0,
                "2026-01-01",
                100,
                "60%",
            ]
        )
    )["opportunities"][0]
    assert (
        row["cost"] is None and row["actual_margin"] is None and row["partial"]
    )


def test_shared_project_cost_is_not_duplicated_between_opportunities():
    cache.clear()
    cache.set(
        key("ROC.001"), {"complete": True, "cost": 100, "entries": {"a": 100}}
    )
    rows = build_opportunities(
        reader(
            *[
                [
                    "Confirmed",
                    "Acme",
                    name,
                    "RaaS",
                    "ROC.001",
                    0,
                    "2026-01-01",
                    100,
                    "60%",
                ]
                for name in ["OP.1", "OP.2"]
            ]
        )
    )["opportunities"]
    assert all(r["cost"] == 100 and r["partial"] for r in rows)
    assert all("compartido" in r["projects"][0]["issues"][0] for r in rows)
    assert all(r["projects"][0]["cost"] == 100 for r in rows)
    assert all(
        r["allocation_pending"] and r["available_project_cost"] == 100
        for r in rows
    )
    assert all(r["projects"][0]["margin"] == 0 for r in rows)
    from apps.portal.services.opportunity_profitability import (
        opportunity_summary,
    )

    assert opportunity_summary(rows)["actual_count"] == 0
    cache.clear()


def test_scope_conflicting_margins_and_partial_costs():
    cache.clear()
    cache.set(key("DEV"), {"complete": False, "cost": 20, "entries": {"a": 20}})
    data = build_opportunities(
        reader(
            [
                "Confirmed",
                "Acme",
                "OP",
                "RaaS",
                "DEV",
                0,
                "2026-01-01",
                100,
                "60%",
            ],
            [
                "Collected",
                "Acme",
                "OP",
                "RaaS",
                "DEV",
                0,
                "2026-02-01",
                100,
                "50%",
            ],
            [
                "Collected",
                "Acme",
                "LICENSE",
                "Licenses",
                "LIC",
                0,
                "2026-01-01",
                900,
                "90%",
            ],
            [
                "Collected",
                "Acme",
                "SAAS",
                "SaaS",
                "SAS",
                0,
                "2026-01-01",
                900,
                "90%",
            ],
            [
                "Collected",
                "Acme",
                "SPECIAL",
                "Servicios especializados",
                "SP",
                0,
                "2026-01-01",
                900,
                "90%",
            ],
        )
    )
    (row,) = data["opportunities"]
    assert row["cost"] == 20 and row["actual_margin"] == 90 and row["partial"]
    assert row["sold_margin"] is None and row["deviation_pp"] is None
    cache.clear()


def test_percent_formats_and_real_zero():
    assert sold_percent("60%") == sold_percent(0.6) == sold_percent(60) == 60
    assert sold_percent("0%") == 0
    assert sold_percent("") is None


def test_view_renders_sold_actual_and_deviation(monkeypatch):
    from django.test import RequestFactory, override_settings
    from apps.portal import views
    from apps.portal.services import opportunity_profitability
    from apps.portal.services import executive_refresh

    monkeypatch.setattr(
        executive_refresh, "request_refresh", lambda **kwargs: None
    )
    monkeypatch.setattr(
        opportunity_profitability,
        "build_sheet_repository",
        lambda: reader(
            [
                "Confirmed",
                "Acme",
                "OP.1",
                "RaaS",
                "MISSING",
                0,
                "2026-01-01",
                100,
                "60%",
            ]
        ),
    )
    with override_settings(PORTAL_LOGIN_REQUIRED=False):
        response = views.oportunidades_financieras(
            RequestFactory().get(
                "/ejecutiva/oportunidades/?periodo=rango&desde=2026-01-01&hasta=2026-09-30"
            )
        )
    assert response.status_code == 200
    html = response.content.decode()
    assert "Margen vendido" in html and "Desviación" in html and "OP.1" in html
    assert "60,00%" in html or "60.00%" in html


def test_cost_detail_opens_opportunity_hierarchy_by_default(monkeypatch):
    from django.test import RequestFactory
    from apps.portal import views
    from django.http import HttpResponse

    captured = []
    monkeypatch.setattr(
        views,
        "oportunidades_financieras",
        lambda request: (
            captured.append(request.GET.get("nombre"))
            or HttpResponse("hierarchy")
        ),
    )
    response = views.costos_detalle(
        RequestFactory().get(
            "/ejecutiva/costos/detalle/?nombre=Heineken+Mexico"
        )
    )
    assert response.content == b"hierarchy"
    assert captured == ["Heineken Mexico"]


def test_summary_uses_only_available_values_and_matched_deviations():
    from apps.portal.services.opportunity_profitability import (
        opportunity_summary,
    )

    result = opportunity_summary(
        [
            {
                "partial": False,
                "cost": 10,
                "sold_margin": 60,
                "actual_margin": 40,
                "deviation_pp": -20,
            },
            {
                "partial": True,
                "cost": 5,
                "sold_margin": None,
                "actual_margin": 80,
                "deviation_pp": None,
            },
            {
                "partial": True,
                "cost": None,
                "sold_margin": 20,
                "actual_margin": None,
                "deviation_pp": None,
            },
        ]
    )
    assert result["complete"] == 1 and result["pending"] == 2
    assert result["sold"] == 40 and result["actual"] == 60
    assert result["deviation"] == -20 and result["deviation_count"] == 1


def test_known_ids_keep_partial_margin_when_other_ids_are_missing_or_shared():
    cache.clear()
    cache.set(
        key("KNOWN"),
        {"complete": True, "cost": 50, "hours": 5, "entries": {"a": 50}},
    )
    cache.set(
        key("SHARED"),
        {"complete": True, "cost": 90, "hours": 9, "entries": {"b": 90}},
    )
    result = build_opportunities(
        reader(
            [
                "Confirmed",
                "Acme",
                "OP",
                "RaaS",
                "KNOWN",
                0,
                "2026-01-01",
                100,
                "60%",
            ],
            [
                "Confirmed",
                "Acme",
                "OP",
                "RaaS",
                "MISSING",
                0,
                "2026-01-01",
                100,
                "60%",
            ],
            [
                "Confirmed",
                "Acme",
                "OP",
                "RaaS",
                "SHARED",
                0,
                "2026-01-01",
                100,
                "60%",
            ],
            [
                "Confirmed",
                "Acme",
                "OTHER",
                "RaaS",
                "SHARED",
                0,
                "2026-01-01",
                100,
                "60%",
            ],
        )
    )
    row = next(o for o in result["opportunities"] if o["name"] == "OP")
    assert row["cost"] == 140
    assert row["actual_margin"] == 53.33
    assert row["deviation_pp"] == -6.67
    assert row["partial"] and row["allocation_pending"]
    cache.clear()


def test_old_zero_and_future_links_do_not_block_current_opportunity_costs():
    cache.clear()
    cache.set(
        key("AER.SBM.003"),
        {
            "complete": True,
            "cost": 19000,
            "hours": 1636,
            "entries": {"a": 19000},
        },
    )
    data = build_opportunities(
        reader(
            [
                "Collected",
                "Arca",
                "ARC-MX-AER-009",
                "RPA Cells",
                "AER.SBM.003",
                0,
                "2025-07-30",
                4000,
                "60%",
            ],
            [
                "Collected",
                "Arca",
                "ARC-MX-AER-011",
                "RPA Cells",
                "AER.SBM.003",
                0,
                "2026-02-25",
                0,
                "60%",
            ],
            [
                "Collected",
                "Arca",
                "ARC-MX-AER-011",
                "RPA Cells",
                "AER.SBM.003",
                0,
                "2026-12-30",
                291.67,
                "60%",
            ],
            [
                "Invoiced",
                "Arca",
                "ARC-MX-AER-012",
                "RPA Cells",
                "AER.SBM.003",
                0,
                "2026-09-30",
                1813.32,
                "66.54%",
            ],
        )
    )
    row = next(
        r for r in data["opportunities"] if r["name"] == "ARC-MX-AER-012"
    )
    assert row["cost"] == 19000 and row["actual_margin"] is not None
    assert not row["allocation_pending"]
    future = next(
        r for r in data["opportunities"] if r["name"] == "ARC-MX-AER-011"
    )
    assert (
        future["cost"] == 19000
        and future["partial"]
        and future["allocation_pending"]
    )
    cache.clear()
