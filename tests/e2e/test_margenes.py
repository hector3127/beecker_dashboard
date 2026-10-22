"""Comparativa de margenes en el navegador: buscar, desglose y fechas."""

import re

import pytest
from playwright.sync_api import expect

pytestmark = pytest.mark.django_db(transaction=True)

PERIODO = "periodo=anio&anio=2026"


def test_buscar_filtra_las_oportunidades_sin_acentos(portal, datos):
    portal.goto(f"{portal.base}/ejecutiva/oportunidades/?{PERIODO}")
    count = portal.locator("#mg-count")
    expect(count).to_have_text("2 de 2 oportunidades")

    portal.get_by_label("Buscar cuenta, oportunidad o proyecto").fill("clínica")

    expect(count).to_have_text("1 de 2 oportunidades")
    # Las filas ocultas siguen en el DOM: se cuentan solo las que se ven.
    expect(portal.get_by_role("row", name=re.compile("OP.7"))).to_have_count(1)
    expect(portal.get_by_role("row", name=re.compile("OP.9"))).to_have_count(0)


def test_el_desglose_de_ids_se_abre_y_se_cierra(portal, datos):
    portal.goto(f"{portal.base}/ejecutiva/oportunidades/?{PERIODO}")
    button = portal.locator("[aria-controls=mg-panel-1]")
    panel = portal.locator("#mg-panel-1")
    expect(panel).to_be_hidden()

    button.click()
    expect(panel).to_be_visible()
    expect(button).to_have_attribute("aria-expanded", "true")

    button.click()
    expect(panel).to_be_hidden()


def test_aplicar_fechas_conserva_la_cuenta_y_el_regreso(portal, datos):
    portal.goto(
        f"{portal.base}/ejecutiva/oportunidades/?nombre=Clinica+Sur&{PERIODO}"
        "&volver=%2Fejecutiva%2Fcuentas%2F"
    )
    portal.get_by_label("Fecha inicio").fill("2026-02-01")
    portal.get_by_role("button", name="Aplicar fechas").click()

    portal.wait_for_url(re.compile(r"desde=2026-02-01"))
    assert "nombre=Clinica+Sur" in portal.url
    assert "volver=%2Fejecutiva%2Fcuentas%2F" in portal.url
    expect(
        portal.get_by_role("link", name="← Regresar a Todas las cuentas")
    ).to_be_visible()
