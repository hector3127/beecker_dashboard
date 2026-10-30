"""Inversion conserva datos, filtros y apariencia al separar el frontend."""

from pathlib import Path

import pytest
from playwright.sync_api import expect

from apps.portal.services.facturability_loader import MonthSources
from tests.portal.test_investment import GSE

pytestmark = pytest.mark.django_db(transaction=True)
PAGE = "/operativa/inversion/?mes=2026-10"


@pytest.fixture
def investment(monkeypatch, datos):
    monkeypatch.setattr(
        "apps.portal.views.load_month_sources",
        lambda month: MonthSources(month=month, gse=GSE),
    )


def test_month_totals_bars_and_return(portal, investment):
    portal.goto(portal.base + PAGE)
    expect(
        portal.get_by_role("heading", name="Por especialidad")
    ).to_be_visible()
    assert portal.locator("main").count() == 1
    assert portal.locator("link[href*='pages/investment.css']").count() == 1
    expect(portal.locator(".kp .kv")).to_have_text(
        ["70 horas", "100 horas", "170 horas"]
    )
    expect(portal.locator("tfoot")).to_contain_text("170 h")
    expect(portal.locator(".fill-commercial").first).to_have_css(
        "width",
        portal.locator(".tr").first.evaluate(
            "el => `${el.getBoundingClientRect().width}px`"
        ),
    )
    back = portal.get_by_role("link", name="← Regresar a Operativa")
    expect(back).to_have_attribute("href", "/operativa/")
    # Playwright emite change al rellenar un input month; no duplicar el envio.
    portal.locator("#mes").fill("2026-09")
    portal.wait_for_url("**/operativa/inversion/?mes=2026-09")
    expect(portal.locator("#mes")).to_have_value("2026-09")


def test_page_has_no_tabs_and_keeps_its_own_content(portal, investment):
    portal.goto(portal.base + PAGE)

    assert portal.locator(".tabs").count() == 0
    for name in ("EVA 1", "EVA 2", "KPIs de Delivery Managers"):
        assert portal.get_by_role("link", name=name, exact=True).count() == 0
    expect(portal.locator(".inv-kpi")).to_have_count(3)
    expect(portal.locator(".inv-panel")).to_have_count(2)


@pytest.mark.parametrize("width", [1450, 900, 390])
def test_layout_fits_the_screen_without_csp_violations(
    portal, investment, width, enforced_csp
):
    problems = []
    portal.on(
        "console",
        lambda m: (
            problems.append(m.text) if "Content Security" in m.text else None
        ),
    )
    portal.set_viewport_size({"width": width, "height": 1000})
    portal.goto(portal.base + PAGE)

    expect(portal.locator(".inv-kpi").first).to_be_visible()
    assert portal.evaluate(
        "document.documentElement.scrollWidth <= innerWidth + 1"
    )
    assert not problems, problems
    output = Path(f"tmp/migration/investment/{width}")
    output.mkdir(parents=True, exist_ok=True)
    portal.screenshot(path=str(output / "current.png"), full_page=True)


def test_missing_source_is_explained(portal, investment, monkeypatch):
    monkeypatch.setattr(
        "apps.portal.views.load_month_sources",
        lambda month: MonthSources(month=month, error="GSE no disponible"),
    )
    portal.goto(portal.base + PAGE)
    expect(portal.locator(".err")).to_contain_text("GSE no disponible")
    expect(portal.locator(".two table")).to_contain_text(
        "Sin horas de inversión en ese mes."
    )


def test_saved_previous_link_retains_month_and_current_module(
    portal, investment
):
    portal.goto(portal.base + PAGE + "&vista=anterior")
    expect(portal.locator("#mes")).to_have_value("2026-10")
    expect(portal.locator(".kp .kv")).to_have_text(
        ["70 horas", "100 horas", "170 horas"]
    )
    expect(
        portal.locator('script[src*="pages/investment/main.js"]')
    ).to_have_count(1)
