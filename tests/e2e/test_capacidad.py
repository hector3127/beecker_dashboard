"""Asignaciones mensuales: misma presentacion, filtros y exportacion."""

import json
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
    monkeypatch.setattr("apps.portal.pages.anterior_disponible", lambda: True)


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


@pytest.mark.parametrize("width", [1450, 390])
def test_layout_matches_previous(portal, capacity, width):
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
    portal.goto(portal.base + PAGE + "&vista=anterior")
    before = boxes()
    portal.screenshot(path=str(output / "previous.png"), full_page=True)
    portal.goto(portal.base + PAGE)
    after = boxes()
    portal.screenshot(path=str(output / "current.png"), full_page=True)
    differences = {
        selector: (old, new)
        for selector, old, new in zip(selectors, before, after, strict=True)
        if new != old
    }
    (output / "differences.json").write_text(
        json.dumps(differences, indent=2), encoding="utf-8"
    )
    assert not differences, differences
