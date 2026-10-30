"""Azure transitorio: API y cargas nuevas, misma presentación anterior."""

import copy

import pytest
from playwright.sync_api import expect

from tests.e2e.test_aer_executive import fixed_day as fixed_day
from tests.e2e.test_ixs_executive import PAGE
from tests.e2e.test_ixs_executive import ixs as ixs
from tests.e2e.test_ixs_planning_transport import planning as planning
from tests.e2e.test_project_detail_entry import project_detail as project_detail

pytestmark = pytest.mark.django_db(transaction=True)
API = "**/screens/proyectos/AMK.008/azure/*"


def enter(portal):
    portal.goto(portal.base + PAGE)
    portal.locator(".ixs-nav").get_by_role(
        "button", name="Azure DevOps", exact=True
    ).click()


def tab(portal, name):
    portal.locator(".ixs-nav").get_by_role(
        "button", name=name, exact=True
    ).click()


def test_api_initial_refresh_filters_and_drawer(
    portal, planning, fixed_day, monkeypatch
):
    from apps.portal.api import project_detail as api

    _, azure, _, _ = planning
    calls, requests = [], []

    def panel(project, force):
        calls.append((project, force))
        return copy.deepcopy(azure)

    monkeypatch.setattr(api, "get_ixs_panel", panel)
    portal.on("request", lambda r: requests.append(r.url))
    enter(portal)
    expect(portal.locator("#ixs-az84-person")).to_contain_text("Ana Pérez")
    portal.get_by_text("↻ Actualizar Azure", exact=True).click()
    expect(portal.locator("#ixs-az84-person")).to_contain_text("Ana Pérez")
    portal.wait_for_load_state("networkidle")
    assert calls == [("AMK.008", False), ("AMK.008", True)]
    assert not any(
        "/rpc/obtenerPanelAzureProyectoIXS/" in url for url in requests
    )
    portal.locator("#ixs-azure-wi-collapse > summary").click()
    portal.locator("#ixs-azure-filter-estado").select_option("Closed")
    expect(portal.locator("#ixs-azure-table tbody tr")).to_have_count(1)
    expect(portal.locator("#ixs-azure-table")).to_contain_text("Luis")
    portal.locator("#ixs-azure-filter-search").fill("inexistente")
    expect(portal.locator("#ixs-azure-table")).to_contain_text(
        "No hay work items"
    )
    portal.locator(".ixs-az85-person").first.get_by_role(
        "button", name="Ver ítems", exact=True
    ).click()
    expect(portal.locator(".ixs-az84-drawer")).to_be_visible()
    portal.get_by_role("button", name="Cerrar", exact=True).click()
    expect(portal.locator(".ixs-az84-drawer")).to_have_count(0)


@pytest.mark.parametrize("ok", [True, False])
def test_late_reply_does_not_replace_reentered_tab(
    portal, planning, fixed_day, ok
):
    held = []

    def hold(route):
        held.append(route)

    portal.route(API, hold)
    enter(portal)
    expect(portal.locator("#ixs-azure-stale")).to_have_text(
        "Cargando Azure DevOps…"
    )
    tab(portal, "Ejecutivo")
    portal.unroute(API, hold)
    tab(portal, "Azure DevOps")
    expect(portal.locator("#ixs-az84-person")).to_contain_text("Ana Pérez")
    held[0].fulfill(
        json={
            "data": {
                "ok": ok,
                "items": [],
                "allItems": [],
                "error": "Respuesta anterior",
            },
            "meta": {},
        }
    )
    portal.wait_for_load_state("networkidle")
    expect(portal.locator("#ixs-az84-person")).to_contain_text("Ana Pérez")
    expect(portal.locator("#ixs-tab-contenido")).not_to_contain_text(
        "Respuesta anterior"
    )


def test_transport_error_is_text_and_can_retry(portal, planning, fixed_day):
    def failure(route):
        route.fulfill(
            status=502,
            json={
                "error": {
                    "code": "source",
                    "message": '<img src=x onerror="window.injected=1">',
                }
            },
        )

    portal.route(API, failure)
    enter(portal)
    expect(portal.locator("#ixs-azure-stale")).to_contain_text(
        "Error al consultar Azure DevOps:"
    )
    expect(portal.locator("#ixs-azure-stale img")).to_have_count(0)
    assert portal.evaluate("window.injected") is None
    portal.unroute(API, failure)
    portal.get_by_text("↻ Actualizar Azure", exact=True).click()
    expect(portal.locator("#ixs-az84-person")).to_contain_text("Ana Pérez")
