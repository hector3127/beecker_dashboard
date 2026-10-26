"""Asignaciones mensuales: misma presentacion, filtros y exportacion."""

from pathlib import Path
from types import SimpleNamespace

import pytest
from playwright.sync_api import expect

from tests.portal.test_capacity import make_data, make_row

pytestmark = pytest.mark.django_db(transaction=True)
PAGE = "/operativa/capacidad-instalada/?mes=2026-10"


@pytest.fixture
def capacity(monkeypatch, datos):
    data = make_data(
        make_row(),
        make_row(recurso="Luis", tecnologia="QA", horasDiarias=6),
        bandaColumna="Octubre",
    )
    monkeypatch.setattr(
        "apps.portal.views.load_capacity",
        lambda *a, **k: SimpleNamespace(data=data, error=""),
    )


def test_filters_export_and_return(portal, capacity):
    portal.goto(portal.base + PAGE)
    assert portal.locator("main").count() == 1
    assert portal.locator("link[href*='pages/capacity.css']").count() == 1
    expect(portal.locator("tbody")).to_contain_text("Ana Perez")
    expect(portal.locator("tbody")).to_contain_text("Luis")
    portal.locator("input[name='buscar']").fill("Ana")
    portal.locator("input[name='jornada']").fill("6")
    portal.locator("input[name='jornada']").dispatch_event("change")
    expect(portal.locator("tbody")).to_contain_text("Ana Perez")
    expect(portal.locator("tbody")).not_to_contain_text("Luis")
    link = portal.get_by_role("link", name="↓ Exportar CSV")
    response = portal.context.request.get(
        portal.base + link.get_attribute("href")
    )
    assert response.status == 200
    assert "Ana Perez" in response.text()
    assert "Luis" not in response.text()
    expect(
        portal.get_by_role("link", name="← Regresar a Operativa")
    ).to_have_attribute("href", "/operativa/")


@pytest.mark.parametrize("width", [1450, 900, 390])
def test_layout_keeps_approved_reference(
    portal, capacity, width, snapshot, enforced_csp
):
    portal.set_viewport_size({"width": width, "height": 1000})
    selectors = [
        ".top",
        ".pgh",
        "main.page",
        ".kp5",
        ".card",
        ".fl",
        ".btn",
        ".chips",
        ".th2",
        "table",
        "th",
        "td",
    ]

    def boxes():
        return portal.evaluate(
            """sels => sels.map(s => [...document.querySelectorAll(s)]
              .map(el => {
                const r = el.getBoundingClientRect();
                const css = getComputedStyle(el);
                return {
                  box: ['x','y','width','height'].map(k =>
                    Math.round(r[k] * 10) / 10),
                  css: ['marginTop','marginBottom','paddingTop',
                    'paddingBottom','lineHeight','fontSize','minHeight']
                    .map(k => css[k])
                };
              }))""",
            selectors,
        )

    output = Path(f"tmp/migration/capacity/{width}")
    output.mkdir(parents=True, exist_ok=True)
    portal.goto(portal.base + PAGE)
    after = boxes()
    snapshot(
        f"capacity_layout_{width}", dict(zip(selectors, after, strict=True))
    )
    portal.screenshot(path=str(output / "current.png"), full_page=True)


def test_saved_previous_link_keeps_current_filters_and_csv(portal, capacity):
    portal.goto(portal.base + PAGE + "&vista=anterior&buscar=Ana&jornada=6")
    expect(portal.locator("input[name='buscar']")).to_have_value("Ana")
    expect(portal.locator("input[name='jornada']")).to_have_value("6")
    expect(portal.locator("tbody")).to_contain_text("Ana Perez")
    expect(portal.locator("tbody")).not_to_contain_text("Luis")
    link = portal.get_by_role("link", name="↓ Exportar CSV")
    response = portal.context.request.get(
        portal.base + link.get_attribute("href")
    )
    assert response.status == 200
    assert "Ana Perez" in response.text() and "Luis" not in response.text()
    expect(
        portal.locator('script[src*="pages/capacity/main.js"]')
    ).to_have_count(1)
