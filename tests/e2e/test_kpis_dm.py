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
    from tests.portal.kpi_cut_support import stub_inventory

    stub_inventory(monkeypatch)


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


def test_cut_and_chart_filters_are_independent(portal):
    portal.goto(portal.base + PAGE)
    portal.locator("#kpi-cut").fill("2026-02")
    portal.get_by_role("button", name="Consultar mes").click()
    portal.wait_for_url(re.compile(r"mes=2026-02"))
    expect(portal.locator(".two table tfoot")).to_contain_text("2")
    portal.locator("#kpi-chart-year").select_option("2025")
    portal.wait_for_url(re.compile(r"chart_year=2025"))
    expect(portal.locator("#kpi-cut")).to_have_value("2026-02")
    expect(portal.locator("#kpi-history-year")).to_have_value("2026")
    expect(
        portal.locator("#kpi-month-history thead tr").first.locator(
            "[colspan='3']"
        )
    ).to_have_count(12)
    portal.locator("#kpi-global-dms summary").click()
    portal.get_by_role("checkbox", name="Beto", exact=True).uncheck()
    portal.get_by_role("button", name="Aplicar DMs").click()
    portal.wait_for_url(re.compile(r"dm=Ana"))
    expect(portal.locator("#kpi-legend button")).to_have_count(1)
    expect(portal.locator(".two table tbody tr")).to_have_count(1)
    expect(portal.locator("#kpi-month-history tbody tr")).to_have_count(1)
    expect(portal.locator("#kpi-quarter-history tbody tr")).to_have_count(1)
    expect(portal.locator("#kpi-cut")).to_have_value("2026-02")
    expect(portal.locator("#kpi-chart-year")).to_have_value("2025")
    portal.get_by_role("button", name="Ver año").click()
    portal.wait_for_url(re.compile(r"dm=Ana"))
    expect(portal.locator(".two table tbody tr")).to_have_count(1)


@pytest.mark.parametrize("width", [1450, 900, 390])
def test_global_dm_panel_is_compact_searchable_and_keyboard_operable(
    portal, width
):
    portal.set_viewport_size({"width": width, "height": 950})
    portal.goto(portal.base + PAGE)
    trigger = portal.locator("#kpi-global-dms summary")
    expect(trigger).to_be_visible()
    before = portal.locator(".kpi-cut-filter").bounding_box()
    trigger.click()
    panel = portal.get_by_role(
        "group", name="Selección global de Delivery Managers"
    )
    expect(panel).to_be_visible()
    after = portal.locator(".kpi-cut-filter").bounding_box()
    assert abs(before["height"] - after["height"]) < 1
    box = panel.bounding_box()
    assert box["x"] >= 0 and box["x"] + box["width"] <= width
    assert box["y"] >= 0 and box["y"] + box["height"] <= 950
    search = portal.get_by_role("searchbox", name="Buscar Delivery Manager")
    search.fill("BÉTO")
    expect(panel.locator(".kpi-dm-row:visible")).to_have_count(1)
    expect(panel.locator(".kpi-dm-row:visible")).to_contain_text("Beto")
    search.press("Enter")
    expect(panel).to_be_visible()
    search.fill("sin coincidencias")
    expect(panel.get_by_text("No hay DMs con ese nombre.")).to_be_visible()
    panel.get_by_role("button", name="Ninguno", exact=True).click()
    expect(panel.get_by_role("status")).to_have_text("0 de 2 seleccionados")
    panel.get_by_role("button", name="Todos", exact=True).click()
    expect(panel.get_by_role("status")).to_have_text("2 de 2 seleccionados")
    search.fill("")
    portal.screenshot(
        path=f"tmp/design/kpis-reference/dm-panel-{width}.png", full_page=True
    )
    search.press("Escape")
    expect(panel).not_to_be_visible()
    expect(trigger).to_be_focused()
    trigger.click()
    portal.mouse.click(2, 10)
    expect(panel).not_to_be_visible()
    assert portal.evaluate("document.documentElement.scrollWidth <= innerWidth")


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
    assert all("C" in path.get_attribute("d") for path in paths.all())

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
    expect(portal.locator(".kp .kc").first).to_contain_text("Cumplimiento en costo")
    expect(portal.locator(".kpi-definition-note")).to_contain_text(
        "último lunes a jueves"
    )
    expect(portal.locator(".two table")).to_contain_text("Fuera de tiempo")
    assert not portal.locator("#kpi-month-history").inner_text().endswith(" d")


@pytest.mark.parametrize("width", [1450, 900, 390])
@pytest.mark.usefixtures("production_site")
def test_smooth_trend_keeps_monthly_values_and_responsive_layout(
    portal, monkeypatch, width, enforced_csp
):
    from datetime import datetime
    from pathlib import Path

    from apps.portal.services.kpi_eva import build_eva_history
    from apps.portal.services.kpi_history_loader import KpiHistoryLoad
    from tests.portal.test_kpi_eva import row

    values = [100, 100, 50, 0, 50, 100, 100, 50, 100, 0]

    def resolve(cut):
        good = values[cut.month - 1] // 50
        return [
            row(str(i), "Ana", -1, 150 if i < good else 50) for i in range(2)
        ]

    history = build_eva_history(2026, datetime(2026, 10, 22), resolve)
    monkeypatch.setattr(
        "apps.portal.views.load_kpi_history",
        lambda *args: KpiHistoryLoad(history),
    )
    portal.set_viewport_size({"width": width, "height": 1000})
    portal.goto(portal.base + PAGE)
    path = portal.locator("#kpi-chart path[stroke-width='2.5']")
    expect(path).to_have_count(1)
    assert path.get_attribute("d").count("C") == 9
    markers = portal.locator("#kpi-chart circle")
    expect(markers).to_have_count(10)
    titles = markers.locator("title").all_text_contents()
    assert [int(text.rsplit(": ", 1)[1].rstrip("%")) for text in titles] == [
        100 - value for value in values
    ]
    assert portal.evaluate("document.documentElement.scrollWidth <= innerWidth")
    portal.evaluate("document.fonts.ready")
    target = Path("tmp/design/kpi-trend")
    target.mkdir(parents=True, exist_ok=True)
    portal.screenshot(path=str(target / f"kpis-{width}.png"), full_page=True)
