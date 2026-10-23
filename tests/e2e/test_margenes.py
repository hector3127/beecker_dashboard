"""Margen vendido vs. real en un navegador real: busqueda y alcance."""

import pytest
from playwright.sync_api import expect

from apps.access.scope import AccessScope
from tests.access.fake_provider import DictProvider

pytestmark = pytest.mark.django_db(transaction=True)

PAGE = "/ejecutiva/oportunidades/"


def test_the_page_uses_the_modular_frontend(portal, datos):
    portal.goto(portal.base + PAGE)

    expect(
        portal.get_by_role("heading", name="Margen vendido vs. real")
    ).to_be_visible()
    assert portal.locator("main").count() == 1
    assert portal.locator("link[href*='pages/margins.css']").count() == 1
    assert portal.locator(".opportunity-metrics article").count() == 5
    expect(portal.locator("#opportunity-count")).to_have_text(
        "2 de 2 oportunidades"
    )
    # Las fechas del filtro llegan con el periodo que calculo el servidor.
    assert portal.input_value("input[name=desde]")
    assert portal.input_value("input[name=hasta]")


def test_search_filters_rows_ignoring_accents(portal, datos):
    portal.goto(portal.base + PAGE)
    count = portal.locator("#opportunity-count")
    expect(count).to_have_text("2 de 2 oportunidades")

    portal.fill("#opportunity-search", "clínica")
    expect(count).to_have_text("1 de 2 oportunidades")
    assert portal.locator("tr[data-opportunity]:visible").count() == 1

    portal.fill("#opportunity-search", "OP.9")
    expect(count).to_have_text("1 de 2 oportunidades")
    expect(portal.locator("tr[data-opportunity]:visible")).to_contain_text(
        "ACME"
    )


def test_linked_ids_panel_opens_and_closes(portal, datos):
    portal.goto(portal.base + PAGE)
    toggle = portal.locator("[data-opportunity-toggle]").first
    panel = portal.locator(".opportunity-panel-row").first
    expect(panel).to_be_hidden()

    toggle.click()
    expect(panel).to_be_visible()
    expect(toggle).to_have_attribute("aria-expanded", "true")
    expect(toggle).to_have_text("Ocultar IDs ligados")

    toggle.click()
    expect(panel).to_be_hidden()
    expect(toggle).to_have_text("Ver IDs ligados")


def test_account_filter_keeps_the_account_and_the_return_link(portal, datos):
    portal.goto(f"{portal.base}{PAGE}?nombre=Clinica+Sur")

    expect(
        portal.get_by_role(
            "heading", name="Margen vendido vs. real · Clinica Sur"
        )
    ).to_be_visible()
    expect(portal.locator("tr[data-opportunity]")).to_have_count(1)
    expect(
        portal.get_by_role("link", name="← Regresar a Clinica Sur")
    ).to_be_visible()
    href = portal.get_by_role(
        "link", name="Ver lista por proyecto"
    ).get_attribute("href")
    assert "nombre=Clinica+Sur" in href and "vista=proyectos" in href


def test_a_failed_request_offers_a_retry(portal, datos):
    portal.route(
        "**/api/v1/screens/margenes/",
        lambda route: route.fulfill(status=500, body="x"),
    )
    portal.goto(portal.base + PAGE)

    expect(portal.get_by_role("alert")).to_contain_text("servidor")
    expect(portal.get_by_role("button", name="Reintentar")).to_be_visible()


def test_limited_scope_cannot_open_a_foreign_account(
    portal, datos, settings, client, django_user_model
):
    settings.ACCESS_ENFORCED = True
    settings.ACCESS_PROVIDER = "tests.access.fake_provider.DictProvider"
    client.force_login(django_user_model.objects.create_user("ana"))
    portal.context.add_cookies(
        [
            {
                "name": "sessionid",
                "value": client.cookies["sessionid"].value,
                "url": portal.base,
            }
        ]
    )
    DictProvider.GRANTS = {
        "ana": (
            frozenset({"view_costs"}),
            AccessScope.limited(accounts=["ACME"]),
        )
    }
    try:
        response = portal.goto(f"{portal.base}{PAGE}?nombre=Clinica+Sur")
        assert response is not None and response.status == 404
    finally:
        DictProvider.GRANTS = {}


def test_pending_values_are_not_shown_but_the_columns_stay(portal, datos):
    portal.goto(portal.base + PAGE)
    expect(portal.locator("#opportunity-count")).to_have_text(
        "2 de 2 oportunidades"
    )

    expect(
        portal.locator("th", has_text="Tarifa de costo vendida")
    ).to_be_visible()
    expect(portal.locator("th", has_text="Revenue operado")).to_be_visible()
    table = portal.locator("#margins-content table").first
    expect(table).not_to_contain_text("G · por validar")
    expect(table).not_to_contain_text("Por validar con Florencia")
    expect(portal.locator("td.sold-rate-pending").first).to_have_text("")


def test_glossary_explains_every_column_and_opens_on_demand(portal, datos):
    portal.goto(portal.base + PAGE)
    glossary = portal.locator("details.margins-glossary")
    expect(glossary).to_be_visible()
    assert glossary.get_attribute("open") is None
    expect(glossary.locator("dd").first).not_to_be_visible()

    glossary.locator("summary").click()
    for term in [
        "Bookings",
        "Revenue operado",
        "Facturado",
        "Cobrado",
        "Costos",
        "Tarifa de costo vendida",
        "Margen vendido",
        "Margen real",
        "Desviación (pp)",
    ]:
        expect(glossary.locator("dt", has_text=term).first).to_be_visible()
    expect(glossary.locator("footer a")).to_have_attribute(
        "href", "/diccionario-datos/"
    )
