"""Esfuerzo AER: presentación, rango, registros y ventana contra la anterior."""

from urllib.parse import parse_qs, urlparse

import pytest
from playwright.sync_api import expect

from tests.e2e.test_aer_executive import fixed_day as fixed_day
from tests.e2e.test_project_detail_entry import project_detail as project_detail

pytestmark = pytest.mark.django_db(transaction=True)
PAGE = "/proyectos/AER.001/"


@pytest.fixture
def effort(portal, project_detail):
    _, data = project_detail
    data["registros"] = [
        {
            "fecha": "2026-10-23",
            "recurso": "Ana",
            "actividad": "Desarrollo",
            "descripcion": f"Registro {i}",
            "inicio": "09:00",
            "fin": "10:00",
            "duracion": 1.25,
            "billable": bool(i % 2),
            "fueraHorario": bool(i % 3),
        }
        for i in range(7)
    ]
    response = {"ok": True, "registros": data["registros"], "total": 7}
    calls = []

    def read(route):
        calls.append(parse_qs(urlparse(route.request.url).query))
        route.fulfill(json={"data": response, "meta": {}})

    portal.route(lambda url: "/aer/registros/" in url, read)
    return data, response, calls


def enter(page):
    page.goto(page.base + PAGE)
    page.locator(".aer-tabs").get_by_role(
        "button", name="Esfuerzo", exact=True
    ).click()
    expect(page.locator(".aer-clockify-preview")).to_be_visible()


def test_query_uses_api_and_filters_only_records(portal, effort, fixed_day):
    _, _, calls = effort
    requests = []
    portal.on("request", lambda request: requests.append(request.url))
    enter(portal)
    before = portal.locator(".aer-vivid-top").inner_text()
    portal.locator("#aer-clock-desde").fill("2026-10-01")
    portal.locator("#aer-clock-hasta").fill("2026-10-23")
    portal.get_by_role("button", name="Aplicar", exact=True).click()
    expect(portal.locator("#aer-clock-desde")).to_have_value("2026-10-01")
    portal.wait_for_function(
        "!aerClockifyFiltro.cargando && "
        "Array.isArray(aerClockifyFiltro.registros)"
    )
    assert calls == [{"desde": ["2026-10-01"], "hasta": ["2026-10-23"]}]
    assert portal.locator(".aer-vivid-top").inner_text() == before
    assert portal.locator(".aer-clockify-preview tbody tr").count() == 5
    portal.get_by_role("button", name="Ver más (7)", exact=True).click()
    assert portal.locator("#aer-modal-wide-back tbody tr").count() == 7
    assert not any("/api/rpc/" in url for url in requests)


def test_invalid_range_and_error_retry(portal, effort, fixed_day):
    _, response, calls = effort
    enter(portal)
    portal.locator("#aer-clock-desde").fill("2026-10-24")
    portal.locator("#aer-clock-hasta").fill("2026-10-01")
    portal.once("dialog", lambda dialog: dialog.accept())
    portal.get_by_role("button", name="Aplicar", exact=True).click()
    assert not calls
    portal.locator("#aer-clock-hasta").fill("2026-10-25")
    response.update({"ok": False, "error": "Fallo simulado"})
    portal.get_by_role("button", name="Aplicar", exact=True).click()
    expect(portal.locator("#view-container")).to_contain_text("Fallo simulado")
    response["ok"] = True
    enter(portal)
    portal.get_by_role("button", name="Aplicar", exact=True).click()
    portal.wait_for_function(
        "!aerClockifyFiltro.cargando && "
        "Array.isArray(aerClockifyFiltro.registros)"
    )
    expect(portal.locator(".aer-clockify-preview")).to_be_visible()


def test_no_previous_renderers_and_safe_text(portal, effort, fixed_day):
    enter(portal)
    unsafe = '<img src=x onerror="window.injected=true">'
    portal.evaluate(
        """unsafe=>{
      const fail=()=>{throw Error('Old effort helper called');};
      _aerVistaEsfuerzo=_aerInitClockifyFiltro=_aerRegistrosClockifyActuales=fail;
      aerAbrirModalWide=aerConsultarRegistrosClockify=aerAbrirRegistrosClockify=fail;
      aerDashboardData.registros[0].descripcion=unsafe;
      _aerRenderTab();
    }""",
        unsafe,
    )
    expect(portal.locator(".aer-clockify-preview")).to_contain_text(unsafe)
    portal.get_by_role("button", name="Ver más (7)", exact=True).click()
    expect(portal.locator("#aer-modal-wide-back")).to_contain_text(unsafe)
    assert (
        portal.locator("#aer-modal-wide-back img, .aer-vivid-grid img").count()
        == 0
    )
    assert portal.evaluate("window.injected||false") is False
    portal.get_by_role("button", name="✕ Cerrar", exact=True).press("Enter")
    expect(portal.locator("#aer-modal-wide-back")).to_have_count(0)


def test_late_and_superseded_queries_do_not_overwrite_state(
    portal, effort, fixed_day
):
    held = []
    portal.route(
        lambda url: "/aer/registros/" in url, lambda route: held.append(route)
    )
    enter(portal)
    with portal.expect_request(
        lambda request: "/aer/registros/" in request.url
    ):
        portal.get_by_role("button", name="Aplicar", exact=True).click()
    portal.locator("#aer-clock-desde").fill("2026-10-01")
    with portal.expect_request(
        lambda request: "/aer/registros/" in request.url
    ):
        portal.get_by_role("button", name="Aplicar", exact=True).click()
    held[1].fulfill(
        json={"data": {"ok": True, "registros": [], "total": 0}, "meta": {}}
    )
    portal.wait_for_function("!aerClockifyFiltro.cargando")
    held[0].fulfill(json={"data": effort[1], "meta": {}})
    portal.wait_for_load_state("networkidle")
    assert portal.evaluate("aerClockifyFiltro.registros.length") == 0
    with portal.expect_request(
        lambda request: "/aer/registros/" in request.url
    ):
        portal.get_by_role("button", name="Aplicar", exact=True).click()
    portal.evaluate("() => {aerDashboardData={...aerDashboardData};}")
    held[2].fulfill(json={"data": effort[1], "meta": {}})
    portal.wait_for_load_state("networkidle")
    assert portal.evaluate("aerClockifyFiltro.registros.length") == 0
