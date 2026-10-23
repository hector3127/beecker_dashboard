"""KPIs de Delivery Managers en un navegador real: periodo, grafica y tablas."""

import re

import pytest
from playwright.sync_api import expect

from tests.portal.test_views import portfolio, stub_history, stub_portfolio

pytestmark = pytest.mark.django_db(transaction=True)

PAGE = "/operativa/kpis-delivery-managers/"


@pytest.fixture(autouse=True)
def sources(monkeypatch):
    stub_portfolio(monkeypatch, portfolio())
    stub_history(monkeypatch)


def test_page_uses_the_modular_frontend_with_the_previous_layout(portal):
    portal.goto(portal.base + PAGE)

    expect(
        portal.get_by_role("heading", name="KPIs de Delivery Managers")
    ).to_be_visible()
    assert portal.locator("main").count() == 1
    assert portal.locator("link[href*='pages/kpis_dm.css']").count() == 1
    assert portal.locator(".kp .kc").count() == 4
    expect(portal.locator(".tabs a.on")).to_have_text(
        "KPIs de Delivery Managers"
    )
    rows = portal.locator(".two table tbody tr")
    expect(rows).to_have_count(2)
    expect(rows.first).to_contain_text("Ana")
    assert portal.locator("#kpi-month-history").count() == 1
    assert portal.locator("#kpi-quarter-history").count() == 1


def test_tabs_and_manager_links_lead_to_their_screens(portal):
    portal.goto(f"{portal.base}{PAGE}?periodo=anio&anio=2026")

    tab = portal.get_by_role("link", name="Facturabilidad por recurso")
    assert "periodo=anio" in tab.get_attribute("href")
    portal.locator(".two table").get_by_role("link", name="Ana").click()
    portal.wait_for_url(re.compile(r"/operativa/delivery-manager/ana/"))


def test_period_picker_switches_lists_and_navigates(portal):
    portal.goto(portal.base + PAGE)
    picker = portal.locator("#period-filter")
    picker.locator("summary").click()
    expect(picker.locator(".pfm")).to_be_visible()

    picker.get_by_role("button", name="Trimestre").click()
    expect(picker.locator('.pfk[data-k="trimestre"]')).to_be_visible()
    expect(picker.locator('.pfk[data-k="mes"]')).to_be_hidden()

    picker.get_by_role("button", name="Mes", exact=True).click()
    picker.locator('.pfk[data-k="mes"] .pfr:visible a:not(.on)').first.click()
    portal.wait_for_url(re.compile(r"periodo=mes"))
    expect(portal.locator("#period-filter summary small")).to_have_text("Mes")


def test_chart_legend_selects_a_series_and_the_scale_toggles(portal):
    portal.goto(portal.base + PAGE)
    scale = portal.locator("#kpi-chart-scale")
    expect(scale).to_contain_text("Escala ampliada")
    paths = portal.locator("#kpi-chart path[stroke-width='2.5']")
    expect(paths).to_have_count(2)

    portal.get_by_role("button", name="Ana").click()
    expect(paths).to_have_count(1)
    portal.get_by_role("button", name="Ana").click()
    expect(paths).to_have_count(2)

    portal.click("#kpi-chart-toggle")
    expect(scale).to_contain_text("Escala completa")
    expect(portal.locator("#kpi-chart-toggle")).to_have_attribute(
        "aria-pressed", "true"
    )


def test_a_failed_request_offers_a_retry(portal):
    portal.route(
        "**/api/v1/screens/kpis-dm/*",
        lambda route: route.fulfill(status=500, body="x"),
    )
    portal.goto(portal.base + PAGE)

    expect(portal.get_by_role("alert")).to_contain_text("servidor")
    expect(portal.get_by_role("button", name="Reintentar")).to_be_visible()
