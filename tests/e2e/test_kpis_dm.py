"""KPIs de Delivery Managers en un navegador real: periodo, grafica y tablas."""

import re

import pytest
from playwright.sync_api import expect

from tests.e2e.frozen.aer_executive_support import production_site  # noqa: F401
from tests.portal.test_views import portfolio, stub_history, stub_portfolio

pytestmark = pytest.mark.django_db(transaction=True)

PAGE = "/operativa/kpis-delivery-managers/"


@pytest.fixture(autouse=True)
def sources(monkeypatch):
    from django.utils import timezone

    from tests.portal.test_kpi_eva import stub_compliance_history

    stub_portfolio(monkeypatch, portfolio())
    stub_compliance_history(monkeypatch, timezone.localdate())


@pytest.mark.parametrize("query", ["", "?vista=anterior"])
def test_page_uses_the_modular_frontend_with_the_previous_layout(portal, query):
    portal.goto(portal.base + PAGE + query)

    expect(
        portal.get_by_role("heading", name="KPIs de Delivery Managers")
    ).to_be_visible()
    assert portal.locator("main").count() == 1
    expect(
        portal.get_by_role("link", name="← Regresar a Operativa")
    ).to_have_attribute("href", "/operativa/")
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
    assert portal.locator("#kpi-month-history thead [colspan='3']").count() > 1
    expect(portal.locator(".kpi-definition-note")).to_contain_text(
        "T: proyectos con desviación ≤ 0 / TP × 100"
    )


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


def test_chart_legend_selects_a_series_and_the_scale_toggles(
    portal, enforced_csp
):
    from tests.e2e.conftest import watch

    problems = watch(portal)
    response = portal.goto(portal.base + PAGE)
    assert "script-src" in response.header_value("content-security-policy")
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
    assert problems == []


def test_a_failed_request_offers_a_retry(portal):
    portal.route(
        "**/api/v1/screens/kpis-dm/*",
        lambda route: route.fulfill(status=500, body="x"),
    )
    portal.goto(portal.base + PAGE)

    expect(portal.get_by_role("alert")).to_contain_text("servidor")
    expect(portal.get_by_role("button", name="Reintentar")).to_be_visible()


@pytest.mark.parametrize("width", [1450, 900, 390])
def test_kpis_reference_layout(portal, monkeypatch, width, enforced_csp):
    from datetime import datetime
    from pathlib import Path

    monkeypatch.setattr(
        "django.utils.timezone.now",
        lambda: datetime.fromisoformat("2026-10-26T18:00:00+00:00"),
    )
    portal.set_viewport_size({"width": width, "height": 1000})
    portal.goto(portal.base + PAGE)
    expect(portal.locator("#kpi-month-history")).to_be_visible()
    expect(portal.locator("#kpi-quarter-history")).to_be_visible()
    assert portal.evaluate("document.documentElement.scrollWidth <= innerWidth")
    portal.mouse.move(0, 0)
    target = Path("tmp/design/kpis-reference")
    target.mkdir(parents=True, exist_ok=True)
    portal.screenshot(path=str(target / f"kpis-{width}.png"), full_page=True)


def test_missing_history_keeps_the_explanation_and_no_false_tables(
    portal, monkeypatch
):
    stub_history(monkeypatch, error="Clockify no responde.")
    portal.goto(portal.base + PAGE)
    expect(portal.locator("#kpis-content")).to_contain_text(
        "No se pudo reconstruir el histórico. Clockify no responde."
    )
    expect(portal.locator("#kpi-month-history")).to_have_count(0)
    expect(portal.locator("#kpi-quarter-history")).to_have_count(0)


@pytest.mark.usefixtures("production_site")
def test_monthly_compliance_uses_percentages_and_explicit_definitions(
    portal, enforced_csp
):
    portal.goto(portal.base + PAGE + "?periodo=anio&anio=2026")
    expect(portal.locator("#kpi-month-history tbody tr").first).to_contain_text(
        "Ana"
    )
    expect(portal.locator("#kpi-month-history tbody tr").first).to_contain_text(
        "50%"
    )
    expect(
        portal.locator("#kpi-month-history tbody tr").nth(1)
    ).to_contain_text("100%")
    expect(portal.locator(".kp .kc").first).to_contain_text(
        "Cumplimiento en costo"
    )
    expect(portal.locator(".kpi-definition-note")).to_contain_text(
        "último lunes a jueves"
    )
    expect(portal.locator(".two table")).to_contain_text("Fuera de tiempo")
    assert not portal.locator("#kpi-month-history").inner_text().endswith(" d")
