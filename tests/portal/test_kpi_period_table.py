from django.test import RequestFactory

from apps.portal import views
from tests.portal.kpi_cut_support import stub_inventory


def test_cut_does_not_change_annual_history(monkeypatch):
    stub_inventory(monkeypatch)
    first = views.kpi_context(
        RequestFactory().get("/?corte=2026-02-15&history_year=2026")
    )
    second = views.kpi_context(
        RequestFactory().get("/?corte=2026-09-30&history_year=2026")
    )
    assert first["month_matrix"] == second["month_matrix"]
    assert first["quarter_matrix"] == second["quarter_matrix"]
    assert first["chart"] == second["chart"]
    assert first["kpis"].totals.total == 2
    assert second["kpis"].totals.total == 3
