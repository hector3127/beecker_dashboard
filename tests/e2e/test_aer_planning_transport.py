"""Planeación AER: transporte API conservando vista, formularios y reglas."""

import copy

import pytest
from playwright.sync_api import expect

from tests.e2e.test_aer_executive import fixed_day as fixed_day
from tests.e2e.test_project_detail_entry import project_detail as project_detail

pytestmark = pytest.mark.django_db(transaction=True)
PAGE = "/proyectos/AER.001/"


@pytest.fixture
def planning(portal, project_detail):
    _, data = project_detail
    results = {
        key: {
            "ok": True,
            "plan": copy.deepcopy(data["plan"]),
            "vacaciones": copy.deepcopy(data["vacaciones"]),
        }
        for key in [
            "guardar",
            "importar",
            "estado",
            "cerrar",
            "eliminar",
            "eliminar-lote",
            "vacacion-guardar",
            "vacacion-eliminar",
        ]
    }
    calls = []

    def write(route):
        op = route.request.url.rstrip("/").rsplit("/", 1)[-1]
        calls.append((op, route.request.post_data_json))
        route.fulfill(json={"data": results[op], "meta": {}})

    portal.route("**/planeacion-aer/*/", write)
    return data, results, calls


def enter(page):
    page.goto(page.base + PAGE)
    # El botón Comunicados ya existía en esta tarjeta antes de este bloque.
    page.evaluate("window.beeProjectCommunique ||= {}")
    page.locator(".aer-tabs").get_by_role(
        "button", name="Planeación", exact=True
    ).click()
    expect(page.locator(".aer-plan-dashboard")).to_be_visible()


def test_plan_save_retry_preserves_fields_and_capacity_rule(
    portal, planning, fixed_day
):
    _, results, calls = planning
    planning[0]["plan"]["filas"].append(
        {
            "uid": "extra",
            "actividad": "Otra tarea",
            "responsable": "Ana",
            "tipo": "Actividad",
            "estado": "En progreso",
            "esfuerzo": 1,
            "inicioPlan": "2026-09-01",
            "finPlan": "2026-10-30",
        }
    )
    enter(portal)
    portal.evaluate("aerAbrirPlan('p2')")
    portal.locator("#ap-act").fill("Desarrollo actualizado")
    results["guardar"] = {"ok": False, "error": "Fallo simulado"}
    save = portal.locator("#aer-modal-back").get_by_role(
        "button", name="Guardar cambios", exact=True
    )
    save.click()
    expect(portal.locator(".aer-toast")).to_contain_text("Fallo simulado")
    expect(portal.locator("#ap-act")).to_have_value("Desarrollo actualizado")
    results["guardar"] = {"ok": True, "plan": planning[0]["plan"]}
    portal.locator("#ap-ord").select_option("6")
    portal.once("dialog", lambda dialog: dialog.dismiss())
    save.click()
    assert len(calls) == 1
    portal.once("dialog", lambda dialog: dialog.accept())
    save.click()
    expect(portal.locator("#aer-modal-back")).to_have_count(0)
    assert calls[-1] == (
        "guardar",
        {
            "UID": "p2",
            "ID_Proyecto": "AER.001",
            "Tipo": "Actividad",
            "Actividad": "Desarrollo actualizado",
            "Responsable": "Ana",
            "Inicio_Plan": "2026-09-01",
            "Fin_Plan": "2026-10-15",
            "Fin_Real": "",
            "Estado": "En progreso",
            "Dependencia": "Accesos",
            "Estado_Dependencia": "Abierta",
            "Orden": "6",
            "Notas": "",
        },
    )


def test_inline_and_checkbox_closures_use_api(portal, planning, fixed_day):
    _, _, calls = planning
    requests = []
    portal.on("request", lambda req: requests.append(req.url))
    enter(portal)
    portal.locator("#apt-est-p2").select_option("Completado")
    expect(portal.locator("#apt-est-p2")).to_be_enabled()
    assert calls[-1] == (
        "estado",
        {"uid": "p2", "estado": "Completado", "cierre": "2026-10-23"},
    )
    with portal.expect_response(lambda r: r.url.endswith("/cerrar/")):
        portal.locator(".aer-commit-check").nth(2).check()
    assert calls[-1][0] == "cerrar"
    assert calls[-1][1]["cerrado"] is True
    assert not any("/api/rpc/" in url for url in requests)


def test_vacation_save_and_delete(portal, planning, fixed_day):
    _, _, calls = planning
    enter(portal)
    portal.evaluate("aerAbrirVacacion()")
    portal.locator("#av-ini").fill("2026-10-26")
    portal.locator("#av-fin").fill("2026-10-30")
    portal.locator("#av-reg").fill("Ana")
    portal.locator("#aer-modal-back").get_by_role(
        "button", name="Guardar", exact=True
    ).click()
    expect(portal.locator("#aer-modal-back")).to_have_count(0)
    assert calls[-1][0] == "vacacion-guardar"
    assert calls[-1][1]["Inicio"] == "2026-10-26"
    assert calls[-1][1]["Registrado_Por"] == "Ana"
    portal.once("dialog", lambda dialog: dialog.dismiss())
    portal.evaluate("aerEliminarVacacion('v1')")
    assert len(calls) == 1
    portal.once("dialog", lambda dialog: dialog.accept())
    with portal.expect_response(
        lambda r: r.url.endswith("/vacacion-eliminar/")
    ):
        portal.evaluate("aerEliminarVacacion('v1')")
    assert calls[-1] == ("vacacion-eliminar", {"uid": "v1"})


def test_import_and_batch_wait_for_confirmation(portal, planning, fixed_day):
    _, results, calls = planning
    enter(portal)
    portal.evaluate(
        "() => {window.reloads=0; beeAerRuntime.refresh=()=>window.reloads++;}"
    )
    portal.evaluate("aerAbrirImportPlan()")
    portal.locator("#aer-plan-text").fill(
        "Tipo\tActividad\tResponsable\tInicio_Plan\tFin_Plan\nActividad\tRevisión\tAna\t01/10/2026\t23/10/2026"
    )
    results["importar"] = {"ok": False, "error": "Reintentar"}
    portal.locator("#aer-plan-import-btn").click()
    expect(portal.locator("#aer-plan-import-status")).to_contain_text(
        "Error: Reintentar"
    )
    results["importar"] = {"ok": True, "guardados": 1, "nuevos": 1}
    portal.locator("#aer-plan-import-btn").click()
    expect(portal.locator("#aer-plan-import-status")).to_contain_text(
        "Importación completa: 1 guardado(s) · 1 nuevo(s)."
    )
    expect(portal.locator("#aer-modal-back")).to_have_count(0)
    assert portal.evaluate("window.reloads") == 1
    assert calls[-1][1]["items"][0]["Inicio_Plan"] == "2026-10-01"
    portal.locator(".aer-plan-row-check").first.check()
    results["eliminar-lote"] = {
        "ok": True,
        "eliminados": 1,
        "eliminadosFisicos": 0,
    }
    portal.on("dialog", lambda dialog: dialog.accept())
    portal.evaluate("aerEliminarPlanesSeleccionados()")
    expect(portal.locator("#aer-plan-delete-selected")).to_be_enabled()
    assert portal.evaluate("window.reloads") == 1
    results["eliminar-lote"] = {"ok": True, "eliminadosFisicos": 1}
    with portal.expect_response(lambda r: r.url.endswith("/eliminar-lote/")):
        portal.evaluate("aerEliminarPlanesSeleccionados()")
    portal.wait_for_function("window.reloads===2")


def test_late_save_cannot_close_new_modal(portal, planning, fixed_day):
    held = []
    portal.route("**/planeacion-aer/guardar/", lambda route: held.append(route))
    enter(portal)
    portal.evaluate("aerAbrirPlan('p2')")
    with portal.expect_request(
        lambda r: r.url.endswith("/planeacion-aer/guardar/")
    ):
        portal.locator("#aer-modal-back").get_by_role(
            "button", name="Guardar cambios", exact=True
        ).click()
    portal.evaluate("aerCerrarModal(); aerAbrirVacacion()")
    portal.locator("#av-reg").fill("Segundo borrador")
    held[0].fulfill(json={"data": planning[1]["guardar"], "meta": {}})
    portal.wait_for_load_state("networkidle")
    expect(portal.locator("#av-reg")).to_have_value("Segundo borrador")


def test_modal_state_and_single_delete_keep_original_reload(
    portal, planning, fixed_day
):
    _, results, calls = planning
    enter(portal)
    portal.evaluate("aerAbrirPlan('p2')")
    portal.locator("#ap-est").select_option("Completado")
    with portal.expect_response(lambda r: r.url.endswith("/estado/")):
        portal.evaluate("aerGuardarEstadoModal('p2')")
    expect(portal.locator("#aer-modal-back")).to_have_count(0)
    assert calls[-1] == (
        "estado",
        {"uid": "p2", "estado": "Completado", "cierre": "2026-10-23"},
    )
    portal.evaluate(
        "() => {window.reloads=0; beeAerRuntime.refresh=()=>window.reloads++;}"
    )
    portal.evaluate("aerAbrirPlan('p2')")
    results["eliminar"] = {"ok": False}
    portal.once("dialog", lambda dialog: dialog.accept())
    portal.locator("#aer-modal-back").get_by_role(
        "button", name="Eliminar", exact=True
    ).click()
    expect(portal.locator("#aer-modal-back")).to_have_count(0)
    assert calls[-1] == ("eliminar", {"uid": "p2"})
    assert portal.evaluate("window.reloads") == 1


def test_response_from_previous_dashboard_is_ignored(
    portal, planning, fixed_day
):
    held = []
    portal.route(
        "**/planeacion-aer/vacacion-guardar/", lambda route: held.append(route)
    )
    enter(portal)
    portal.evaluate("aerAbrirVacacion()")
    with portal.expect_request(lambda r: r.url.endswith("/vacacion-guardar/")):
        portal.locator("#aer-modal-back").get_by_role(
            "button", name="Guardar", exact=True
        ).click()
    portal.evaluate(
        "() => {aerDashboardData={...aerDashboardData,"
        "vacaciones:{filas:[],sentinel:true}};}"
    )
    held[0].fulfill(json={"data": planning[1]["vacacion-guardar"], "meta": {}})
    portal.wait_for_load_state("networkidle")
    assert portal.evaluate("aerDashboardData.vacaciones.sentinel") is True
    expect(portal.locator("#aer-modal-back")).to_have_count(1)
