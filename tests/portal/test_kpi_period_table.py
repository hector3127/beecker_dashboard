import pytest
from django.test import override_settings

from apps.portal import views
from tests.portal.test_views import stub_history


@pytest.fixture(autouse=True)
def anterior_screens(monkeypatch):
    """Estas pruebas leen la pantalla anterior (?vista=anterior)."""
    monkeypatch.setattr("apps.portal.pages.anterior_disponible", lambda: True)


@override_settings(PORTAL_LOGIN_REQUIRED=False)
@pytest.mark.parametrize(
    "query,end_month",
    [
        ("periodo=mes&mes=2026-02", "2026-02"),
        ("periodo=trimestre&anio=2026&trim=1", "2026-03"),
        ("periodo=anio&anio=2026", "2026-10"),
    ],
)
def test_manager_table_uses_the_exact_cut_selected_by_picker(
    client, monkeypatch, query, end_month
):
    stub_history(monkeypatch)
    response = client.get(
        "/operativa/kpis-delivery-managers/?vista=anterior&" + query
    )
    history = views.load_kpi_history(2026).history
    cut = next(item for item in history.months if item.key == end_month)
    assert response.status_code == 200
    assert response.context["kpis"] == cut.view
    assert response.context["cut_label"] == cut.cut_label
    assert response.context["period"].end_month == end_month
