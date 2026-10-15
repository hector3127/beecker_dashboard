from django.core.cache import cache

from apps.portal.services.account_profitability import account_profitability
from apps.portal.services.project_profitability import add_project_revenue
from apps.portal.services.revenue_costs import key, project_ids
from tests.fakes import InMemorySheetRepository
from tests.portal.test_kpi_sources import MPB


def test_unbilled_project_reduces_account_margin_without_adding_revenue():
    cache.clear()
    r = InMemorySheetRepository(
        {
            "MPB": [
                MPB,
                [
                    "Acme",
                    "GIFT",
                    "Gift",
                    "AER",
                    "2026-01-01",
                    "2026-12-31",
                    "En progreso",
                    "Ana",
                    100,
                ],
            ],
            "DataRevenue": [
                ["Status", "Account", "", "", "ID", "", "Date", "USD"],
                ["Collected", "Acme", "", "", "PAID", "", "2026-01-01", 200],
            ],
        }
    )
    assert project_ids(r, "Acme") == ["GIFT", "PAID"]
    cache.set(key("PAID"), {"complete": True, "entries": {"paid": 50}})
    cache.set(key("GIFT"), {"complete": True, "entries": {"gift": 100}})
    a = account_profitability(r)["accounts"][0]
    assert a["revenue"] == 200 and a["cost"] == 150 and a["margin"] == 25
    assert a["classification"] == "unhealthy"
    gift = add_project_revenue(
        {"id": "GIFT", "cost": 100, "complete": True}, r, "Acme"
    )
    assert (
        gift["revenue"] == 0
        and gift["gross_profit"] == -100
        and gift["margin"] is None
    )
    cache.clear()


def test_zero_revenue_account_with_costs_is_unhealthy_not_profitable():
    cache.clear()
    r = InMemorySheetRepository(
        {
            "MPB": [
                MPB,
                [
                    "Gift account",
                    "GIFT",
                    "Gift",
                    "AER",
                    "2026-01-01",
                    "2026-12-31",
                    "En progreso",
                    "Ana",
                    100,
                ],
            ],
            "DataRevenue": [[]],
        }
    )
    cache.set(key("GIFT"), {"complete": True, "entries": {"gift": 100}})
    a = account_profitability(r)["unhealthy"][0]
    assert (
        a["revenue"] == 0 and a["gross_profit"] == -100 and a["margin"] is None
    )
    cache.clear()


def test_generic_mpb_name_maps_by_exact_historical_id_to_existing_country():
    cache.clear()
    history = [
        [],
        ["", "Arca Continental Mexico", "GIFT", "", "", "", "", "", ""],
    ]
    r = InMemorySheetRepository(
        {
            "MPB": [
                MPB,
                [
                    "ARCA CONTINENTAL",
                    "GIFT",
                    "Gift",
                    "AER",
                    "2026-01-01",
                    "2026-12-31",
                    "En progreso",
                    "Ana",
                    100,
                ],
            ],
            "Historico_Proyectos": history,
            "DataRevenue": [
                ["Status", "Account", "", "", "ID", "", "Date", "USD"],
                [
                    "Collected",
                    "Arca Continental Mexico",
                    "",
                    "",
                    "PAID",
                    "",
                    "2026-01-01",
                    200,
                ],
                [
                    "Collected",
                    "Arca Continental Peru",
                    "",
                    "",
                    "PERU",
                    "",
                    "2026-01-01",
                    100,
                ],
            ],
        }
    )
    assert project_ids(r, "Arca Continental Mexico") == ["GIFT", "PAID"]
    assert project_ids(r, "Arca Continental Peru") == ["PERU"]
    cache.set(key("PAID"), {"complete": True, "entries": {"paid": 50}})
    cache.set(key("GIFT"), {"complete": True, "entries": {"gift": 100}})
    cache.set(key("PERU"), {"complete": True, "entries": {"peru": 10}})
    accounts = account_profitability(r)["accounts"]
    assert len(accounts) == 2
    mexico = next(a for a in accounts if a["name"] == "Arca Continental Mexico")
    assert mexico["cost"] == 150 and mexico["margin"] == 25
    cache.clear()


def test_variant_without_revenue_uses_base_project_account():
    cache.clear()
    r = InMemorySheetRepository(
        {
            "MPB": [
                MPB,
                [
                    "Cadena Comercial Oxxo.",
                    "CCO.002_S1",
                    "Gift",
                    "AER",
                    "2026-01-01",
                    "2026-12-31",
                    "En progreso",
                    "Ana",
                    100,
                ],
            ],
            "DataRevenue": [
                ["Status", "Account", "", "", "ID", "", "Date", "USD"],
                [
                    "Collected",
                    "Cadena Comercial Oxxo",
                    "",
                    "",
                    "CCO.002",
                    "",
                    "2026-01-01",
                    200,
                ],
            ],
        }
    )
    assert project_ids(r, "Cadena Comercial Oxxo") == ["CCO.002"]
    cache.set(
        key("CCO.002"), {"complete": True, "entries": {"base": 50, "s1": 100}}
    )
    cache.set(key("CCO.002_S1"), {"complete": True, "entries": {"s1": 100}})
    accounts = account_profitability(r)["accounts"]
    assert len(accounts) == 1 and accounts[0]["name"] == "Cadena Comercial Oxxo"
    assert accounts[0]["cost"] == 150 and accounts[0]["margin"] == 25
    cache.clear()


def test_only_variants_registered_in_revenue_are_separated():
    cache.clear()
    r = InMemorySheetRepository(
        {
            "MPB": [
                MPB,
                [
                    "Oxxo",
                    "CCO.002_S1",
                    "Scope 1",
                    "AER",
                    "2026-01-01",
                    "2026-12-31",
                    "En progreso",
                    "Ana",
                    100,
                ],
                [
                    "Oxxo",
                    "CCO.002_S2",
                    "Scope 2",
                    "AER",
                    "2026-01-01",
                    "2026-12-31",
                    "En progreso",
                    "Ana",
                    100,
                ],
            ],
            "DataRevenue": [
                ["Status", "Account", "", "", "ID", "", "Date", "USD"],
                ["Collected", "Oxxo", "", "", "CCO.002", "", "2026-01-01", 200],
                [
                    "Collected",
                    "Oxxo",
                    "",
                    "",
                    "CCO.002_S1",
                    "",
                    "2026-01-01",
                    100,
                ],
            ],
        }
    )
    assert project_ids(r, "Oxxo") == ["CCO.002", "CCO.002_S1"]
    cache.clear()


def test_historical_inventory_uses_only_a_to_i_and_selected_period():
    from apps.portal.services import executive_period as period

    r = InMemorySheetRepository(
        {
            "DataRevenue": [[]],
            "Historico_Proyectos": [
                [],
                [
                    "Ana",
                    "Acme",
                    "P1",
                    "IXB",
                    "One",
                    "",
                    "Discovery OP",
                    "2026-05-01",
                    "2026-05-30",
                    "",
                    "",
                    "Wrong account",
                    "WRONG",
                ],
                [
                    "Ana",
                    "Acme",
                    "P1",
                    "IXB",
                    "One",
                    "",
                    "Completed",
                    "2026-06-01",
                    "2026-06-15",
                ],
                [
                    "Ana",
                    "Acme",
                    "OLD",
                    "IXB",
                    "Old",
                    "",
                    "Completed",
                    "2025-01-01",
                    "2025-06-15",
                ],
            ],
        }
    )
    token = period._current.set(
        period.parse({"periodo": "mes", "anio": "2026", "mes": "5"})
    )
    try:
        assert project_ids(r, "Acme") == ["P1"]
        assert project_ids(r, "Wrong account") == []
    finally:
        period._current.reset(token)


def test_generic_arca_costs_belong_to_mexico_and_never_peru():
    r = InMemorySheetRepository(
        {
            "MPB": [
                MPB,
                [
                    "ARCA CONTINENTAL",
                    "GIFT",
                    "Gift",
                    "AER",
                    "2026-01-01",
                    "2026-12-31",
                    "En progreso",
                    "Ana",
                    100,
                ],
            ],
            "DataRevenue": [
                ["Status", "Account", "", "", "ID", "", "Date", "USD"],
                [
                    "Collected",
                    "Arca Continental Mexico",
                    "",
                    "",
                    "MEX",
                    "",
                    "2026-01-01",
                    200,
                ],
                [
                    "Collected",
                    "Arca Continental Peru",
                    "",
                    "",
                    "PERU",
                    "",
                    "2026-01-01",
                    100,
                ],
            ],
        }
    )
    assert project_ids(r, "Arca Continental Mexico") == ["GIFT", "MEX"]
    assert project_ids(r, "Arca Continental Peru") == ["PERU"]
    cache.clear()
    cache.set(key("GIFT"), {"complete": True, "entries": {"gift": 50}})
    cache.set(key("MEX"), {"complete": True, "entries": {"mex": 25}})
    cache.set(key("PERU"), {"complete": True, "entries": {"peru": 10}})
    accounts = account_profitability(r)["accounts"]
    assert len(accounts) == 2
    mexico = next(a for a in accounts if a["name"] == "Arca Continental Mexico")
    assert mexico["cost"] == 75 and mexico["revenue"] == 200
    cache.clear()
