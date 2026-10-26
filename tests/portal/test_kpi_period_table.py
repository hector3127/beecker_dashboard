import pytest
from django.test import RequestFactory

from apps.portal import views
from tests.portal.test_views import stub_history


@pytest.mark.parametrize(
    "query,end_month",
    [
        ("periodo=mes&mes=2026-02", "2026-02"),
        ("periodo=trimestre&anio=2026&trim=1", "2026-03"),
        ("periodo=anio&anio=2026", "2026-10"),
    ],
)
def test_manager_table_uses_the_exact_cut_selected_by_picker(
    monkeypatch, query, end_month
):
    stub_history(monkeypatch)
    context = views.kpi_context(
        RequestFactory().get("/api/v1/screens/kpis-dm/?" + query)
    )
    history = views.load_kpi_history(2026).history
    cut = next(item for item in history.months if item.key == end_month)
    assert context["kpis"] == cut.view
    assert context["cut_label"] == cut.cut_label
    assert context["period"].end_month == end_month
