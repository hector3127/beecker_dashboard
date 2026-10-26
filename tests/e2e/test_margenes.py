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
    expect(portal.locator(".account-group-row:visible")).to_contain_text("ACME")
    expect(portal.locator("tr[data-opportunity]:visible")).to_contain_text(
        "OP.9"
    )


def test_linked_ids_panel_opens_and_closes(portal, datos):
    portal.goto(portal.base + PAGE)
    toggle = portal.locator("[data-opportunity-toggle]").first
    panel = portal.locator(".opportunity-panel-row").first
    expect(panel).to_be_hidden()

    portal.locator(".account-group-toggle").first.click()
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


def test_sold_cost_rate_column_is_removed(portal, datos):
    portal.goto(portal.base + PAGE)
    expect(portal.locator("#opportunity-count")).to_have_text(
        "2 de 2 oportunidades"
    )

    expect(
        portal.locator("th", has_text="Tarifa de costo vendida")
    ).to_have_count(0)
    expect(portal.locator("th", has_text="Revenue operado")).to_be_visible()
    table = portal.locator("#margins-content table").first
    expect(table).not_to_contain_text("G · por validar")
    expect(table).not_to_contain_text("Por validar con Florencia")
    # Las diez celdas mantienen la alineación de los encabezados.
    assert (
        portal.locator("tr[data-opportunity]").first.locator("td").count() == 10
    )


@pytest.mark.parametrize("width", [1450, 900, 390])
def test_glossary_explains_every_column_and_opens_on_demand(
    portal, datos, width
):
    portal.set_viewport_size({"width": width, "height": 1000})
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
        "Margen vendido",
        "Margen real",
        "Desviación (pp)",
    ]:
        expect(glossary.locator("dt", has_text=term).first).to_be_visible()
    expect(glossary.locator("footer a")).to_have_attribute(
        "href", "/diccionario-datos/"
    )
    expect(glossary.locator(".glossary-definition-card")).to_have_count(3)
    expect(glossary.locator(".glossary-definition")).to_have_count(11)
    expect(glossary.locator(".glossary-definition svg")).to_have_count(11)
    expect(
        glossary.get_by_role("heading", name="Notas importantes")
    ).to_be_visible()
    assert glossary.evaluate("e => e.scrollWidth <= e.clientWidth + 1")
    assert portal.evaluate(
        "document.documentElement.scrollWidth <= window.innerWidth"
    )
    from pathlib import Path

    output = Path("tmp/design/margins-glossary")
    output.mkdir(parents=True, exist_ok=True)
    glossary.screenshot(path=str(output / f"glossary-{width}.png"))
    glossary.locator("summary").click()
    expect(glossary.locator("dd").first).to_be_hidden()


@pytest.mark.parametrize("width", [1450, 900, 390])
def test_redesigned_groups_and_responsive_controls(portal, datos, width):
    from pathlib import Path

    portal.set_viewport_size({"width": width, "height": 1000})
    portal.goto(f"{portal.base}{PAGE}?periodo=anio&anio=2026")
    expect(portal.locator("#opportunity-count")).to_have_text(
        "2 de 2 oportunidades"
    )
    expect(portal.locator(".account-group-toggle")).to_have_count(2)
    expect(portal.locator(".opportunity-metrics article")).to_have_count(5)
    expect(portal.locator(".opportunity-metrics svg")).to_have_count(5)
    group = portal.locator(".account-group-toggle").first
    section = portal.locator(".account-opportunities").first
    expect(section).to_be_hidden()
    group.click()
    expect(section).to_be_visible()
    original = section.inner_text()
    group.click()
    expect(group).to_have_attribute("aria-expanded", "false")
    expect(section).to_be_hidden()
    # La búsqueda abre el grupo que contiene la coincidencia.
    portal.fill("#opportunity-search", "OP.9")
    expect(portal.locator("#opportunity-count")).to_have_text(
        "1 de 2 oportunidades"
    )
    expect(portal.locator(".account-group-row:visible")).to_have_count(1)
    portal.fill("#opportunity-search", "")
    expect(section).to_be_visible()
    assert section.inner_text() == original
    assert portal.evaluate(
        "document.documentElement.scrollWidth <= window.innerWidth"
    )
    glossary = portal.locator("details.margins-glossary")
    glossary.locator("summary").click()
    expect(glossary.locator("dd").first).to_be_visible()
    assert portal.evaluate(
        "document.documentElement.scrollWidth <= window.innerWidth"
    )
    glossary.locator("summary").click()
    output = Path("tmp/design/margins-compact")
    output.mkdir(parents=True, exist_ok=True)
    portal.screenshot(path=str(output / f"margins-{width}.png"), full_page=True)


def test_account_group_contains_multiple_opportunities_without_changing_values(
    portal, datos
):
    def same_account(route):
        response = route.fetch()
        body = response.json()
        for opportunity in body["data"]["opportunities"]:
            opportunity["account"] = "Cuenta compartida de prueba"
        route.fulfill(response=response, json=body)

    portal.route("**/api/v1/screens/margenes/", same_account)
    portal.goto(portal.base + PAGE)
    expect(portal.locator("#opportunity-count")).to_have_text(
        "2 de 2 oportunidades"
    )
    expect(portal.locator(".account-group-toggle")).to_have_count(1)
    expect(portal.locator(".account-group-count")).to_have_text(
        "2 oportunidades"
    )
    expect(portal.locator("tr[data-opportunity]")).to_have_count(2)
    expect(portal.locator("tr[data-opportunity]").first).to_contain_text(
        "55.00%"
    )
    expect(portal.locator("tr[data-opportunity]").last).to_contain_text(
        "40.00%"
    )
    group = portal.locator(".account-group-toggle")
    expect(portal.locator("tr[data-opportunity]:visible")).to_have_count(0)
    group.click()
    expect(portal.locator("tr[data-opportunity]:visible")).to_have_count(2)
    portal.locator(".account-group-action").click()
    expect(portal.locator("tr[data-opportunity]:visible")).to_have_count(0)


def test_shared_cost_shows_available_values_with_partial_reference(
    portal, datos
):
    def shared_opportunity(route):
        response = route.fetch()
        body = response.json()
        row = body["data"]["opportunities"][0]
        row.update(
            allocation_pending=True,
            partial=True,
            cost=3550.26,
            actual_margin=-44.18,
            deviation_pp=-170.68,
            sold_margin=126.5,
        )
        for project in row["projects"]:
            project.update(
                shared=True,
                partial=True,
                margin=-44.18,
                gross_profit=-1087.86,
            )
        other = body["data"]["opportunities"][1]
        other.update(
            allocation_pending=False,
            partial=False,
            actual_margin=60,
            deviation_pp=0,
            sold_margin=60,
        )
        route.fulfill(response=response, json=body)

    portal.route("**/api/v1/screens/margenes/", shared_opportunity)
    portal.route(
        "**/api/v1/costs/project/**",
        lambda route: route.fulfill(
            json={
                "data": {
                    "id": "SHARED",
                    "scope_start": "2026-01-01",
                    "scope_end": "2026-10-25",
                    "sprints": [],
                    "people": [
                        {
                            "name": "Sin tarifa",
                            "hours": 10.25,
                            "band": "",
                            "band_month": "",
                            "rate": None,
                            "cost": 0,
                            "missing": True,
                        },
                        {
                            "name": "Cero conocido",
                            "hours": 0,
                            "band": "A2",
                            "band_month": "octubre",
                            "rate": 7.04,
                            "cost": 0,
                            "missing": False,
                        },
                    ],
                },
                "meta": {},
            }
        ),
    )
    portal.goto(portal.base + PAGE)
    expect(portal.locator("#opportunity-count")).to_have_text(
        "2 de 2 oportunidades"
    )
    portal.locator(".account-group-toggle").first.click()
    main = portal.locator("tr[data-opportunity]").first
    expect(main).to_contain_text("126.50%")
    expect(main).to_contain_text("Validar dato de origen (>100%)")
    expect(main).to_contain_text("Referencia compartida")
    expect(main).not_to_contain_text("Pendiente de asignación")
    expect(main).to_contain_text("-44.18%*")
    expect(main).to_contain_text("-170.68 pp*")
    other = portal.locator("tr[data-opportunity]").last
    expect(other).to_contain_text("60.00%")
    expect(other).to_contain_text("0.00 pp")
    expect(other.locator(".margin-unassigned")).to_have_count(0)
    main.locator("[data-opportunity-toggle]").click()
    panel = portal.locator(".opportunity-panel-row").first
    expect(panel).not_to_contain_text("Pendiente de asignación")
    expect(panel).to_contain_text("-44.18%*")
    panel.locator(".opportunity-people summary").first.click()
    people = panel.locator(".opportunity-people-content").first
    missing = people.get_by_role("row").filter(has_text="Sin tarifa")
    expect(missing).to_contain_text("Pendiente")
    expect(missing).not_to_contain_text("$0")
    valid_zero = people.get_by_role("row").filter(has_text="Cero conocido")
    expect(valid_zero).to_contain_text("$0")
    expect(valid_zero).to_contain_text("Horas × tarifa")


def test_collapsed_account_totals_stay_global_during_search(portal, datos):
    portal.goto(portal.base + PAGE)
    expect(portal.locator("#opportunity-count")).to_have_text(
        "2 de 2 oportunidades"
    )
    header = portal.locator(".account-group-row").first
    expect(header.locator("td")).to_have_count(10)
    expect(header.locator("td").nth(1)).to_contain_text("$500")
    expect(header.locator("td").nth(6)).to_contain_text("55.00%")
    expect(header.locator("td").nth(5)).to_contain_text("Pendiente")
    before = [header.locator("td").nth(i).inner_text() for i in range(1, 9)]
    portal.fill("#opportunity-search", "OP.9")
    expect(portal.locator(".account-group-row:visible")).to_have_count(1)
    after = [header.locator("td").nth(i).inner_text() for i in range(1, 9)]
    assert before == after


@pytest.mark.parametrize("width", [1450, 900, 390])
def test_method_cards_keep_the_current_rules_and_fold(portal, datos, width):
    from pathlib import Path

    portal.set_viewport_size({"width": width, "height": 1000})
    portal.goto(portal.base + PAGE)
    method = portal.locator(".opportunity-method")
    expect(method).to_be_visible()
    cards = method.locator(".method-info-card")
    expect(cards).to_have_count(6)
    expect(cards.first).to_be_hidden()
    method.locator("summary").click()
    expect(cards.first).to_be_visible()
    expect(method.get_by_role("heading", name="Qué representa")).to_be_visible()
    expect(method.get_by_role("heading", name="Qué incluye")).to_be_visible()
    expect(method.locator(".method-scope")).to_contain_text("se excluyen")
    expect(method.locator(".method-margins")).to_contain_text(
        "(revenue del periodo − costos) ÷ revenue del periodo"
    )
    expect(method.locator(".method-deviation")).to_contain_text(
        "Margen real − margen vendido"
    )
    expect(method.locator(".method-notes")).to_contain_text(
        "una sola vez por registro de horas"
    )
    assert method.evaluate("e => e.scrollWidth <= e.clientWidth + 1")
    assert portal.evaluate(
        "document.documentElement.scrollWidth <= window.innerWidth"
    )
    output = Path("tmp/design/margins-method")
    output.mkdir(parents=True, exist_ok=True)
    method.screenshot(path=str(output / f"method-{width}.png"))
    method.locator("summary").click()
    expect(cards.first).to_be_hidden()
