"""Cliente/Acciones IXS: transporte nuevo y presentación conservada."""

import copy

import pytest
from playwright.sync_api import expect

from tests.e2e.test_aer_executive import fixed_day as fixed_day
from tests.e2e.test_ixs_executive import PAGE
from tests.e2e.test_ixs_executive import ixs as ixs
from tests.e2e.test_project_detail_entry import project_detail as project_detail

pytestmark = pytest.mark.django_db(transaction=True)


@pytest.fixture
def client_actions(portal, ixs, monkeypatch):
    from apps.portal.api import project_ai as api

    action = {
        "uid": "a1",
        "accion": "Revisar entrega",
        "responsable": "Ana Pérez",
        "estado": "Pendiente",
        "prioridad": "Alta",
        "fechaInicio": "2026-10-01",
        "fechaLimite": "2026-10-23",
        "fechaReal": "",
        "dependencia": "Cliente",
    }
    data = {
        "ok": True,
        "proyectoId": "AMK.008",
        "cliente": {
            "contactos": [
                {
                    "uid": "c1",
                    "nombre": "Ana Pérez",
                    "cargo": "Dirección",
                    "rol": "Sponsor",
                    "area": "TI",
                    "correo": "ana@example.com",
                    "telefono": "",
                    "nivelDecision": "Alto",
                    "estado": "Activo",
                    "canal": "Correo",
                    "alcance": "Proyecto",
                }
            ],
            "info": {},
            "gobierno": [],
            "documentos": [],
            "resumen": {},
        },
        "acciones": {
            "filas": [action],
            "abiertas": [action],
            "vencidas": [],
            "detenidas": [],
        },
        "partes": [],
    }
    calls = []

    def read(store, project):
        calls.append(project)
        return copy.deepcopy(data)

    monkeypatch.setattr(api.ixs_rpc, "build_store_sheets", lambda: None)
    monkeypatch.setattr(api.ixs_client, "read_client_actions", read)

    return data, calls


def enter(page, tab):
    page.goto(page.base + PAGE)
    page.locator(".ixs-nav").get_by_role("button", name=tab, exact=True).click()
    expect(
        page.locator(
            ".aer-client-shell" if tab == "Cliente" else ".aer-action-shell"
        )
    ).to_be_visible()
    page.wait_for_load_state("networkidle")


def test_api_cache_reused_between_tabs(portal, client_actions, fixed_day):
    _, calls = client_actions
    requests = []
    portal.on("request", lambda request: requests.append(request.url))
    enter(portal, "Cliente")
    portal.locator(".ixs-nav").get_by_role(
        "button", name="Acciones", exact=True
    ).click()
    expect(portal.locator(".aer-action-shell")).to_be_visible()
    portal.locator(".ixs-nav").get_by_role(
        "button", name="Cliente", exact=True
    ).click()
    expect(portal.locator(".aer-client-shell")).to_be_visible()
    assert calls == ["AMK.008"]
    assert any("/screens/proyectos/AMK.008/cliente/" in url for url in requests)
    assert not any("/ixsClienteAccionesLeer" in url for url in requests)


def test_source_error_retry_and_invalid_project(
    portal, client_actions, fixed_day
):
    data, _ = client_actions
    data.update(ok=False, error='<img src=x onerror="window.injected=true">')
    portal.goto(portal.base + PAGE)
    portal.locator(".ixs-nav").get_by_role(
        "button", name="Cliente", exact=True
    ).click()
    expect(portal.locator("#ixs-tab-contenido")).to_contain_text(data["error"])
    expect(portal.locator("#ixs-tab-contenido img")).to_have_count(0)
    data.update(ok=True, proyectoId="AJENO")
    data.pop("error")
    portal.evaluate("ixsCargarClienteAcciones()")
    expect(portal.locator("#ixs-tab-contenido")).to_contain_text(
        "respuesta de proyecto inválida"
    )
    data["proyectoId"] = "AMK.008"
    portal.evaluate("ixsCargarClienteAcciones()")
    expect(portal.locator(".aer-client-shell")).to_be_visible()


def test_left_tab_ignores_late_response(portal, client_actions, fixed_day):
    data, _ = client_actions
    held = []
    portal.route(
        "**/screens/proyectos/AMK.008/cliente/",
        lambda route: held.append(route),
    )
    portal.goto(portal.base + PAGE)
    portal.locator(".ixs-nav").get_by_role(
        "button", name="Cliente", exact=True
    ).click()
    expect(portal.locator("#ixs-tab-contenido")).to_contain_text(
        "Cargando información de cliente"
    )
    portal.locator(".ixs-nav").get_by_role(
        "button", name="Ejecutivo", exact=True
    ).click()
    held[0].fulfill(json={"data": data, "meta": {}})
    portal.wait_for_load_state("networkidle")
    expect(portal.locator(".aer-client-shell")).to_have_count(0)
