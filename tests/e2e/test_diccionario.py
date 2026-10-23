"""Diccionario de datos en un navegador real: busqueda, URL y regreso."""

import pytest
from playwright.sync_api import expect

from apps.portal.services.data_dictionary import CONCEPTS

pytestmark = pytest.mark.django_db(transaction=True)

PAGE = "/diccionario-datos/"


def test_lists_every_concept_with_the_previous_layout(portal):
    portal.goto(portal.base + PAGE)

    expect(
        portal.get_by_role("heading", name="Diccionario de datos")
    ).to_be_visible()
    assert portal.locator("main").count() == 1
    expect(portal.locator("#dictionary-count")).to_have_text(
        f"{len(CONCEPTS)} conceptos"
    )
    assert portal.locator("[data-dictionary-entry]").count() == len(CONCEPTS)
    expect(portal.locator("#dictionary-updated")).to_have_text(
        "Definiciones al 22/10/2026"
    )
    expect(
        portal.get_by_role("link", name="Regresar a Business Overview")
    ).to_have_attribute("href", "/")


def test_search_ignores_accents_keeps_the_url_and_clears(portal):
    portal.goto(portal.base + PAGE)
    count = portal.locator("#dictionary-count")

    portal.fill("#dictionary-search", "MARGEN")
    shown = portal.locator("[data-dictionary-entry]:visible").count()
    assert 0 < shown < len(CONCEPTS)
    expect(count).to_have_text(f"{shown} de {len(CONCEPTS)} conceptos")
    assert "q=MARGEN" in portal.url

    portal.fill("#dictionary-search", "zzzz sin coincidencia")
    expect(portal.locator("#dictionary-empty")).to_be_visible()

    portal.click("#dictionary-clear")
    expect(count).to_have_text(f"{len(CONCEPTS)} conceptos")
    expect(portal.locator("#dictionary-empty")).to_be_hidden()
    assert "q=" not in portal.url


def test_the_search_in_the_url_is_applied_on_load(portal):
    portal.goto(f"{portal.base}{PAGE}?q=clockify")

    expect(portal.locator("#dictionary-search")).to_have_value("clockify")
    assert portal.locator("[data-dictionary-entry]:visible").count() < len(
        CONCEPTS
    )
    expect(portal.locator("#dictionary-clear")).to_be_visible()


def test_a_failed_request_offers_a_retry(portal):
    portal.route(
        "**/api/v1/reference/glossary/",
        lambda route: route.fulfill(status=500, body="x"),
    )
    portal.goto(portal.base + PAGE)

    expect(portal.get_by_role("alert")).to_contain_text("servidor")
    expect(portal.get_by_role("button", name="Reintentar")).to_be_visible()
