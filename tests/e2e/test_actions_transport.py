"""Acciones: operaciones por API y paridad con la vista anterior."""

import copy
from pathlib import Path

import pytest
from playwright.sync_api import expect

from tests.e2e.test_aer_executive import PAGE as AER_PAGE
from tests.e2e.test_aer_executive import fixed_day as fixed_day
from tests.e2e.test_ixs_client_actions_transport import (
    client_actions as client_actions,
)
from tests.e2e.test_ixs_effort import state as capture_state
from tests.e2e.test_ixs_executive import PAGE as IXS_PAGE
from tests.e2e.test_ixs_executive import ixs as ixs
from tests.e2e.test_project_detail_entry import project_detail as project_detail

pytestmark = pytest.mark.django_db(transaction=True)


@pytest.fixture(params=["aer", "ixs"])
def family(request):
    return request.param


@pytest.fixture
def board(request, portal, family):
    if family == "ixs":
        dashboard, _ = request.getfixturevalue("client_actions")
    else:
        _, dashboard = request.getfixturevalue("project_detail")
    rows = [
        {
            "uid": "a1",
            "accion": "Revisar entrega",
            "responsable": "Ana",
            "estado": "Pendiente",
            "prioridad": "Alta",
            "fechaInicio": "2026-10-01",
            "fechaLimite": "2026-10-23",
            "fechaReal": "",
            "dependencia": "Cliente",
            "notas": "Notas",
        }
    ]
    actions = {"filas": rows, "abiertas": rows, "vencidas": [], "detenidas": []}
    parts = [
        {
            "uid": "p1",
            "accion": "Dar acceso",
            "responsable": "Cliente",
            "estado": "Pendiente",
            "fechaLimite": "2026-10-23",
            "proximaRevision": "2026-10-24",
            "notas": "Permisos",
        }
    ]
    dashboard["acciones"] = copy.deepcopy(actions)
    dashboard["partes"] = copy.deepcopy(parts)
    results = {
        "guardar": {"ok": True, "acciones": actions},
        "actualizar": {"ok": True, "acciones": actions},
        "limpiar-duplicados": {
            "ok": True,
            "eliminados": 0,
            "acciones": actions,
        },
        "eliminar": {"ok": True},
        "leer": {"ok": True, "acciones": actions},
        "partes-leer": {"ok": True, "filas": parts},
        "parte-guardar": {"ok": True, "filas": parts},
        "parte-actualizar": {"ok": True, "filas": parts},
        "parte-eliminar": {"ok": True, "filas": []},
    }
    calls = []

    def api(route):
        suffix = (
            route.request.url.split("/acciones/", 1)[1].split("?")[0].strip("/")
        )
        operation = "partes-leer" if suffix == "partes" else suffix or "leer"
        calls.append(
            (
                operation,
                route.request.post_data_json
                if route.request.method == "POST"
                else None,
            )
        )
        route.fulfill(json={"data": results[operation], "meta": {}})

    def rpc(route):
        name = route.request.url.rstrip("/").rsplit("/", 1)[-1]
        if name in {"listarAccionesPartesAER", "ixsListarAccionesPartes"}:
            route.fulfill(json={"ok": True, "result": results["partes-leer"]})
        else:
            route.fallback()

    portal.route(
        lambda url: "/api/v1/screens/proyectos/" in url and "/acciones/" in url,
        api,
    )
    portal.route("**/api/rpc/**", rpc)
    return results, calls


def enter(page, family, previous=False):
    page.goto(
        page.base
        + (AER_PAGE if family == "aer" else IXS_PAGE)
        + ("?vista=anterior" if previous else "")
    )
    page.locator(".aer-tabs" if family == "aer" else ".ixs-nav").get_by_role(
        "button", name="Acciones", exact=True
    ).click()
    expect(page.locator(".aer-action-shell")).to_be_visible()
    page.wait_for_load_state("networkidle")


@pytest.mark.parametrize("width", [1450, 900, 390])
def test_model_keeps_shared_view(portal, board, family, fixed_day, width):
    states = []
    portal.set_viewport_size({"width": width, "height": 1000})
    directory = (
        Path("tmp/migration/project_detail/actions_transport")
        / family
        / str(width)
    )
    directory.mkdir(parents=True, exist_ok=True)
    for previous in [True, False]:
        enter(portal, family, previous)
        portal.mouse.move(0, 0)
        states.append(
            capture_state(portal, ".aer-action-shell, .aer-action-shell *")
        )
        portal.screenshot(
            path=str(directory / ("old.png" if previous else "new.png")),
            full_page=True,
        )
    assert states[0] == states[1]


def test_save_retry_and_inline_edit_use_api(portal, board, family, fixed_day):
    results, calls = board
    requests = []
    portal.on("request", lambda request: requests.append(request.url))
    enter(portal, family)
    portal.get_by_role("button", name="+ Agregar acción", exact=True).click()
    portal.locator("#aa-a").fill("Acción nueva")
    results["guardar"] = {"ok": False, "error": "Fallo simulado"}
    portal.locator("#aer-modal-back").get_by_role(
        "button", name="Guardar", exact=True
    ).click()
    expect(portal.locator(".aer-toast")).to_contain_text("Fallo simulado")
    expect(portal.locator("#aa-a")).to_have_value("Acción nueva")
    results["guardar"] = {"ok": True, "acciones": results["leer"]["acciones"]}
    portal.locator("#aer-modal-back").get_by_role(
        "button", name="Guardar", exact=True
    ).click()
    expect(portal.locator("#aer-modal-back")).to_have_count(0)
    saved = [b for op, b in calls if op == "guardar"][-1]
    assert saved["servicio"] == family
    assert saved["Accion"] == "Acción nueva"
    portal.locator("#aer-actions-table-body input").first.fill("Luis")
    portal.locator("#aer-actions-table-body input").first.press("Tab")
    portal.wait_for_load_state("networkidle")
    assert any(op == "actualizar" and b["valor"] == "Luis" for op, b in calls)
    assert not any("/api/rpc/" in url for url in requests)


def test_delete_confirmation_reload_and_cleanup(
    portal, board, family, fixed_day
):
    _, calls = board
    enter(portal, family)
    portal.once("dialog", lambda dialog: dialog.dismiss())
    portal.locator("#aer-actions-table-body button.danger").first.click()
    assert not any(op == "eliminar" for op, _ in calls)
    portal.once("dialog", lambda dialog: dialog.accept())
    with portal.expect_response(lambda response: "/acciones/?" in response.url):
        portal.locator("#aer-actions-table-body button.danger").first.click()
    portal.wait_for_load_state("networkidle")
    assert [op for op, _ in calls][-2:] == ["eliminar", "leer"]
    portal.once("dialog", lambda dialog: dialog.accept())
    portal.get_by_role("button", name="Limpiar duplicados", exact=True).click()
    portal.wait_for_load_state("networkidle")
    assert calls[-1][0] == "limpiar-duplicados"


def test_parts_save_edit_and_delete(portal, board, family, fixed_day):
    _, calls = board
    enter(portal, family)
    portal.get_by_role(
        "button", name="＋ Agregar pendiente", exact=True
    ).click()
    portal.locator("#aerp-new-accion").fill("Pendiente nuevo")
    portal.locator("#aerp-new-save").click()
    expect(portal.locator("#aer-modal-back")).to_have_count(0)
    assert calls[-1][0] == "parte-guardar"
    assert calls[-1][1]["datos"]["accion"] == "Pendiente nuevo"
    portal.locator("#aeri-partes-card textarea[aria-label=Notas]").fill(
        "Revisado"
    )
    portal.locator("#aeri-partes-card textarea[aria-label=Notas]").press("Tab")
    expect(portal.locator("#aeri-partes-status")).to_have_text("✓ Guardado")
    assert calls[-1][0] == "parte-actualizar"
    portal.once("dialog", lambda dialog: dialog.accept())
    portal.get_by_role("button", name="Eliminar pendiente", exact=True).click()
    expect(portal.locator("#aeri-partes-card")).to_contain_text(
        "Sin pendientes registrados"
    )
    assert calls[-1][0] == "parte-eliminar"


def test_save_response_does_not_close_a_new_editor(
    portal, board, family, fixed_day
):
    results, _ = board
    held = []
    portal.route("**/acciones/guardar/", lambda route: held.append(route))
    enter(portal, family)
    portal.get_by_role("button", name="+ Agregar acción", exact=True).click()
    portal.locator("#aa-a").fill("Primer borrador")
    with portal.expect_request(
        lambda req: req.url.endswith("/acciones/guardar/")
    ):
        portal.locator("#aer-modal-back").get_by_role(
            "button", name="Guardar", exact=True
        ).click()
    portal.evaluate("aerCerrarModal()")
    portal.get_by_role("button", name="+ Agregar acción", exact=True).click()
    portal.locator("#aa-a").fill("Segundo borrador")
    held[0].fulfill(json={"data": results["guardar"], "meta": {}})
    portal.wait_for_load_state("networkidle")
    expect(portal.locator("#aa-a")).to_have_value("Segundo borrador")
