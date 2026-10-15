from apps.portal.services import executive_period as period
from apps.portal.services.project_profitability import add_project_revenue
from tests.fakes import InMemorySheetRepository


def source():
    return InMemorySheetRepository(
        {
            "DataRevenue": [
                ["Status", "Account", "", "", "ID", "", "Date", "USD"],
                ["Collected", "Acme", "", "", "P1", "", "2026-01-10", 100],
                ["Confirmed", "Acme", "", "", "P1", "", "2026-02-10", 300],
                ["Forecast", "Acme", "", "", "P1", "", "2026-01-10", 999],
                ["Collected", "Other", "", "", "P1", "", "2026-01-10", 50],
                ["Collected", "Acme", "", "", "P1", "", "2025-01-10", 999],
                ["Collected", "Acme", "", "", "ZERO", "", "2026-01-10", 0],
            ]
        }
    )


def test_project_revenue_filters_account_period_and_status():
    token = period._current.set(
        period.parse({"periodo": "mes", "anio": "2026", "mes": "1"})
    )
    try:
        result = add_project_revenue(
            {"projects": [{"id": "P1", "cost": 20, "complete": True}]},
            source(),
            "Acme",
        )
        p = result["projects"][0]
        assert (
            p["revenue"] == 100
            and p["gross_profit"] == 80
            and p["margin"] == 80
        )
        assert not p["margin_provisional"]
    finally:
        period._current.reset(token)


def test_missing_zero_and_partial_values_do_not_invent_margins():
    result = add_project_revenue(
        {
            "projects": [
                {"id": "P1", "cost": 20, "complete": False},
                {"id": "ZERO", "cost": 10, "complete": True},
                {"id": "ABSENT", "cost": 0, "complete": True},
                {"id": "P1", "cost": None, "complete": False},
            ]
        },
        source(),
        "Acme",
    )
    a, zero, missing, pending = result["projects"]
    assert a["revenue"] == 400 and a["margin"] == 95 and a["margin_provisional"]
    assert zero["revenue"] == 0 and zero["margin"] is None
    assert (
        missing["revenue"] == 0
        and missing["margin"] is None
        and missing["no_revenue"]
    )
    assert pending["revenue"] == 400 and pending["margin"] is None
