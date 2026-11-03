"""Proyecto simple conserva cifras, navegación y presentación del anterior."""

import pytest
from playwright.sync_api import expect

from tests.portal.test_views import stub_project

pytestmark = pytest.mark.django_db(transaction=True)
PAGE = "/proyecto/3/"


@pytest.fixture
def project(monkeypatch, datos):
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
