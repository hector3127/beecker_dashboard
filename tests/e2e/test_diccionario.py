"""Diccionario de datos en un navegador real: busqueda, URL y regreso."""

import pytest
from playwright.sync_api import expect

from apps.portal.services.data_dictionary import CONCEPTS

pytestmark = pytest.mark.django_db(transaction=True)

PAGE = "/diccionario-datos/"


@pytest.mark.parametrize("query", ["", "?vista=anterior"])
def test_lists_every_concept_with_the_reference_layout(portal, query):
    portal.goto(portal.base + PAGE + query)

    expect(
        portal.get_by_role("heading", name="Glosario de indicadores")
    ).to_be_visible()
    assert portal.locator("main").count() == 1
    expect(portal.locator("#dictionary-count")).to_have_text(
        f"{len(CONCEPTS)} conceptos"
    )
    assert portal.locator("[data-dictionary-entry]").count() == len(CONCEPTS)
    expect(portal.locator("#dictionary-updated")).to_have_text(
        "Definiciones al 17/11/2026"
    )
    expect(
        portal.get_by_role("link", name="Volver al resumen ejecutivo")
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


@pytest.mark.parametrize("suffix", ["", "&vista=anterior"])
def test_the_search_in_the_url_is_applied_on_load(portal, suffix):
    portal.goto(f"{portal.base}{PAGE}?q=clockify{suffix}")

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


def test_reference_layout_preserves_every_original_definition(portal):
    portal.goto(portal.base + PAGE)
    expect(portal.locator("#dictionary-count")).to_have_text(
        f"{len(CONCEPTS)} conceptos"
    )
    expect(portal.locator(".dictionary-table thead th")).to_have_count(3)
    for index, (name, definition, _source) in enumerate(CONCEPTS):
        row = portal.locator("[data-dictionary-entry]").nth(index)
        expect(row.locator(".dictionary-concept")).to_have_text(name)
        expect(row.locator("td").nth(0)).to_have_text(definition)
        expect(row.locator("td").nth(1)).not_to_be_empty()
    expect(
        portal.locator(".dictionary-source-badge, .dictionary-notes")
    ).to_have_count(0)


def test_categories_search_order_and_reset_work_together(portal, enforced_csp):
    portal.goto(portal.base + PAGE)
    expect(portal.locator("#dictionary-count")).to_have_text(
        f"{len(CONCEPTS)} conceptos"
    )
    portal.get_by_role("button", name="Financieros", exact=True).click()
    expect(portal.locator("#dictionary-category")).to_have_value("Financieros")
    portal.fill("#dictionary-search", "tarifa")
    visible = portal.locator("[data-dictionary-entry]:visible")
    assert 0 < visible.count() < len(CONCEPTS)
    for row in visible.all():
        expect(row).to_have_attribute("data-category", "Financieros")
    heading = portal.get_by_role("columnheader", name="Indicador")
    heading.get_by_role("button").click()
    expect(heading).to_have_attribute("aria-sort", "ascending")
    heading.get_by_role("button").click()
    expect(heading).to_have_attribute("aria-sort", "descending")
    assert "orden=name" in portal.url and "sentido=desc" in portal.url
    portal.reload()
    expect(portal.locator("#dictionary-search")).to_have_value("tarifa")
    expect(portal.locator("#dictionary-category")).to_have_value("Financieros")
    expect(
        portal.get_by_role("columnheader", name="Indicador")
    ).to_have_attribute("aria-sort", "descending")
    portal.click("#dictionary-clear")
    expect(portal.locator("#dictionary-search")).to_have_value("")
    expect(portal.locator("#dictionary-category")).to_have_value("")
    expect(portal.locator("#dictionary-count")).to_have_text(
        f"{len(CONCEPTS)} conceptos"
    )
    assert "categoria=" not in portal.url and "orden=" not in portal.url


@pytest.mark.parametrize("width", [1450, 900, 390])
def test_dictionary_reference_design_is_responsive(portal, width, enforced_csp):
    from pathlib import Path

    portal.set_viewport_size({"width": width, "height": 1000})
    portal.goto(portal.base + PAGE)
    expect(portal.locator("#dictionary-count")).to_have_text(
        f"{len(CONCEPTS)} conceptos"
    )
    expect(portal.locator(".dictionary-entry-icon")).to_have_count(
        len(CONCEPTS)
    )
    expect(portal.locator("#dictionary-clear")).to_be_visible()
    assert portal.evaluate(
        "document.documentElement.scrollWidth <= window.innerWidth"
    )
    portal.select_option("#dictionary-category", "Operativos")
    expect(
        portal.get_by_role("button", name="Operativos", exact=True)
    ).to_have_attribute("aria-pressed", "true")
    portal.click("#dictionary-clear")
    output = Path("tmp/design/dictionary-reference")
    output.mkdir(parents=True, exist_ok=True)
    portal.screenshot(
        path=str(output / f"dictionary-{width}.png"), full_page=width > 700
    )
