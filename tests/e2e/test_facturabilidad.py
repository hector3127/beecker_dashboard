"""Facturabilidad conserva los periodos, roles, cifras y diseño anteriores."""

from pathlib import Path

import pytest
from playwright.sync_api import expect

from apps.portal.services.facturability_loader import MonthSources
from tests.portal.test_views import facturable_gse

pytestmark = pytest.mark.django_db(transaction=True)
SCREENS = ["", "especialidad/", "recurso/"]
BASE = "/operativa/facturabilidad/"


@pytest.fixture
def facturability(monkeypatch, datos):
    data = facturable_gse(
        ("Ana", "DEV", "AER", 84),
        ("Eva", "QA", "IXB", 42),
        ("Dan", "DM", "AER", 100),
    )
    monkeypatch.setattr(
        "apps.portal.views.load_month_sources",
        lambda month: MonthSources(month=month, gse=data),
    )
    monkeypatch.setattr(
        "apps.portal.views.load_year_sources",
        lambda month: [
            MonthSources(month=f"2026-{i:02d}", gse=data)
            for i in range(1, int(month[-2:]) + 1)
        ],
    )
    monkeypatch.setattr("apps.portal.pages.anterior_disponible", lambda: True)


@pytest.mark.parametrize("screen", SCREENS)
def test_period_roles_tabs_and_return(portal, facturability, screen):
    portal.goto(portal.base + BASE + screen + "?mes=2026-02")
    assert portal.locator("main").count() == 1
    assert portal.locator("main style, main script").count() == 0
    expect(portal.locator(".tabs .on")).to_be_visible()
    portal.locator(".rf summary").click()
    for checkbox in portal.locator('input[name="rol"]').all():
        checkbox.uncheck()
    portal.locator('input[name="rol"][value="QA"]').check()
    portal.get_by_role("button", name="Aplicar", exact=True).click()
    portal.wait_for_url("**roles=1*")
    assert "rol=QA" in portal.url
    assert "mes=2026-02" in portal.url
    tab = portal.locator(".tabs a").filter(
        has_text="Facturabilidad por recurso"
    )
    # Las pestañas anteriores trasladan el periodo, no el filtro de roles.
    assert "mes=2026-02" in tab.get_attribute("href")
    if screen == "recurso/":
        expect(portal.locator("table")).to_contain_text("Eva")
        expect(portal.locator("table")).not_to_contain_text("Ana")
    portal.locator(".pf summary").click()
    portal.locator('.pfp button[data-k="trimestre"]').click()
    quarter = portal.locator(
        '.pfk[data-k="trimestre"] .pfr:not([hidden]) a'
    ).first
    assert "rol=QA" in quarter.get_attribute("href")
    quarter.click()
    expect(portal.locator(".pf summary small")).to_have_text("Trimestre")
    portal.locator(".pf summary").click()
    portal.locator('.pfp button[data-k="anio"]').click()
    portal.locator('.pfk[data-k="anio"] a').last.click()
    expect(portal.locator(".pf summary small")).to_have_text("Año")
    portal.locator(".pf summary").click()
    portal.locator('.pfp button[data-k="mes"]').click()
    portal.locator('.pfk[data-k="mes"] .pfr:not([hidden]) a').first.click()
    expect(portal.locator(".pf summary small")).to_have_text("Mes")
    portal.locator(".rf summary").click()
    portal.get_by_role("link", name="Solo operativas", exact=True).click()
    expect(portal.locator(".rf summary")).to_contain_text("solo operativas")
    assert "mes=" in portal.locator(".tabs a").first.get_attribute("href")
    portal.locator(".tabs a").filter(
        has_text="Facturabilidad por recurso"
    ).click()
    portal.wait_for_url("**/recurso/**")
    expect(portal.locator(".pf summary small")).to_have_text("Mes")
    portal.get_by_role("link", name="← Regresar a Operativa").click()
    portal.wait_for_url("**/operativa/")


@pytest.mark.parametrize("screen", SCREENS)
@pytest.mark.parametrize("width", [1450, 390])
def test_matches_previous(portal, facturability, screen, width):
    portal.set_viewport_size({"width": width, "height": 1000})
    selectors = [
        ".top",
        ".pgh",
        ".tabs",
        ".mf",
        ".pf summary",
        ".rf summary",
        ".pfm",
        ".pfp button",
        ".pfr a",
        ".rfl",
        ".rfb",
        ".hero",
        ".kp",
        ".kc",
        ".card",
        ".card h2",
        ".hs",
        "table",
        "th",
        "td",
        ".bars",
        ".bc i",
        ".note",
    ]

    def measure():
        return portal.evaluate(
            """selectors => selectors.map(selector =>
            [...document.querySelectorAll(selector)].map(el => {
              const box = el.getBoundingClientRect();
              const css = getComputedStyle(el);
              return {box: ['x','y','width','height'].map(k =>
                Math.round(box[k]*10)/10),
                styles: ['fontSize','fontWeight','color','backgroundColor',
                  'paddingTop',
                  'paddingBottom','marginTop','marginBottom'].map(k => css[k])};
            }))""",
            selectors,
        )

    path = BASE + screen + "?mes=2026-02"
    output = Path(
        f"tmp/migration/billability/{screen.strip('/') or 'general'}/{width}"
    )
    output.mkdir(parents=True, exist_ok=True)
    portal.goto(portal.base + path + "&vista=anterior")
    before = measure()
    text = portal.locator("table").inner_text()
    portal.screenshot(path=str(output / "previous.png"), full_page=True)
    portal.goto(portal.base + path)
    assert portal.locator("table").inner_text() == text
    after = measure()
    portal.screenshot(path=str(output / "current.png"), full_page=True)
    for selector, old, new in zip(selectors, before, after, strict=True):
        assert old == new, (selector, old, new)

    portal.locator(".rf summary").click()
    portal.locator(".pf summary").click()
    current_open = measure()
    portal.screenshot(path=str(output / "current-open.png"), full_page=True)
    portal.goto(portal.base + path + "&vista=anterior")
    portal.locator(".rf summary").click()
    portal.locator(".pf summary").click()
    previous_open = measure()
    portal.screenshot(path=str(output / "previous-open.png"), full_page=True)
    assert current_open == previous_open


@pytest.mark.parametrize("screen", SCREENS)
def test_missing_data(portal, facturability, monkeypatch, screen):
    monkeypatch.setattr(
        "apps.portal.views.load_month_sources",
        lambda month: MonthSources(month=month, error="GSE no disponible"),
    )
    monkeypatch.setattr(
        "apps.portal.views.load_year_sources",
        lambda month: [
            MonthSources(month="2026-02", error="GSE no disponible")
        ],
    )
    portal.goto(portal.base + BASE + screen + "?mes=2026-02")
    expect(portal.locator(".err")).to_contain_text("GSE no disponible")
    if screen:
        expect(portal.locator("table")).to_contain_text("Sin datos")
