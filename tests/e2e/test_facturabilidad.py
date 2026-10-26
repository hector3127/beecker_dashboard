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


@pytest.mark.parametrize("screen", SCREENS)
def test_period_roles_tabs_and_return(portal, facturability, screen):
    def open_period():
        portal.wait_for_load_state("networkidle")
        if screen == "recurso/":
            # This table is mounted after period handlers are bound. Wait for
            # the module, not just the server-rendered heading after navigation.
            expect(portal.locator(".eva-column-trigger").first).to_be_visible()
        portal.locator(".pf summary").click()

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
    open_period()
    portal.locator('.pfp button[data-k="trimestre"]').click()
    quarter = portal.locator(
        '.pfk[data-k="trimestre"] .pfr:not([hidden]) a'
    ).first
    assert "rol=QA" in quarter.get_attribute("href")
    quarter.click()
    expect(portal.locator(".pf summary small")).to_have_text("Trimestre")
    open_period()
    portal.locator('.pfp button[data-k="anio"]').click()
    portal.locator('.pfk[data-k="anio"] a').last.click()
    expect(portal.locator(".pf summary small")).to_have_text("Año")
    open_period()
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


@pytest.mark.parametrize("width", [1450, 900, 390])
def test_billability_reference_chart_and_free_colors(
    portal, facturability, width
):
    portal.set_viewport_size({"width": width, "height": 1100})
    portal.goto(portal.base + BASE + "?mes=2026-09")
    table = portal.locator("#bill-summary")
    expect(table.locator("tbody tr")).to_have_count(9)
    free = table.locator("tbody td.free")
    expect(free).to_have_count(18)
    for cell in free.all():
        expect(cell).to_have_css("background-color", "rgb(255, 247, 224)")
    expect(portal.locator(".hero .bill-reference-icon")).to_have_count(3)
    expect(portal.locator("#bill-chart g[role=button]")).to_have_count(9)
    # The SVG fills the plot without horizontal letterboxing on wide screens.
    geometry = portal.locator("#bill-chart").evaluate("""chart => {
      const svgBox = chart.getBoundingClientRect();
      const first = chart.querySelector('g[role=button] rect:nth-child(2)')
        .getBoundingClientRect();
      const groups = chart.querySelectorAll('g[role=button]');
      const last = groups[groups.length - 1].querySelector('rect:nth-child(2)')
        .getBoundingClientRect();
      return {left: first.left - svgBox.left,
        right: svgBox.right - last.right};
    }""")
    assert 40 <= geometry["left"] <= 60
    assert 5 <= geometry["right"] <= 25
    table_before = table.inner_text()
    portal.locator("#bill-mode-hours").click()
    expect(portal.locator("#bill-mode-hours")).to_have_attribute(
        "aria-pressed", "true"
    )
    expect(portal.locator("#bill-chart")).to_have_attribute(
        "aria-label", "Horas facturadas por mes"
    )
    expect(portal.locator(".bill-chart-aside strong")).to_have_text("126 h")
    portal.locator("#bill-mode-percent").click()
    portal.locator("#bill-chart g[role=button]").first.click()
    expect(portal.locator(".bill-chart-aside small").first).to_contain_text(
        "Enero"
    )
    assert table.inner_text() == table_before
    portal.locator("#bill-chart-expand").click()
    expect(portal.locator("#bill-chart-card")).to_have_class(
        "card bill-chart-card bill-chart-expanded"
    )
    portal.keyboard.press("Escape")
    expect(portal.locator("#bill-chart-expand")).to_have_attribute(
        "aria-expanded", "false"
    )
    assert portal.evaluate("document.documentElement.scrollWidth <= innerWidth")
    output = Path("tmp/design/billability-reference")
    output.mkdir(parents=True, exist_ok=True)
    portal.screenshot(
        path=str(output / f"billability-{width}.png"), full_page=True
    )


@pytest.mark.parametrize("width", [1450, 900, 390])
def test_specialty_reference_keeps_source_values(portal, facturability, width):
    portal.set_viewport_size({"width": width, "height": 1100})
    path = BASE + "especialidad/?mes=2026-09"
    portal.goto(portal.base + path + "&vista=anterior")
    original = portal.locator("table").evaluate(
        """table => [...table.rows].map(row =>
          [...row.cells].map(cell => cell.textContent.trim()))"""
    )
    portal.goto(portal.base + path)
    table = portal.locator("#specialty-summary")
    assert (
        table.evaluate(
            """table => [...table.rows].map(row =>
          [...row.cells].map(cell => cell.textContent.trim()))"""
        )
        == original
    )
    expect(portal.locator(".kp .kc")).to_have_count(4)
    expect(portal.locator(".kp .kc > .specialty-icon svg")).to_have_count(4)
    expect(table.locator("tfoot tr")).to_have_count(1)
    assert (
        table.locator('tr[data-specialty="dev"] b').evaluate(
            "node => getComputedStyle(node, '::before').backgroundColor"
        )
        == "rgb(7, 140, 255)"
    )
    for badge in table.locator(".specialty-free").all():
        positive = float(badge.inner_text()) > 0
        expect(badge).to_have_class(
            "specialty-free positive" if positive else "specialty-free negative"
        )
    assert portal.evaluate("document.documentElement.scrollWidth <= innerWidth")
    if width == 1450:
        tops = portal.locator(".kp .kc").evaluate_all(
            "cards => cards.map(card => card.getBoundingClientRect().top)"
        )
        assert len(set(tops)) == 1
    output = Path("tmp/design/billability-specialty")
    output.mkdir(parents=True, exist_ok=True)
    portal.screenshot(
        path=str(output / f"specialty-{width}.png"), full_page=True
    )


@pytest.mark.parametrize("width", [1450, 390])
def test_resource_bajas_and_column_menus(
    portal, facturability, monkeypatch, width
):
    old = facturable_gse(("Ana", "DEV", "AER", 84), ("Eva", "QA", "IXB", 42))
    current = facturable_gse(("Eva", "QA", "IXB", 42))
    current["plantillaBajas"] = ["Ána"]
    monkeypatch.setattr(
        "apps.portal.views.load_year_sources",
        lambda month: [
            MonthSources(month=f"2026-{i:02d}", gse=current if i == 9 else old)
            for i in range(1, 10)
        ],
    )
    portal.set_viewport_size({"width": width, "height": 1000})
    portal.goto(portal.base + BASE + "recurso/?mes=2026-09")
    table = portal.locator("#resource-history")
    expect(table.locator("s.resource-inactive")).to_have_text("Ana")
    expect(table.locator("s.resource-inactive")).to_have_css(
        "text-decoration-line", "line-through"
    )
    rows = table.locator("tbody tr[data-resource-row]")
    expect(rows).to_have_count(2)
    visible_rows = table.locator("tbody tr[data-resource-row]:visible")
    expect(table.locator("thead th button")).to_have_count(12)
    footer = table.locator("tfoot").inner_text()
    days = table.locator("thead .dl").inner_text()
    for condition, expected in [
        ("resource-active", "Eva"),
        ("resource-inactive", "Ana"),
        ("resource-all", None),
    ]:
        table.locator('th[data-column-index="0"] button').click()
        menu = portal.locator(".eva3-column-menu")
        details = menu.locator("details").filter(
            has_text="Filtrar por condición"
        )
        if details.get_attribute("open") is None:
            menu.get_by_text("Filtrar por condición", exact=True).click()
        menu.get_by_label("Condición", exact=True).select_option(condition)
        expect(
            menu.get_by_label("Valor de la condición", exact=True)
        ).to_be_hidden()
        menu.get_by_role("button", name="Aceptar", exact=True).click()
        expect(visible_rows).to_have_count(1 if expected else 2)
        if expected:
            expect(visible_rows).to_contain_text(expected)
    portal.get_by_role("button", name="Limpiar filtros de columnas").click()
    table.get_by_role("button", name="Opciones de Recurso", exact=True).click()
    menu = portal.locator(".eva3-column-menu")
    menu.get_by_role("button", name="Ordenar Z a la A", exact=True).click()
    expect(rows.first).to_contain_text("Eva")
    table.get_by_role("button", name="Opciones de Rol", exact=True).click()
    menu.get_by_role("checkbox", name="QA", exact=True).uncheck()
    menu.get_by_role("button", name="Cancelar", exact=True).click()
    expect(visible_rows).to_have_count(2)
    table.get_by_role("button", name="Opciones de Rol", exact=True).click()
    menu.get_by_role("checkbox", name="QA", exact=True).uncheck()
    menu.get_by_role("button", name="Aceptar", exact=True).click()
    expect(visible_rows).to_have_count(1)
    expect(visible_rows).to_contain_text("Ana")
    portal.get_by_role("button", name="Limpiar filtros de columnas").click()
    table.get_by_role("button", name="Opciones de Ene", exact=True).click()
    menu.get_by_text("Filtrar por condición", exact=True).click()
    menu.get_by_label("Condición", exact=True).select_option("gt")
    menu.get_by_label("Valor de la condición", exact=True).fill("30")
    menu.get_by_role("button", name="Aceptar", exact=True).click()
    expect(visible_rows).to_have_count(1)
    expect(visible_rows).to_contain_text("Ana")
    portal.get_by_role("button", name="Limpiar filtros de columnas").click()
    table.get_by_role("button", name="Opciones de Ene", exact=True).click()
    expect(menu.get_by_text("Filtrar por color", exact=True)).to_be_visible()
    menu.get_by_text("Filtrar por color", exact=True).click()
    menu.get_by_label("Filtrar por color", exact=True).select_option("red")
    menu.get_by_role("button", name="Aceptar", exact=True).click()
    expect(visible_rows).to_have_count(1)
    expect(visible_rows).to_contain_text("Eva")
    assert table.locator("tfoot").inner_text() == footer
    assert table.locator("thead .dl").inner_text() == days
    portal.get_by_role("button", name="Limpiar filtros de columnas").click()
    table.get_by_role("button", name="Opciones de Recurso", exact=True).click()
    portal.keyboard.press("Escape")
    assert portal.evaluate("document.documentElement.scrollWidth <= innerWidth")
    output = Path("tmp/design/billability-resource")
    output.mkdir(parents=True, exist_ok=True)
    portal.screenshot(
        path=str(output / f"resource-{width}.png"), full_page=True
    )


@pytest.mark.parametrize("screen", SCREENS)
@pytest.mark.parametrize("width", [1450, 900, 390])
def test_approved_billability_layout(
    portal, facturability, screen, width, snapshot, enforced_csp
):
    from datetime import datetime

    portal.clock.set_fixed_time(
        datetime.fromisoformat("2026-10-26T18:00:00+00:00")
    )
    portal.set_viewport_size({"width": width, "height": 1000})
    portal.goto(portal.base + BASE + screen + "?mes=2026-02")
    portal.wait_for_load_state("networkidle")
    selectors = [
        ".pgh",
        ".tabs",
        ".pf",
        ".rf",
        ".hero",
        ".card",
        "table",
        "#bill-chart",
    ]
    state = portal.evaluate(
        """selectors => Object.fromEntries(selectors.map(selector => [selector,
          [...document.querySelectorAll(selector)].map(node => {
            const box = node.getBoundingClientRect();
            const css = getComputedStyle(node);
            return {
              box: ['x','y','width','height']
                .map(k => Math.round(box[k]*10)/10),
              css: ['fontSize','color','backgroundColor','padding','margin',
                'borderRadius'].map(k => css[k]),
              text: node.tagName === 'TABLE' ? node.innerText : null
            };
          })]))""",
        selectors,
    )
    key = screen.strip("/") or "general"
    snapshot(f"billability_layout_{key}_{width}", state)
    target = Path("tmp/design/billability-retirement")
    target.mkdir(parents=True, exist_ok=True)
    portal.mouse.move(0, 0)
    portal.screenshot(path=str(target / f"{key}-{width}.png"), full_page=True)


@pytest.mark.parametrize(
    "screen,name",
    list(
        zip(
            SCREENS,
            ["billability", "billability_specialty", "billability_resource"],
            strict=True,
        )
    ),
)
def test_saved_previous_link_keeps_month_roles_and_current_module(
    portal, facturability, screen, name
):
    portal.goto(
        portal.base
        + BASE
        + screen
        + "?vista=anterior&mes=2026-02&rol=QA&roles=1"
    )
    expect(
        portal.locator(f'script[src*="pages/{name}/main.js"]')
    ).to_have_count(1)
    expect(portal.locator(".pf summary")).to_contain_text("Febrero 2026")
    expect(portal.locator('input[name="rol"][value="QA"]')).to_be_checked()
    expect(portal.locator('input[name="rol"][value="DEV"]')).not_to_be_checked()
    expect(
        portal.get_by_role("link", name="← Regresar a Operativa")
    ).to_have_attribute("href", "/operativa/")
    if screen == "recurso/":
        expect(portal.locator("table")).to_contain_text("Eva")
        expect(portal.locator("table")).not_to_contain_text("Ana")
