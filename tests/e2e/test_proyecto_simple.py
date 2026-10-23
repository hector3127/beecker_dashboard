"""Proyecto simple conserva cifras, navegación y presentación del anterior."""

import json
from pathlib import Path

import pytest
from playwright.sync_api import expect

from tests.portal.test_views import stub_project

pytestmark = pytest.mark.django_db(transaction=True)
PAGE = "/proyecto/3/"


@pytest.fixture
def project(monkeypatch, datos):
    monkeypatch.setattr("apps.portal.pages.anterior_disponible", lambda: True)
    stub_project(
        monkeypatch,
        {
            "proyecto": {
                "fechaInicio": "2026-01-01",
                "fechaFinEstimada": "2026-12-28",
            },
            "avance": {"pctTiempoTranscurrido": 65},
            "riesgosCriticos": [
                {
                    "descripcion": "Sin acceso",
                    "impacto": "Alto",
                    "probabilidad": "Alta",
                },
                {"descripcion": "Validación", "impacto": "Medio"},
                {"descripcion": "Dependencia", "impacto": "Bajo"},
            ],
            "filasRecursosCompleto": [
                {"nombre": "Ana", "posicion": "QA", "horasReales": 20.5},
                {"nombre": "Luis", "posicion": "QA", "horasReales": 30},
            ],
            "hitos": [
                {
                    "nombre": "Arranque",
                    "fechaFinReal": "2026-02-02",
                    "estado": "Completado",
                },
            ],
        },
    )


def test_numbers_bars_and_navigation(portal, project):
    portal.goto(portal.base + PAGE)
    expect(portal.locator(".tr i").first).to_have_css(
        "background-color", "rgb(214, 48, 75)"
    )
    assert portal.locator("main").count() == 1
    expect(portal.locator("h1")).to_have_text("HIS")
    expect(portal.locator(".dec")).to_contain_text("Requiere decisión")
    expect(portal.locator("table").first).to_contain_text("Sin acceso")
    expect(portal.locator("table").nth(1)).to_contain_text("51 h")
    expect(portal.locator(".ev").first).to_contain_text("28/12/2026")
    widths = portal.locator(".tr i").evaluate_all(
        "els => els.map(el => el.style.width)"
    )
    assert widths == ["83.3%", "33.3%", "43.3%"]
    expect(portal.locator("[data-portal-back]")).to_have_attribute(
        "href", "/operativa/"
    )
    # Keep the project as the parent when opening its account.
    with portal.expect_request(lambda r: "/cuenta/acme/" in r.url) as request:
        portal.locator(".sub a").click()
    assert "volver=%2Fproyecto%2F3%2F" in request.value.url


def test_partial_data_and_reload(portal, project, monkeypatch):
    stub_project(monkeypatch, error="Sin Clockify.")
    portal.goto(portal.base + PAGE)
    expect(portal.locator(".err")).to_contain_text("Sin Clockify.")
    expect(portal.locator(".vacio").nth(0)).to_have_text(
        "Sin riesgos abiertos."
    )
    expect(portal.locator(".vacio").nth(1)).to_have_text(
        "Sin horas registradas."
    )
    expect(portal.locator(".kp")).to_be_visible()
    stub_project(monkeypatch)
    portal.reload()
    expect(portal.locator(".err")).to_have_count(0)


@pytest.mark.parametrize("width", [1450, 390])
@pytest.mark.parametrize("empty", [False, True])
def test_layout_matches_previous(portal, project, monkeypatch, width, empty):
    if empty:
        stub_project(monkeypatch, error="Sin Clockify.")
    portal.set_viewport_size({"width": width, "height": 1000})
    selectors = [
        ".top",
        "main.page",
        ".crumb",
        ".hd",
        "h1",
        ".badge",
        ".sub",
        ".dec",
        ".dec h2",
        ".dec .amt",
        ".kp",
        ".kc",
        ".kl",
        ".kv",
        ".kv small",
        ".kv span",
        ".ke",
        ".two",
        ".card",
        ".card h2",
        ".hs",
        ".br",
        ".tr",
        ".tr i",
        ".tr u",
        ".ax",
        ".ax em",
        "table",
        "th",
        "td",
        ".st",
        ".ev",
        ".ev i",
        ".note",
        ".vacio",
        ".err",
    ]

    def state():
        portal.locator(".tr i").first.wait_for(state="attached")
        portal.wait_for_function(
            "document.querySelector('.tr i').style.width !== ''"
        )
        return portal.evaluate(
            """selectors => selectors.map(s =>
              [...document.querySelectorAll(s)].map(el => {
                const r = el.getBoundingClientRect(), c = getComputedStyle(el);
                return {
                  box: ['x','y','width','height'].map(k =>
                    Math.round(r[k]*10)/10),
                  css: ['color','backgroundColor','fontSize','fontWeight',
                    'lineHeight','marginTop','marginBottom','paddingTop',
                    'paddingBottom','boxShadow','borderRadius','boxSizing']
                    .map(k => c[k]),
                  text: el.textContent.replace(/\\s+/g, '')
                };
              }))""",
            selectors,
        )

    output = Path(
        f"tmp/migration/project/{width}/{'empty' if empty else 'full'}"
    )
    output.mkdir(parents=True, exist_ok=True)
    portal.goto(portal.base + PAGE + "?vista=anterior")
    before = state()
    portal.screenshot(path=str(output / "previous.png"), full_page=True)
    portal.goto(portal.base + PAGE)
    after = state()
    portal.screenshot(path=str(output / "current.png"), full_page=True)
    differences = {
        selector: (old, new)
        for selector, old, new in zip(selectors, before, after, strict=True)
        if old != new
    }
    (output / "differences.json").write_text(
        json.dumps(differences, indent=2), encoding="utf-8"
    )
    assert not differences, differences
