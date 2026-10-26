"""EVA-04 en un navegador real: estructura, filtros, estados y alcance."""

import re

import pytest
from playwright.sync_api import expect

from apps.access.scope import AccessScope
from apps.portal.services import eva4
from tests.access.fake_provider import DictProvider
from tests.e2e.conftest import watch
from tests.portal.test_eva4 import TODAY
from tests.portal.test_eva4_api import report

pytestmark = pytest.mark.django_db(transaction=True)

PAGE = "/operativa/eva-4/"
API = "**/api/v1/screens/eva4/**"


@pytest.fixture
def loads(monkeypatch):
    """Fuente de EVA-04 de prueba; anota cada mes que se consulta."""
    calls = []

    def fake(*args):
        calls.append(args[0] if args else None)
        return {**report(), "month": args[0] if args else "2026-10"}

    monkeypatch.setattr(eva4, "load_eva4", fake)
    monkeypatch.setattr(eva4.timezone, "localdate", lambda: TODAY)
    return calls


def month_input(portal):
    return portal.locator("#eva4-month")


def test_structure_is_accessible_and_keeps_the_previous_order(portal, loads):
    portal.goto(portal.base + PAGE)

    expect(portal.locator("#eva4-processes")).to_be_visible()
    assert portal.locator("main").count() == 1
    assert portal.locator("#eva4-processes thead th[scope=col]").count() == 15
    assert portal.locator("#eva4-processes caption").count() == 1
    order = portal.eval_on_selector_all(
        "#eva4-processes, #eva4-renewals, #eva4-clients",
        "els => els.map(e => e.id)",
    )
    assert order == ["eva4-clients", "eva4-renewals", "eva4-processes"]
    assert portal.locator("details").count() == 0  # sin secciones plegadas
    expect(portal.locator(".eva4-kpis")).to_contain_text("3 activos")
    expect(portal.locator("#eva4-count")).to_have_attribute("role", "status")
    headers = portal.eval_on_selector_all(
        "#eva4-processes thead th", "els => els.map(e => e.textContent)"
    )
    assert headers == [
        "Delivery Manager",
        "Country",
        "Client",
        "BOT ID",
        "Service",
        "Process Name",
        "Status ROC",
        "Start",
        "Finish",
        "Average Limit",
        "Invested Hours",
        "Hours Balance",
        "Hours Package Limit",
        "Available Hours Package",
        "Risk",
    ]  # las columnas del Excel, en su orden


def filter_client_column(portal, value):
    table = portal.locator("#eva4-processes")
    table.get_by_role("button", name="Opciones de Client", exact=False).click()
    menu = portal.get_by_role("dialog", name="Opciones de Client", exact=True)
    condition = menu.get_by_label("Condición", exact=True)
    if not condition.is_visible():
        menu.locator("summary").filter(has_text="Filtrar por condición").click()
    condition.select_option("contains")
    menu.get_by_label("Valor de la condición", exact=True).fill(value)
    menu.get_by_role("button", name="Aceptar", exact=True).click()


def clear_process_columns(portal):
    portal.locator("#eva4-processes").locator(
        "xpath=ancestor::section"
    ).locator(".eva-column-clear").click()


def test_column_filter_replaces_search_and_updates_the_count(portal, loads):
    portal.goto(portal.base + PAGE)
    count = portal.locator("#eva4-count")
    expect(count).to_have_text("3 de 3 procesos activos")
    expect(portal.locator("#eva4-search")).to_have_count(0)

    filter_client_column(portal, "cagsa")
    expect(count).to_have_text("1 de 3 procesos activos")
    assert portal.locator("#eva4-processes tbody tr:visible").count() == 1

    filter_client_column(portal, "NESTLE")  # sin acento y en mayusculas
    expect(count).to_have_text("2 de 3 procesos activos")

    filter_client_column(portal, "no existe")
    expect(count).to_have_text("0 de 3 procesos activos")
    clear_process_columns(portal)
    expect(count).to_have_text("3 de 3 procesos activos")


def test_changing_the_month_keeps_the_page_and_the_return_context(
    portal, loads
):
    portal.goto(f"{portal.base}{PAGE}?volver=%2Foperativa%2F&mes=2026-10")
    expect(portal.locator("#eva4-source")).to_contain_text("Consumo 2026-10")
    portal.evaluate("window.marker = 'misma pagina'")

    month_input(portal).fill("2026-09")

    expect(portal.locator("#eva4-source")).to_contain_text("Consumo 2026-09")
    assert "mes=2026-09" in portal.url
    assert "volver=%2Foperativa%2F" in portal.url
    assert portal.evaluate("window.marker") == "misma pagina"  # sin recargar
    assert loads == ["2026-10", "2026-09"]

    portal.go_back()
    expect(portal.locator("#eva4-source")).to_contain_text("Consumo 2026-10")
    expect(month_input(portal)).to_have_value("2026-10")
    assert loads == ["2026-10", "2026-09", "2026-10"]


def test_month_field_stops_at_the_limits(portal, loads):
    portal.goto(f"{portal.base}{PAGE}?mes=2026-10")
    field = month_input(portal)
    expect(field).to_have_attribute("max", "2026-10")
    expect(field).to_have_attribute("min", "2024-08")


def test_loading_state_blocks_the_picker_until_the_answer(portal, loads):
    def slow(route):
        portal.wait_for_timeout(800)
        route.continue_()

    portal.route(API, slow)
    portal.goto(portal.base + PAGE)

    expect(portal.locator("#eva4-content")).to_contain_text(
        "Consultando el mes"
    )
    expect(month_input(portal)).to_be_disabled()
    expect(portal.locator("#eva4-processes")).to_be_visible()
    expect(month_input(portal)).to_be_enabled()


def test_server_failure_offers_a_retry_that_recovers(portal, loads):
    portal.route(API, lambda route: route.fulfill(status=502, body="<html>"))
    portal.goto(portal.base + PAGE)

    alert = portal.get_by_role("alert")
    expect(alert).to_contain_text("El servidor no pudo completar la consulta")
    expect(portal.locator("#eva4-processes")).to_have_count(0)

    portal.unroute(API)
    alert.get_by_role("button", name="Reintentar").click()
    expect(portal.locator("#eva4-processes")).to_be_visible()
    expect(portal.get_by_role("alert")).to_have_count(0)


def test_source_without_data_explains_why_and_hides_the_tables(
    portal, monkeypatch
):
    monkeypatch.setattr(eva4.timezone, "localdate", lambda: TODAY)
    monkeypatch.setattr(
        eva4,
        "load_eva4",
        lambda *a: {"available": False, "error": "ROC no responde."},
    )
    portal.goto(portal.base + PAGE)

    expect(portal.locator("#eva4-error")).to_have_text("ROC no responde.")
    expect(portal.locator(".eva4-banner p")).to_contain_text(
        "Servicios de automa"
    )
    expect(portal.locator("#eva4-processes")).to_have_count(0)
    expect(portal.locator("#eva4-search")).to_have_count(0)


def test_stale_cut_is_shown_with_a_warning(portal, monkeypatch):
    monkeypatch.setattr(eva4.timezone, "localdate", lambda: TODAY)
    stale = {**report(), "error": "Sheets no responde."}
    monkeypatch.setattr(eva4, "load_eva4", lambda *a: stale)
    portal.goto(portal.base + PAGE)

    expect(portal.locator("#eva4-error")).to_contain_text(
        "Sheets no responde. Se conserva el último corte disponible."
    )
    expect(portal.locator("#eva4-processes")).to_be_visible()


def test_invalid_month_in_the_url_shows_the_error_and_the_current_month(
    portal, monkeypatch
):
    monkeypatch.setattr(eva4.timezone, "localdate", lambda: TODAY)
    monkeypatch.setattr(
        eva4,
        "load_eva4",
        lambda *a: {
            "available": False,
            "error": "El mes debe tener el formato AAAA-MM.",
        },
    )
    portal.goto(f"{portal.base}{PAGE}?mes=zzz")

    expect(portal.locator("#eva4-error")).to_contain_text("formato AAAA-MM")
    expect(month_input(portal)).to_have_value("2026-10")


def test_text_from_the_sheet_is_shown_as_text_never_as_html(
    portal, monkeypatch
):
    monkeypatch.setattr(eva4.timezone, "localdate", lambda: TODAY)
    hostile = report()
    hostile["processes"][0]["process"] = '<img src=x onerror="window.pwn=1">'
    monkeypatch.setattr(eva4, "load_eva4", lambda *a: hostile)
    portal.goto(portal.base + PAGE)

    expect(portal.locator("#eva4-processes")).to_contain_text("<img src=x")
    assert portal.evaluate("window.pwn") is None
    assert portal.locator("#eva4-processes img").count() == 0


def test_back_link_returns_to_operativa(portal, loads, datos):
    portal.goto(portal.base + PAGE)

    portal.get_by_role("link", name="← Regresar a Operativa").click()

    portal.wait_for_url(re.compile(r"/operativa/$"))


def test_page_has_no_errors_or_csp_violations(portal, loads, settings):
    settings.CSP_REPORT_ONLY = True
    problems = watch(portal)

    portal.goto(portal.base + PAGE)
    expect(portal.locator("#eva4-processes")).to_be_visible()
    month_input(portal).fill("2026-09")
    expect(portal.locator("#eva4-source")).to_contain_text("2026-09")

    assert problems == []


def test_limited_scope_only_shows_the_allowed_accounts(
    portal, loads, settings, client, django_user_model
):
    settings.ACCESS_ENFORCED = True
    settings.ACCESS_PROVIDER = "tests.access.fake_provider.DictProvider"
    DictProvider.GRANTS = {
        "ana": (
            frozenset({"view_operations"}),
            AccessScope.limited(accounts=["Cagsa"]),
        )
    }
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
    try:
        portal.goto(portal.base + PAGE)

        expect(portal.locator(".eva4-kpis")).to_contain_text("1 activos")
        body = portal.locator("body")
        expect(body).to_contain_text("Cagsa")
        expect(body).not_to_contain_text("Nestlé")
        expect(portal.locator("#eva4-count")).to_have_text(
            "1 de 1 procesos activos"
        )
    finally:
        DictProvider.GRANTS = {}


def test_empty_cells_say_why_and_zero_hours_is_not_missing_data(
    portal, monkeypatch
):
    monkeypatch.setattr(eva4.timezone, "localdate", lambda: TODAY)
    data = report()
    zero, no_limit, no_match = data["processes"][:2] + data["processes"][3:]
    zero.update(invested_hours=0, hours_balance=30)
    no_limit.update(average_limit=None, hours_balance=None)
    no_match.update(invested_hours=None, hours_balance=None)
    monkeypatch.setattr(eva4, "load_eva4", lambda *a: data)
    portal.goto(portal.base + PAGE)

    rows = portal.locator("#eva4-processes tbody tr")
    first = rows.nth(0).locator("td")
    expect(first.nth(10)).to_have_text("0")  # cero real, no "sin dato"
    expect(rows.nth(1)).to_contain_text("Sin dato")
    expect(rows.nth(2).locator("[title]").first).to_have_attribute(
        "title", "Sin coincidencia en Clockify"
    )


@pytest.mark.parametrize(
    ("origin", "expected", "absent"),
    [
        ("database", "horas de Clockify (base de datos)", "08.Base Clockify"),
        ("sheet", "horas de Clockify (hoja 08.Base Clockify 2026)", "(base"),
    ],
)
def test_footer_names_where_the_hours_come_from(
    portal, monkeypatch, origin, expected, absent
):
    monkeypatch.setattr(eva4.timezone, "localdate", lambda: TODAY)
    data = {**report(), "hours_origin": origin}
    monkeypatch.setattr(eva4, "load_eva4", lambda *a: data)
    portal.goto(portal.base + PAGE)

    source = portal.locator("#eva4-source")
    expect(source).to_contain_text(expected)
    expect(source).not_to_contain_text(absent)
    expect(source).to_contain_text("Solo lectura")


def test_negative_balance_is_highlighted(portal, monkeypatch):
    monkeypatch.setattr(eva4.timezone, "localdate", lambda: TODAY)
    data = report()
    data["processes"][0].update(invested_hours=40, hours_balance=-10)
    monkeypatch.setattr(eva4, "load_eva4", lambda *a: data)
    portal.goto(portal.base + PAGE)

    cell = (
        portal.locator("#eva4-processes tbody tr").nth(0).locator("td").nth(11)
    )
    expect(cell).to_have_text("-10")
    expect(cell).to_have_class(re.compile("critical"))


@pytest.mark.parametrize("width", [1450, 390])
def test_process_column_menus_combine_with_client_and_month(
    portal, loads, width
):
    from pathlib import Path

    portal.set_viewport_size({"width": width, "height": 1000})
    portal.goto(portal.base + PAGE)
    table = portal.locator("#eva4-processes")
    expect(table.locator("thead button.eva-column-trigger")).to_have_count(15)
    table.get_by_role(
        "button", name="Opciones de Invested Hours", exact=True
    ).click()
    menu = portal.get_by_role(
        "dialog", name="Opciones de Invested Hours", exact=True
    )
    menu.locator("summary").filter(has_text="Filtrar por condición").click()
    menu.get_by_label("Condición", exact=True).select_option("gt")
    menu.get_by_label("Valor de la condición", exact=True).fill("10")
    target = Path("tmp/design/eva-column-menus")
    target.mkdir(parents=True, exist_ok=True)
    portal.screenshot(path=str(target / f"eva4-{width}.png"))
    menu.get_by_role("button", name="Aceptar", exact=True).click()
    expect(table.locator("tbody tr:visible")).to_have_count(2)
    filter_client_column(portal, "NESTLE")
    expect(table.locator("tbody tr:visible")).to_have_count(1)
    expect(portal.locator("#eva4-count")).to_have_text(
        "1 de 3 procesos activos"
    )
    portal.locator("#eva4-processes").locator(
        "xpath=ancestor::section"
    ).locator(".eva-column-clear").click()
    expect(table.locator("tbody tr:visible")).to_have_count(3)
    month_input(portal).fill("2026-09")
    expect(portal.locator("#eva4-source")).to_contain_text("Consumo 2026-09")
    expect(table.locator("thead button.eva-column-trigger")).to_have_count(15)


@pytest.mark.parametrize("width", [1450, 900, 390])
def test_eva4_reference_pagination_exports_and_responsive(
    portal, monkeypatch, width
):
    from pathlib import Path

    from tests.portal.test_eva4 import HEADER, row

    records = []
    for index in range(17):
        record = row(str(index))
        record[0] = "=1+1" if index == 0 else f"Cliente {index}"
        record[2] = f"ROC.TEST.{index:03}"
        records.append(record)
    data = eva4.build_eva4([HEADER, *records], TODAY)
    for process in data["processes"]:
        process.update(
            bot_label=process["bot_id"],
            invested_hours=12.5,
            average_limit=30,
            hours_balance=17.5,
        )
    data.update(
        month="2026-10",
        hours_origin="database",
        hours_source="08.Base Clockify 2026",
        unmatched_tasks=0,
        missing_limits=0,
    )
    monkeypatch.setattr(eva4, "load_eva4", lambda *a: data)
    monkeypatch.setattr(eva4.timezone, "localdate", lambda: TODAY)
    portal.set_viewport_size({"width": width, "height": 1100})
    portal.goto(portal.base + PAGE)
    table = portal.locator("#eva4-processes")
    expect(table.locator("tbody tr:visible")).to_have_count(10)
    expect(portal.locator("#eva4-processes-count")).to_have_text(
        "Mostrando 10 de 17 procesos"
    )
    for kind in ["processes", "clients", "renewals"]:
        with portal.expect_download() as result:
            portal.locator(f"#eva4-{kind}-export").click()
        content = Path(result.value.path()).read_text(encoding="utf-8-sig")
        assert len(content.splitlines()) == 18
        if kind in ["processes", "clients"]:
            assert '"\'=1+1"' in content
    portal.get_by_role(
        "button", name="processes página siguiente", exact=True
    ).click()
    expect(table.locator("tbody tr:visible")).to_have_count(7)
    filter_client_column(portal, "Cliente 16")
    expect(table.locator("tbody tr:visible")).to_have_count(1)
    with portal.expect_download() as result:
        portal.locator("#eva4-processes-export").click()
    assert (
        len(
            Path(result.value.path())
            .read_text(encoding="utf-8-sig")
            .splitlines()
        )
        == 2
    )
    clear_process_columns(portal)
    expect(table.locator("tbody tr:visible")).to_have_count(10)
    portal.get_by_label(
        "Filas por página de processes", exact=True
    ).select_option("25")
    expect(table.locator("tbody tr:visible")).to_have_count(17)
    portal.get_by_label(
        "Filas por página de processes", exact=True
    ).select_option("10")
    assert portal.evaluate("document.documentElement.scrollWidth <= innerWidth")
    target = Path("tmp/design/eva4-reference")
    target.mkdir(parents=True, exist_ok=True)
    portal.mouse.move(0, 0)
    portal.screenshot(path=str(target / f"eva4-{width}.png"), full_page=True)


def test_process_logos_and_removed_notices(portal, monkeypatch):
    import base64
    import json

    data = report()
    data["missing_limits"] = 1
    monkeypatch.setattr(eva4, "load_eva4", lambda *a: data)
    monkeypatch.setattr(eva4.timezone, "localdate", lambda: TODAY)
    portal.route(
        "**/api/v1/account-logos/",
        lambda route: route.fulfill(
            content_type="application/json",
            body=json.dumps(
                {
                    "data": {
                        "items": [
                            {
                                "key": "nestle mexico",
                                "url": "/eva4-test-logo.png",
                            }
                        ]
                    }
                }
            ),
        ),
    )
    portal.route(
        "**/eva4-test-logo.png",
        lambda route: route.fulfill(
            content_type="image/png",
            body=base64.b64decode(
                "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jRZkAAAAASUVORK5CYII="
            ),
        ),
    )
    portal.goto(portal.base + PAGE)
    expect(portal.locator("#eva4-processes td:nth-child(3) img")).to_have_count(
        2
    )
    expect(portal.locator("#eva4-search")).to_have_count(0)
    section = portal.locator("#eva4-processes").locator(
        "xpath=ancestor::section"
    )
    expect(section).not_to_contain_text(
        "procesos son de un servicio sin Average Limit"
    )
    expect(section).not_to_contain_text(
        "Las columnas de paquete permanecen sin dato"
    )
