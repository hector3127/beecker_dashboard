"""Delivery Manager en el navegador: proyectos, horas por mes y regreso."""

import re

import pytest
from playwright.sync_api import expect

pytestmark = pytest.mark.django_db(transaction=True)

URL = "/operativa/delivery-manager/alberto/"
MONTHS = {
    "complete": True,
    "monthly_has_data": True,
    "monthly": [
        {
            "label": "Sep 2026",
            "total": 30,
            "budget": 50,
            "billable": 20,
            "operational": 6,
            "commercial": 4,
            "projects": [
                {
                    "id": "2",
                    "name": "=Portal",
                    "client": "Clinica Sur",
                    "service": "T&M",
                    "project_budget": 100,
                    "billable": 20,
                    "operational": 6,
                    "commercial": 4,
                    "total": 30,
                }
            ],
        }
    ],
}


@pytest.fixture
def horas(monkeypatch, datos):
    monkeypatch.setattr(
        "apps.portal.services.operational_sources.manager_monthly_history",
        lambda *args: MONTHS,
    )


def test_los_proyectos_critican_primero_y_enlazan_con_regreso(portal, datos):
    portal.goto(portal.base + URL)
    table = portal.locator("#dm-projects")

    expect(table).to_contain_text("Portal Pacientes")
    expect(portal.locator("#dm-sub")).to_contain_text("2 proyectos asignados")
    link = table.get_by_role("link", name="Portal Pacientes")
    assert (
        "volver=%2Foperativa%2Fdelivery-manager%2Falberto%2F"
        in link.get_attribute("href")
    )
    expect(
        portal.get_by_role("link", name="← Regresar a Operativa")
    ).to_be_visible()


def test_las_horas_por_mes_abren_el_detalle_y_descargan_csv(portal, horas):
    portal.goto(portal.base + URL)
    bar = portal.get_by_role("button", name=re.compile("Sep 2026: 30"))
    bar.click()

    dialog = portal.get_by_role("dialog", name=re.compile("Detalle de horas"))
    expect(dialog).to_contain_text("Clinica Sur")
    with portal.expect_download() as download:
        dialog.get_by_role("button", name="Descargar CSV").click()
    assert download.value.suggested_filename == "horas-Sep-2026.csv"
    path = download.value.path()
    text = open(path, encoding="utf-8-sig").read()
    assert "'=Portal" in text  # una formula no se ejecuta al abrir el CSV


def test_si_clockify_no_responde_la_pagina_lo_dice(portal, datos):
    portal.goto(portal.base + URL)

    expect(portal.locator("#dm-monthly")).to_contain_text(
        "No se pudo completar la consulta de Clockify"
    )
    expect(portal.locator("#dm-projects")).to_be_visible()
