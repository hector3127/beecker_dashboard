"""Diccionario de datos en el navegador: buscar y conservar la busqueda."""

import re

import pytest
from playwright.sync_api import expect

from apps.portal.services.data_dictionary import CONCEPTS

pytestmark = pytest.mark.django_db(transaction=True)


def test_la_busqueda_filtra_sin_acentos_y_vive_en_la_url(portal, datos):
    portal.goto(portal.base + "/diccionario-datos/")
    count = portal.locator("#dic-count")
    expect(count).to_have_text(f"{len(CONCEPTS)} conceptos")

    portal.get_by_label("Buscar en el diccionario").fill("facturacion")

    expect(count).to_contain_text(f" de {len(CONCEPTS)} conceptos")
    assert "q=facturacion" in portal.url
    expect(portal.get_by_role("rowheader", name="Facturación")).to_be_visible()

    portal.get_by_role("button", name="Limpiar búsqueda").click()
    expect(count).to_have_text(f"{len(CONCEPTS)} conceptos")
    assert "q=" not in portal.url


def test_una_busqueda_sin_resultados_lo_dice_y_se_restaura_de_la_url(
    portal, datos
):
    portal.goto(portal.base + "/diccionario-datos/?q=zzzz")

    expect(portal.get_by_label("Buscar en el diccionario")).to_have_value(
        "zzzz"
    )
    expect(portal.get_by_text("No encontramos coincidencias.")).to_be_visible()
    expect(portal.locator("#dic-count")).to_contain_text("0 de")


def test_el_glosario_de_business_overview_enlaza_al_diccionario(portal, datos):
    portal.goto(portal.base + "/")
    portal.get_by_text("¿Qué significa cada indicador?").click()
    portal.get_by_role(
        "link", name="Ver fórmulas, fuentes y validaciones"
    ).click()

    portal.wait_for_url(re.compile(r"/diccionario-datos/"))
    expect(
        portal.get_by_role("heading", name="Diccionario de datos")
    ).to_be_visible()
