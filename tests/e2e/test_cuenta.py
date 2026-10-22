"""Cuenta nueva (?vista=nueva) en el navegador: indicadores, tabla y regreso."""

import re

import pytest
from playwright.sync_api import expect

from tests.e2e.conftest import visible

pytestmark = pytest.mark.django_db(transaction=True)

URL = (
    "/cuenta/clinica-sur/?nombre=Clinica+Sur&vista=nueva&volver=%2Foperativa%2F"
)


def project(index, **extra):
    return {
        "id": f"P{index}",
        "nombre": f"Proyecto {index}",
        "servicio": "RaaS",
        "etapa": "Build",
        "estado": "En desarrollo",
        "deliveryManager": "Ana",
        "budget": 100,
        "burn": 50,
        "nps": None,
        "clockifyPending": False,
        "excedido": False,
        "atrasado": False,
        **extra,
    }


VIEW = {
    "ok": True,
    "cliente": "Clinica Sur",
    "fechaCorte": "2026-10-22",
    "nps": 8,
    "npsMuestra": 1,
    "rocActivos": 2,
    "mpbPendientes": 0,
    "proyectos": [
        project(1, nps=8, etapa="Completed", estado="Producción"),
        project(2, burn=150),
        *[project(n) for n in range(3, 9)],
    ],
    "roc": [],
    "oportunidades": [
        {"account": "Clinica Sur", "name": "OP.7", "stage": "Won"}
    ],
}


@pytest.fixture
def cuenta(monkeypatch, datos):
    monkeypatch.setattr(
        "apps.portal.services.account_screen.get_account_view", lambda c: VIEW
    )


def test_indicadores_y_alertas_salen_de_las_horas(portal, cuenta):
    portal.goto(portal.base + URL)

    kpis = portal.locator(".cuenta-kpis")
    expect(kpis).to_contain_text("8 NPS")
    expect(kpis).to_contain_text("8")  # total de proyectos
    # 50*7 + 150 = 500 h de 800 h presupuestadas
    expect(kpis).to_contain_text("63%")
    alerts = portal.locator("#cuenta-alerts")
    expect(alerts).to_contain_text("P2")
    expect(alerts).to_contain_text("Consumo mayor que el presupuesto")
    expect(portal.locator("#cuenta-opportunities")).to_contain_text("OP.7")


def test_la_tabla_pagina_y_busca_sin_acentos(portal, cuenta):
    portal.goto(portal.base + URL)
    label = portal.locator("#cuenta-page-label")
    expect(label).to_have_text("Mostrando 1–6 de 8 proyectos")

    portal.get_by_label("Buscar proyecto").fill("proyecto 7")
    expect(label).to_have_text("Mostrando 1–1 de 1 proyectos")

    portal.get_by_label("Buscar proyecto").fill("")
    portal.get_by_label("Filtrar por estado").select_option("Producción")
    expect(label).to_have_text("Mostrando 1–1 de 1 proyectos")


def test_los_enlaces_llevan_el_regreso(portal, cuenta):
    portal.goto(portal.base + URL)
    expect(portal.locator("#cuenta-page-label")).to_be_visible()

    compare = portal.get_by_role("link", name="Comparar margen vendido y real")
    assert "volver=%2Fcuenta%2Fclinica-sur%2F" in compare.get_attribute("href")
    first = portal.locator("tbody a").first
    assert "volver=" in first.get_attribute("href")
    back = portal.get_by_role("link", name="← Regresar a Operativa")
    expect(back).to_have_attribute("href", "/operativa/")


def test_una_cuenta_que_no_carga_dice_por_que(portal, datos, monkeypatch):
    monkeypatch.setattr(
        "apps.portal.services.account_screen.get_account_view",
        lambda c: {"ok": False, "error": "Sin conexión con Sheets"},
    )
    portal.goto(portal.base + URL)

    expect(portal.locator("#cuenta-error")).to_contain_text(
        "Sin conexión con Sheets"
    )
    assert (
        re.search(r"proyectos", visible(portal.locator("#cuenta-content")))
        is None
    )
