from datetime import date

import pytest
from django.utils import timezone
from playwright.sync_api import expect

from tests.portal.test_kpi_eva import stub_compliance_history


@pytest.mark.django_db(transaction=True)
def test_rango_mensual_conserva_grafica_y_avisa_si_falta_captura(
    portal, datos, monkeypatch
):
    today = date(2026, 10, 22)
    monkeypatch.setattr(timezone, "localdate", lambda: today)
    stub_compliance_history(monkeypatch, today)
    portal.goto(portal.base + "/operativa/kpis-delivery-managers/?mes=2026-10")
    table = portal.locator("#kpi-month-history")
    expect(table).to_be_visible()
    assert table.locator("thead tr").first.locator("th").count() == 4
    expect(portal.locator(".two #kpi-month-history")).to_be_visible()
    chart = portal.locator(".two > .card").nth(1).inner_text()
    expect(portal.locator(".kc").first).to_contain_text("Mes anterior sin captura comparable")
    portal.get_by_label("Desde mes", exact=True).select_option("1")
    portal.get_by_label("Hasta mes", exact=True).select_option("12")
    portal.get_by_role("button", name="Consultar", exact=True).click()
    expect(table.locator("thead tr").first.locator("th")).to_have_count(11)
    assert portal.locator(".two > .card").nth(1).inner_text() == chart
    portal.get_by_label("Desde mes", exact=True).select_option("9")
    portal.get_by_label("Hasta mes", exact=True).select_option("10")
    portal.get_by_role("button", name="Consultar", exact=True).click()
    expect(table.locator("thead tr").first.locator("th")).to_have_count(3)
