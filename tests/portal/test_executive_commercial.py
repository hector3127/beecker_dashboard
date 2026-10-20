from datetime import date
from django.core.cache import cache
from tests.fakes import InMemorySheetRepository
from apps.portal.services import executive_commercial as executive
from apps.portal.services import commercial_view, executive_period as period


def test_commercial_uses_won_open_fx_and_close_date(monkeypatch):
    cache.clear()
    rows = [
        [
            "Account Name",
            "Opportunity Name",
            "Opportunity Stage",
            "Close Date",
            "Amount",
            "Currency",
        ],
        ["A", "Sale", "Closed Won", "2026-01-15", 100, "USD"],
        ["A", "Deal", "Proposal", "2026-01-20", 200, "EUR"],
        ["A", "Lost", "Closed Lost", "2026-01-20", 999, "USD"],
        ["A", "Old", "Closed Won", "2025-01-15", 9999, "USD"],
    ]
    r = InMemorySheetRepository(
        {"Backlog_Proyectos": rows, "DataRevenue": [["Status"]]}
    )
    monkeypatch.setattr(commercial_view, "build_sheet_repository", lambda: r)
    monkeypatch.setattr(executive, "build_sheet_repository", lambda: r)
    monkeypatch.setattr(
        commercial_view,
        "load_rates",
        lambda today: {"rates": {"USD": 1, "EUR": 2}, "date": "2026-10-01"},
    )
    token = period._current.set(
        period.parse({"periodo": "mes", "anio": "2026", "mes": "1"})
    )
    try:
        result = executive.commercial_summary()
        assert result["won"] == 100 and result["open"] == 100
        assert result["won_count"] == result["open_count"] == 1
        assert result["delivery"] == "0.00"
        assert result["start"] == "2026-01-01" and result["end"] == "2026-01-31"
    finally:
        period._current.reset(token)
    token = period._current.set(
        period.parse({"periodo": "mes", "anio": "2026", "mes": "2"})
    )
    try:
        result = executive.commercial_summary()
        assert result["won"] == 0 and result["open"] == 0
    finally:
        period._current.reset(token)
    cache.clear()


def test_future_delivery_uses_confirmed_g_h_and_selected_period():
    rows = [
        [
            "Status",
            "Cliente",
            "Oportunidad",
            "Servicio",
            "ID",
            "Horas",
            "Fecha",
            "USD",
        ]
    ]
    for status, day, amount in [
        ("Confirmed", "20/10/2026", 100),
        ("Confirmed", "19/10/2026", 200),
        ("Confirmed", "21/10/2026", "$1,200.50"),
        (" Confirmed ", "30/11/2026", 300),
        ("Confirmed", "01/01/2027", 9999),
        ("Invoiced", "30/11/2026", 400),
        ("Invoiced Factoring", "30/11/2026", 500),
        ("Collected", "30/11/2026", 600),
        ("Confirmed", "invalid", 700),
        ("Confirmed", "30/11/2026", "NaN"),
    ]:
        rows.append([status, "A", "Opportunity", "RaaS", "ID", 40, day, amount])
    reader = InMemorySheetRepository({"DataRevenue": rows})
    token = period._current.set(
        period.parse({"periodo": "anio", "anio": "2026"})
    )
    try:
        result = executive.future_delivery(reader, date(2026, 10, 20))
        assert result["delivery"] == "1500.50"
        assert result["delivery_count"] == 2
    finally:
        period._current.reset(token)
    token = period._current.set(
        period.parse({"periodo": "mes", "anio": "2026", "mes": "11"})
    )
    try:
        assert (
            executive.future_delivery(reader, date(2026, 10, 20))["delivery"]
            == "300.00"
        )
    finally:
        period._current.reset(token)


def test_finance_failure_preserves_commercial_sales(monkeypatch):
    cache.clear()
    monkeypatch.setattr(
        executive,
        "build_commercial_context",
        lambda params: {
            "won_usd": 1200,
            "won_count": 2,
            "open_usd": 300,
            "open_count": 1,
            "pending_usd": 0,
            "fx_date": "2026-10-20",
            "fx_error": "",
        },
    )

    def unavailable():
        raise ValueError("Finanzas no disponible")

    monkeypatch.setattr(executive, "future_delivery", unavailable)
    result = executive.commercial_summary()
    assert result["won"] == 1200
    assert result["delivery"] is None
    assert result["delivery_error"]
    cache.clear()


def test_open_opportunities_are_unique_and_match_closing_range(monkeypatch):
    cache.clear()
    header = [
        "Account Name",
        "Opportunity Name",
        "Opportunity Stage",
        "Close Date",
        "Amount",
        "Currency",
        "Deal ID",
        "Fecha ultimo seguimiento",
    ]
    rows = [
        header,
        ["A", "One", "Proposal", "2026-10-01", 100, "USD", "1", "2026-09-01"],
        ["A", "One", "Proposal", "2026-10-01", 100, "USD", "1", "2026-09-01"],
        [
            "A",
            "Closed",
            "Proposal",
            "2026-10-15",
            200,
            "USD",
            "2",
            "2026-09-01",
        ],
        [
            "A",
            "Closed",
            "Closed Won",
            "2026-10-15",
            200,
            "USD",
            "2",
            "2026-10-01",
        ],
        ["A", "Lost", "Closed Lost", "2026-10-15", 300, "USD", "3", ""],
        ["A", "Outside", "Proposal", "2026-11-01", 400, "USD", "4", ""],
        ["A", "Undated", "Proposal", "", 500, "USD", "5", ""],
        ["A", " No ID ", "Proposal", "2026-10-31", 50, "USD", "", ""],
        ["A", "no id", "Proposal", "2026-10-31", 50, "USD", "", ""],
        ["B", "No ID", "Proposal", "2026-10-01", 25, "USD", "", ""],
    ]
    reader = InMemorySheetRepository(
        {"Backlog_Proyectos": rows, "DataRevenue": [["Status"]]}
    )
    monkeypatch.setattr(
        commercial_view, "build_sheet_repository", lambda: reader
    )
    monkeypatch.setattr(executive, "build_sheet_repository", lambda: reader)
    token = period._current.set(
        period.parse(
            {"periodo": "rango", "desde": "2026-10-01", "hasta": "2026-10-31"}
        )
    )
    try:
        result = executive.commercial_summary()
        assert result["open"] == 175
        assert result["open_count"] == 3
        assert result["open_duplicates_removed"] == 3
    finally:
        period._current.reset(token)
        cache.clear()
