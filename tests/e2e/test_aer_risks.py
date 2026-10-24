"""Riesgos AER: paridad visual, CRUD, acciones reutilizadas y texto seguro."""

import copy
from pathlib import Path

import pytest
from playwright.sync_api import expect

from tests.e2e.test_aer_executive import fixed_day as fixed_day
from tests.e2e.test_ixs_effort import state
from tests.e2e.test_project_detail_entry import project_detail as project_detail

pytestmark = pytest.mark.django_db(transaction=True)
PAGE = "/proyectos/AER.001/"


@pytest.fixture
def risks(portal, project_detail):
    _, data = project_detail
    responses = {
        op: {"ok": True, "riesgos": copy.deepcopy(data["riesgos"])}
        for op in ["leer", "guardar", "eliminar", "limpiar-duplicados"]
    }
    responses["limpiar-duplicados"]["eliminados"] = 1
    calls = []

    def dispatch(route):
        op = route.request.url.split("/riesgos-aer/", 1)[1].strip("/") or "leer"
        calls.append(
            (
                op,
                route.request.post_data_json
                if route.request.method == "POST"
                else None,
            )
        )
        route.fulfill(json={"data": responses[op], "meta": {}})

    portal.route("**/riesgos-aer/**", dispatch)
    return data, responses, calls


def enter(page, previous=False):
    page.goto(page.base + PAGE + ("?vista=anterior" if previous else ""))
    page.locator(".aer-tabs").get_by_role(
        "button", name="Riesgos", exact=True
    ).click()
    expect(page.locator(".aer-risk-kpis")).to_be_visible()


@pytest.mark.parametrize("width", [1450, 900, 390])
@pytest.mark.parametrize("variant", ["full", "empty", "duplicates"])
def test_view_matches_previous(portal, risks, fixed_day, width, variant):
    data, _, _ = risks
    if variant == "empty":
        data["riesgos"] = {}
        data["acciones"] = {}
        data["kpis"] = {}
        data["alertas"] = []
    elif variant == "duplicates":
        first = data["riesgos"]["activos"][0]
        data["riesgos"]["activos"].extend(
            [
                {**first, "uid": "duplicate", "notas": "Información adicional"},
                {
                    **first,
                    "uid": "different",
                    "responsable": "Otra persona",
                    "fechaLimite": "2026-11-01",
                },
                {
                    "uid": "low",
                    "riesgo": "Bajo",
                    "impacto": "Bajo",
                    "probabilidad": "Baja",
                    "estado": "En mitigación",
                },
                {"uid": "closed", "riesgo": "Cerrado", "estado": "Cerrado"},
            ]
        )
    portal.set_viewport_size({"width": width, "height": 1000})
    directory = (
        Path("tmp/migration/project_detail/aer_risks") / variant / str(width)
    )
    directory.mkdir(parents=True, exist_ok=True)
    states = []
    for previous in [True, False]:
        enter(portal, previous)
        portal.mouse.move(0, 0)
        states.append(state(portal, ".aer-vivid-grid, .aer-vivid-grid *"))
        portal.screenshot(
            path=str(directory / ("old.png" if previous else "new.png")),
            full_page=True,
        )
    assert states[0] == states[1]
    assert portal.locator(".aer-vivid-grid [onclick]").count() == 0


@pytest.mark.parametrize("width", [1450, 900, 390])
@pytest.mark.parametrize("uid", ["", "r1", "r4"])
def test_editor_matches_previous(portal, risks, fixed_day, width, uid):
    portal.set_viewport_size({"width": width, "height": 1000})
    directory = (
        Path("tmp/migration/project_detail/aer_risks/editor")
        / (uid or "new")
        / str(width)
    )
    directory.mkdir(parents=True, exist_ok=True)
    states = []
    for previous in [True, False]:
        enter(portal, previous)
        portal.evaluate("uid=>aerAbrirRiesgo(uid)", uid)
        portal.mouse.move(0, 0)
        states.append(
            (
                state(portal, "#aer-modal-back, #aer-modal-back *"),
                portal.locator("#aer-modal-back").evaluate(
                    "root=>[...root.querySelectorAll('input,textarea,select')].map(e=>({id:e.id,value:e.value}))"
                ),
            )
        )
        portal.screenshot(
            path=str(directory / ("old.png" if previous else "new.png")),
            full_page=True,
        )
    assert states[0] == states[1]
    assert portal.locator("#aer-modal-back [onclick]").count() == 0


def test_save_retry_and_delete_reload_use_api(portal, risks, fixed_day):
    _, responses, calls = risks
    requests = []
    portal.on("request", lambda request: requests.append(request.url))
    enter(portal)
    portal.get_by_role("button", name="Ver detalle →", exact=True).first.click()
    portal.locator("#ar-r").fill("Riesgo actualizado")
    responses["guardar"] = {"ok": False, "error": "Fallo simulado"}
    save = portal.locator("#aer-modal-back").get_by_role(
        "button", name="Guardar", exact=True
    )
    save.click()
    expect(portal.locator(".aer-toast")).to_contain_text("Fallo simulado")
    expect(portal.locator("#ar-r")).to_have_value("Riesgo actualizado")
    responses["guardar"] = {"ok": True, "riesgos": risks[0]["riesgos"]}
    save.click()
    expect(portal.locator("#aer-modal-back")).to_have_count(0)
    assert calls[-1] == (
        "guardar",
        {
            "UID": "r1",
            "ID_Proyecto": "AER.001",
            "Riesgo": "Riesgo actualizado",
            "Impacto": "Alto",
            "Probabilidad": "Media",
            "Responsable": "Ana",
            "Fecha_Limite": "2026-10-10",
            "Estado": "Abierto",
            "Accion": "Escalar",
            "Notas": "",
        },
    )
    portal.get_by_role("button", name="Ver detalle →", exact=True).first.click()
    portal.once("dialog", lambda dialog: dialog.dismiss())
    portal.locator("#aer-modal-back").get_by_role(
        "button", name="Eliminar", exact=True
    ).click()
    assert not any(op == "eliminar" for op, _ in calls)
    portal.once("dialog", lambda dialog: dialog.accept())
    with portal.expect_response(
        lambda response: response.url.endswith("/riesgos-aer/")
    ):
        portal.locator("#aer-modal-back").get_by_role(
            "button", name="Eliminar", exact=True
        ).click()
    expect(portal.locator("#aer-modal-back")).to_have_count(0)
    assert [op for op, _ in calls][-2:] == ["eliminar", "leer"]
    assert not any("/api/rpc/" in url for url in requests)


def test_cleanup_preserves_counts_and_no_new_button(portal, risks, fixed_day):
    enter(portal)
    assert (
        portal.get_by_role(
            "button", name="Limpiar duplicados", exact=False
        ).count()
        == 0
    )
    portal.once("dialog", lambda dialog: dialog.accept())
    with portal.expect_response(
        lambda response: response.url.endswith("/limpiar-duplicados/")
    ):
        portal.evaluate("aerLimpiarDuplicadosRiesgos()")
    assert risks[2][-1] == ("limpiar-duplicados", {})


def test_shared_action_editor_uses_existing_api(portal, risks, fixed_day):
    held = []

    def save(route):
        held.append(route.request.post_data_json)
        route.fulfill(
            json={
                "data": {"ok": True, "acciones": risks[0]["acciones"]},
                "meta": {},
            }
        )

    portal.route("**/acciones/guardar/", save)
    enter(portal)
    portal.get_by_role("button", name="+ Nueva acción", exact=True).click()
    portal.locator("#aa-a").fill("Mitigar riesgo")
    portal.locator("#aer-modal-back").get_by_role(
        "button", name="Guardar", exact=True
    ).click()
    expect(portal.locator("#aer-modal-back")).to_have_count(0)
    assert held[-1]["Accion"] == "Mitigar riesgo"
    assert held[-1]["servicio"] == "aer"


def test_no_previous_renderer_and_safe_source(portal, risks, fixed_day):
    enter(portal)
    unsafe = '<img src=x onerror="window.injected=true">'
    portal.evaluate(
        """unsafe=>{
      const fail=()=>{throw Error('Old renderer called');};
      _aerVistaRiesgos=_aerTablaAcciones=_aerDedupRiesgosVista=_aerModal=fail;
      aerDashboardData.riesgos.activos[0].riesgo=unsafe;
      aerDashboardData.riesgos.filas[0].riesgo=unsafe;
      _aerRenderTab();
    }""",
        unsafe,
    )
    expect(portal.locator(".aer-risk-item-title b").first).to_have_text(unsafe)
    portal.get_by_role("button", name="Ver detalle →", exact=True).first.click()
    expect(portal.locator("#ar-r")).to_have_value(unsafe)
    assert (
        portal.locator(".aer-vivid-grid img, #aer-modal-back img").count() == 0
    )
    assert portal.evaluate("window.injected||false") is False
    portal.locator("#aer-modal-back").get_by_role(
        "button", name="✕", exact=True
    ).press("Enter")
    expect(portal.locator("#aer-modal-back")).to_have_count(0)


def test_late_save_keeps_new_editor_and_ignores_other_dashboard(
    portal, risks, fixed_day
):
    held = []
    portal.route("**/riesgos-aer/guardar/", lambda route: held.append(route))
    enter(portal)
    portal.get_by_role("button", name="+ Riesgo", exact=True).click()
    portal.locator("#ar-r").fill("Primero")
    with portal.expect_request(
        lambda request: request.url.endswith("/riesgos-aer/guardar/")
    ):
        portal.locator("#aer-modal-back").get_by_role(
            "button", name="Guardar", exact=True
        ).click()
    portal.evaluate("aerCerrarModal();aerAbrirRiesgo()")
    portal.locator("#ar-r").fill("Segundo")
    held[0].fulfill(json={"data": risks[1]["guardar"], "meta": {}})
    portal.wait_for_load_state("networkidle")
    expect(portal.locator("#ar-r")).to_have_value("Segundo")
    with portal.expect_request(
        lambda request: request.url.endswith("/riesgos-aer/guardar/")
    ):
        portal.locator("#aer-modal-back").get_by_role(
            "button", name="Guardar", exact=True
        ).click()
    portal.evaluate(
        "() => {aerDashboardData={...aerDashboardData,"
        "riesgos:{sentinel:true}};}"
    )
    held[1].fulfill(json={"data": risks[1]["guardar"], "meta": {}})
    portal.wait_for_load_state("networkidle")
    assert portal.evaluate("aerDashboardData.riesgos.sentinel") is True
