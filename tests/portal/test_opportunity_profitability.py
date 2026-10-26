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


def test_bookings_and_collection_use_the_selected_period(monkeypatch):
    from datetime import date

    from apps.portal.services.executive_period import ExecutivePeriod, _current

    cache.clear()
    monkeypatch.setattr(
        "apps.portal.services.opportunity_profitability.timezone.localdate",
        lambda: date(2026, 10, 22),
    )
    source = reader(
        ["Collected", "Acme", "OP", "RaaS", "DEV", 0, "2025-12-01", 100, "60%"],
        ["Invoiced", "Acme", "OP", "RaaS", "DEV", 0, "2026-09-01", 200, "60%"],
        [
            "Collected Factoring",
            "Acme",
            "OP",
            "RaaS",
            "DEV",
            0,
            "2026-09-02",
            300,
            "60%",
        ],
        ["Confirmed", "Acme", "OP", "RaaS", "DEV", 0, "2026-12-01", 400, "60%"],
        [
            "Collected",
            "Other",
            "OP",
            "RaaS",
            "OTHER",
            0,
            "2026-09-01",
            999,
            "60%",
        ],
        ["Cancelled", "Acme", "OP", "RaaS", "DEV", 0, "2026-09-01", 999, "60%"],
        [
            "Collected",
            "Acme",
            "OP",
            "Licenses",
            "LIC",
            0,
            "2026-09-01",
            999,
            "60%",
        ],
    )
    token = _current.set(
        ExecutivePeriod(date(2026, 9, 1), date(2026, 9, 30), "rango")
    )
    try:
        row = next(
            r
            for r in build_opportunities(source)["opportunities"]
            if r["account"] == "Acme"
        )
    finally:
        _current.reset(token)
    assert row["bookings"] == 500
    assert row["revenue"] == row["invoiced"] == 500
    assert row["collected"] == 300
    assert row["operated_revenue"] == 500
    assert row["operated_revenue_status"] == "assumed_service_date_g"
    assert row["actual_margin"] is None  # Missing costs never become zero.


def test_operated_revenue_excludes_future_service_but_keeps_margin_basis(
    monkeypatch,
):
    from datetime import date

    monkeypatch.setattr(
        "apps.portal.services.opportunity_profitability.timezone.localdate",
        lambda: date(2026, 10, 22),
    )
    cache.clear()
    cache.set(
        key("DEV"), {"complete": True, "cost": 100, "entries": {"a": 100}}
    )
    row = build_opportunities(
        reader(
            [
                "Confirmed",
                "Acme",
                "OP",
                "RaaS",
                "DEV",
                0,
                "2026-09-01",
                200,
                "60%",
            ],
            [
                "Confirmed",
                "Acme",
                "OP",
                "RaaS",
                "DEV",
                0,
                "2026-12-01",
                300,
                "60%",
            ],
        )
    )["opportunities"][0]
    assert row["bookings"] == row["revenue"] == 500
    assert row["operated_revenue"] == 200
    assert row["collected"] == row["invoiced"] == 0
    assert row["actual_margin"] == 80
    cache.clear()


def test_a_row_without_opportunity_has_no_bookings_instead_of_zero():
    cache.clear()
    rows = build_opportunities(
        reader(
            ["Confirmed", "Acme", "", "RaaS", "DEV", 0, "2026-09-01", 50, ""]
        )
    )["opportunities"]

    assert rows[0]["name"] == "Sin oportunidad"
    assert rows[0]["bookings"] is None
    cache.clear()


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


def test_screen_serves_sold_actual_and_deviation(monkeypatch, client):
    from apps.portal.services import (
        executive_refresh,
        opportunity_profitability,
    )

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

    response = client.get(
        "/api/v1/screens/margenes/"
        "?periodo=rango&desde=2026-01-01&hasta=2026-09-30"
    )

    assert response.status_code == 200
    [row] = response.json()["data"]["opportunities"]
    assert (row["name"], row["sold_margin"]) == ("OP.1", 60)
    assert row["deviation_pp"] is None  # sin costo no hay desviacion


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


def test_unformatted_sheet_percentages_above_one_keep_their_scale():
    from decimal import Decimal

    for raw, expected in [
        (1.265, 126.5),
        (Decimal("1.3023"), 130.23),
        (1.7262, 172.62),
        (0.6, 60),
        (1, 100),
        (0, 0),
        (-0.171, -17.1),
        (-1.265, -126.5),
        ("126.5%", 126.5),
    ]:
        assert sold_percent(raw, fractional=True) == expected
    assert sold_percent(None, fractional=True) is None
    assert sold_percent(float("nan"), fractional=True) is None


def test_aer_monthly_revenue_and_shared_cost_keep_margin_percent_scale():
    from datetime import date

    from apps.portal.services.executive_period import ExecutivePeriod, _current

    cache.clear()
    token = _current.set(
        ExecutivePeriod(date(2026, 1, 1), date(2026, 12, 31), "anio")
    )
    try:
        source_rows = []
        for offset in range(24):
            month = 2026 * 12 + 8 + offset
            source_rows.append(
                [
                    "Collected" if offset < 12 else "Confirmed",
                    "Aeromexico Cargo",
                    "AER-MX-RAAS-010",
                    "RaaS",
                    "ROC.AEC.001",
                    0,
                    date(month // 12, month % 12 + 1, 23).isoformat(),
                    615.6,
                    1.265,
                ]
            )
        source_rows.append(
            [
                "Collected",
                "Aeromexico Cargo",
                "OTHER",
                "RaaS",
                "ROC.AEC.001",
                0,
                "2026-01-01",
                100,
                "60%",
            ]
        )
        cache.set(
            key("ROC.AEC.001"),
            {
                "complete": False,
                "cost": 3550.26,
                "hours": 332.18,
                "entries": {"shared-entry": 3550.26},
            },
        )
        data = build_opportunities(reader(*source_rows))
        row = next(
            r for r in data["opportunities"] if r["name"] == "AER-MX-RAAS-010"
        )
        assert row["sold_margin"] == 126.5
        assert row["bookings"] == 2462.4
        assert row["revenue"] == row["invoiced"] == row["collected"] == 2462.4
        assert row["cost"] == 3550.26
        assert row["actual_margin"] == -44.18
        assert row["deviation_pp"] == -170.68
        assert row["allocation_pending"] is True
        assert row["partial"] is True
    finally:
        _current.reset(token)
        cache.clear()


def test_bookings_use_inclusive_date_boundaries_and_switch_periods():
    from datetime import date

    from apps.portal.services.executive_period import ExecutivePeriod, _current

    source = reader(
        *[
            ["Confirmed", "Acme", "OP", "RaaS", "DEV", 0, day, amount, "60%"]
            for day, amount in [
                ("2025-12-31", 999),
                ("2026-01-01", 100),
                ("2026-01-31", 200),
                ("2026-02-01", 400),
                ("2026-12-31", 800),
                ("2027-01-01", 999),
            ]
        ]
    )
    for start, end, expected in [
        (date(2026, 1, 1), date(2026, 12, 31), 1500),
        (date(2026, 1, 1), date(2026, 1, 31), 300),
        (date(2026, 2, 1), date(2026, 2, 1), 400),
    ]:
        token = _current.set(ExecutivePeriod(start, end, "rango"))
        try:
            row = build_opportunities(source)["opportunities"][0]
            assert row["bookings"] == row["revenue"] == expected
        finally:
            _current.reset(token)


def test_account_totals_deduplicate_shared_entries_and_weight_sold_margin():
    cache.clear()
    cache.set(
        key("SHARED"),
        {
            "complete": True,
            "cost": 100,
            "hours": 10,
            "entries": {"same-entry": 100},
        },
    )
    source = reader(
        [
            "Collected",
            "Acme",
            "OP1",
            "RaaS",
            "SHARED",
            0,
            "2026-01-01",
            100,
            "40%",
        ],
        [
            "Collected",
            "Acme",
            "OP2",
            "RaaS",
            "SHARED",
            0,
            "2026-01-01",
            300,
            "60%",
        ],
    )
    result = build_opportunities(source)
    account = result["accounts"][0]
    assert account["bookings"] == account["period_revenue"] == 400
    assert account["invoiced"] == account["collected"] == 400
    assert sum(r["cost"] for r in result["opportunities"]) == 200
    assert account["cost"] == 100
    assert account["actual_margin"] == 75
    assert account["sold_margin"] == 55
    assert account["deviation_pp"] == 20
    assert account["partial"] is False
    cache.clear()


def test_account_totals_deduplicate_overlapping_project_entries():
    cache.clear()
    cache.set(
        key("PARENT"),
        {
            "complete": True,
            "cost": 70,
            "entries": {"common": 50, "other": 20},
        },
    )
    cache.set(
        key("CHILD"),
        {
            "complete": True,
            "cost": 50,
            "entries": {"common": 50},
        },
    )
    source = reader(
        [
            "Collected",
            "Acme",
            "OP1",
            "RaaS",
            "PARENT",
            0,
            "2026-01-01",
            100,
            "40%",
        ],
        [
            "Collected",
            "Acme",
            "OP2",
            "RaaS",
            "CHILD",
            0,
            "2026-01-01",
            100,
            "60%",
        ],
    )
    account = build_opportunities(source)["accounts"][0]
    assert account["cost"] == 70
    assert account["actual_margin"] == 65
    cache.clear()


def test_account_partial_totals_keep_known_values_and_unknowns_distinct():
    cache.clear()
    cache.set(
        key("KNOWN"),
        {
            "complete": False,
            "cost": 20,
            "entries": {"known": 20},
        },
    )
    source = reader(
        [
            "Collected",
            "Acme",
            "OP1",
            "RaaS",
            "KNOWN",
            0,
            "2026-01-01",
            100,
            "40%",
        ],
        [
            "Collected",
            "Acme",
            "OP2",
            "RaaS",
            "UNKNOWN",
            0,
            "2026-01-01",
            100,
            "",
        ],
        [
            "Collected",
            "Other",
            "OP3",
            "RaaS",
            "OTHER",
            0,
            "2026-01-01",
            100,
            "60%",
        ],
    )
    accounts = {
        a["account"]: a for a in build_opportunities(source)["accounts"]
    }
    assert accounts["Acme"]["cost"] == 20
    assert accounts["Acme"]["actual_margin"] == 90
    assert accounts["Acme"]["sold_margin"] == 40
    assert accounts["Acme"]["sold_partial"] is True
    assert accounts["Acme"]["cost_partial"] is True
    assert accounts["Other"]["cost"] is None
    assert accounts["Other"]["actual_margin"] is None
    cache.clear()
