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
    monkeypatch.setattr("apps.portal.pages.anterior_disponible", lambda: True)


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


@pytest.mark.parametrize("width", [1450, 900, 390])
def test_layout_matches_previous_with_same_data(portal, investment, width):
    portal.set_viewport_size({"width": width, "height": 1000})
    selectors = [
        ".top",
        ".pgh",
        ".kp",
        ".two",
        ".two .card",
        ".two h2",
        ".two .hs",
        ".two th",
        ".two td",
        ".note",
    ]

    def measure():
        return portal.evaluate(
            """selectors => selectors.map(selector =>
              [...document.querySelectorAll(selector)].map(el => {
                const box = el.getBoundingClientRect();
                const css = getComputedStyle(el);
                return {
                  box: ['x', 'y', 'width', 'height'].map(k =>
                    Math.round(box[k] * 10) / 10),
                  styles: ['fontSize', 'lineHeight', 'paddingTop',
                    'paddingBottom', 'marginTop', 'marginBottom']
                    .map(k => css[k])
                };
              }))""",
            selectors,
        )

    output = Path(f"tmp/migration/investment/{width}")
    output.mkdir(parents=True, exist_ok=True)
    portal.goto(portal.base + PAGE + "&vista=anterior")
    previous = measure()
    portal.screenshot(path=str(output / "previous.png"), full_page=True)
    portal.goto(portal.base + PAGE)
    current = measure()
    portal.screenshot(path=str(output / "current.png"), full_page=True)
    for selector, before, after in zip(
        selectors, previous, current, strict=True
    ):
        assert after == before, (selector, before, after)


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
