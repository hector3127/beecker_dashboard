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


def month_select(portal):
    return portal.get_by_label("Mes", exact=True)


def year_select(portal):
    return portal.get_by_label("Año", exact=True)


def test_structure_is_accessible_and_puts_processes_first(portal, loads):
    portal.goto(portal.base + PAGE)

    expect(portal.locator("#eva4-processes")).to_be_visible()
    assert portal.locator("main").count() == 1
    assert portal.locator("#eva4-processes thead th[scope=col]").count() == 15
    assert portal.locator("#eva4-processes caption").count() == 1
    order = portal.eval_on_selector_all(
        "#eva4-processes, #eva4-renewals, #eva4-clients",
        "els => els.map(e => e.id)",
    )
    assert order == ["eva4-processes", "eva4-renewals", "eva4-clients"]
    # Renovaciones y clientes quedan plegados bajo la tabla principal.
    folds = portal.locator("details.card.eva4-fold")
    assert folds.count() == 2
    assert folds.evaluate_all("els => els.every(e => !e.open)")
    expect(portal.locator("#eva4-count")).to_have_attribute("role", "status")
    expect(portal.locator("#eva4-subtitle")).to_have_text(
        "3 procesos activos · 2 por renovar"
    )
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
    assert "Sin dato" not in portal.locator("body").inner_text()


def test_search_filters_rows_ignoring_accents_and_updates_the_count(
    portal, loads
):
    portal.goto(portal.base + PAGE)
    count = portal.locator("#eva4-count")
    expect(count).to_have_text("3 de 3 procesos activos")
    search = portal.get_by_label(re.compile("Buscar procesos"))

    search.fill("cagsa")
    expect(count).to_have_text("1 de 3 procesos activos")
    assert portal.locator("#eva4-processes tbody tr:visible").count() == 1

    search.fill("NESTLE")  # sin acento y en mayusculas
    expect(count).to_have_text("2 de 3 procesos activos")

    search.fill("no existe")
    expect(count).to_have_text("0 de 3 procesos activos")
    search.fill("")
    expect(count).to_have_text("3 de 3 procesos activos")


def test_changing_the_month_keeps_the_page_and_the_return_context(
    portal, loads
):
    portal.goto(f"{portal.base}{PAGE}?volver=%2Foperativa%2F&mes=2026-10")
    expect(portal.locator("#eva4-source")).to_contain_text("Consumo 2026-10")
    portal.evaluate("window.marker = 'misma pagina'")

    month_select(portal).select_option("9")

    expect(portal.locator("#eva4-source")).to_contain_text("Consumo 2026-09")
    assert "mes=2026-09" in portal.url
    assert "volver=%2Foperativa%2F" in portal.url
    assert portal.evaluate("window.marker") == "misma pagina"  # sin recargar
    assert loads == ["2026-10", "2026-09"]

    portal.go_back()
    expect(portal.locator("#eva4-source")).to_contain_text("Consumo 2026-10")
    expect(month_select(portal)).to_have_value("10")
    assert loads == ["2026-10", "2026-09", "2026-10"]


def test_step_buttons_move_one_month_and_stop_at_the_limits(portal, loads):
    portal.goto(f"{portal.base}{PAGE}?mes=2026-10")
    previous = portal.get_by_role("button", name="Mes anterior")
    following = portal.get_by_role("button", name="Mes siguiente")
    expect(following).to_be_disabled()  # no hay meses futuros

    previous.click()
    expect(month_select(portal)).to_have_value("9")
    expect(following).to_be_enabled()

    portal.goto(f"{portal.base}{PAGE}?mes=2024-08")
    expect(portal.get_by_role("button", name="Mes anterior")).to_be_disabled()
    expect(year_select(portal)).to_have_value("2024")


def test_loading_state_blocks_the_picker_until_the_answer(portal, loads):
    def slow(route):
        portal.wait_for_timeout(800)
        route.continue_()

    portal.route(API, slow)
    portal.goto(portal.base + PAGE)

    expect(portal.locator("#eva4-content")).to_contain_text(
        "Consultando el mes"
    )
    expect(portal.locator(".month-picker")).to_have_attribute(
        "aria-busy", "true"
    )
    expect(portal.locator("#eva4-processes")).to_be_visible()
    expect(portal.locator(".month-picker")).not_to_have_attribute(
        "aria-busy", "true"
    )


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
    expect(portal.locator("#eva4-subtitle")).to_contain_text(
        "Servicios de automa"
    )
    expect(portal.locator("#eva4-processes")).to_have_count(0)
    expect(portal.locator("#eva4-search")).to_be_hidden()


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
    expect(month_select(portal)).to_have_value("10")
    expect(year_select(portal)).to_have_value("2026")


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
    month_select(portal).select_option("9")
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

        expect(portal.locator("#eva4-subtitle")).to_have_text(
            "1 procesos activos · 1 por renovar"
        )
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
    expect(rows.nth(1)).to_contain_text("Sin límite para este servicio")
    expect(rows.nth(2)).to_contain_text("Sin coincidencia en Clockify")
    assert "Sin dato" not in portal.locator("body").inner_text()


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
