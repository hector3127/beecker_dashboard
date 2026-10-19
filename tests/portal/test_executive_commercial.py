from django.core.cache import cache

from apps.portal.services import commercial_view
from apps.portal.services import executive_commercial as executive
from apps.portal.services import executive_period as period
from tests.fakes import InMemorySheetRepository


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
    r = InMemorySheetRepository({"Backlog_Proyectos": rows})
    monkeypatch.setattr(commercial_view, "build_sheet_repository", lambda: r)
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
        assert result["delivery"] is None
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
