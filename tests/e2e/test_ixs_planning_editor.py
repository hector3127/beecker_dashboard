"""Editores de Planeación: presentación anterior, API y respuestas tardías."""

from urllib.parse import quote

import pytest
from playwright.sync_api import expect

from tests.e2e.test_aer_executive import fixed_day as fixed_day
from tests.e2e.test_ixs_executive import ixs as ixs
from tests.e2e.test_ixs_planning_transport import open_planning
from tests.e2e.test_ixs_planning_transport import planning as planning
from tests.e2e.test_project_detail_entry import project_detail as project_detail

pytestmark = pytest.mark.django_db(transaction=True)


def open_editor(portal, kind="vacacion", uid="", initial=""):
    portal.evaluate(
        "args => ixsAbrirPlanEditor(...args)",
        [kind, quote(uid, safe=""), initial],
    )
    return portal.locator("#ixs-plan-form")


def fields(portal):
    return portal.locator(
        "#ixs-plan-form"
    ).evaluate("""form => [...form.elements]
      .filter(x=>x.name).map(x=>({name:x.name,value:x.value,type:x.type,
        required:x.required,options:x.options?[...x.options].map(o=>o.value):null}))""")


@pytest.mark.parametrize(
    "kind,uid", [("vacacion", "vac/'1"), ("compromiso", "hito/'1")]
)
def test_edit_and_delete_keep_exact_uid(portal, planning, fixed_day, kind, uid):
    _, _, calls, _ = planning
    open_planning(portal)
    form = open_editor(portal, kind, uid)
    form.locator('[name="estado"]').select_option(
        "Cancelada" if kind == "vacacion" else "Detenido"
    )
    form.get_by_role("button", name="Guardar", exact=True).click()
    expect(portal.locator("#ixs-plan-modal")).to_have_count(0)
    assert calls[0][2]["uid"] == uid
    form = open_editor(portal, kind, uid)
    portal.once("dialog", lambda dialog: dialog.dismiss())
    form.get_by_role("button", name="Eliminar", exact=True).click()
    assert len(calls) == 1
    portal.once("dialog", lambda dialog: dialog.accept())
    form.get_by_role("button", name="Eliminar", exact=True).click()
    expect(portal.locator("#ixs-plan-modal")).to_have_count(0)
    assert calls[1] == ("delete", kind, "AMK.008", uid)


@pytest.mark.parametrize("mode", ["source", "transport", "permission"])
def test_delete_failure_preserves_editor_for_retry(
    portal, planning, fixed_day, mode
):
    open_planning(portal)
    form = open_editor(portal, "vacacion", "vac/'1")
    pattern = "**/planeacion/vacacion/eliminar/"

    def fail(route):
        if mode == "transport":
            route.abort()
        elif mode == "permission":
            route.fulfill(
                status=403,
                json={
                    "error": {
                        "code": "forbidden",
                        "message": "Sin permiso de edición.",
                    }
                },
            )
        else:
            route.fulfill(
                json={
                    "data": {"ok": False, "error": "No se pudo eliminar."},
                    "meta": {},
                }
            )

    portal.route(pattern, fail)
    portal.on("dialog", lambda dialog: dialog.accept())
    form.get_by_role("button", name="Eliminar", exact=True).click()
    expect(portal.locator("#ixs-plan-error")).not_to_be_empty()
    expect(form.locator('[name="recurso"]')).to_have_value("Ana Pérez")
    expect(
        form.get_by_role("button", name="Eliminar", exact=True)
    ).to_be_enabled()
    portal.unroute(pattern, fail)
    form.get_by_role("button", name="Eliminar", exact=True).click()
    expect(portal.locator("#ixs-plan-modal")).to_have_count(0)


@pytest.mark.parametrize("result", ["success", "failure"])
def test_double_submit_and_late_response_do_not_replace_reopened_editor(
    portal, planning, fixed_day, result
):
    open_planning(portal)
    form = open_editor(portal, "vacacion", "vac/'1")
    held = []

    def hold(route):
        held.append(route)

    portal.route("**/planeacion/vacacion/guardar/", hold)
    with portal.expect_request("**/planeacion/vacacion/guardar/"):
        form.get_by_role("button", name="Guardar", exact=True).click()
    expect(
        form.get_by_role("button", name="Guardando…", exact=True)
    ).to_be_disabled()
    form.dispatch_event("submit")
    assert len(held) == 1
    form.get_by_role("button", name="Cancelar", exact=True).click()
    form = open_editor(portal, "compromiso", "", "Hito")
    form.locator('[name="actividad"]').fill("Editor nuevo")
    held[0].fulfill(
        json={
            "data": {
                "ok": result == "success",
                "error": "Respuesta anterior",
                "vacaciones": [],
                "compromisos": [],
            },
            "meta": {},
        }
    )
    portal.wait_for_load_state("networkidle")
    expect(form.locator('[name="actividad"]')).to_have_value("Editor nuevo")
    expect(portal.locator("#ixs-plan-error")).to_be_empty()
    expect(
        form.get_by_role("button", name="Guardar", exact=True)
    ).to_be_enabled()
    expect(portal.locator("#ixs-plan-vacaciones")).to_contain_text("Ana Pérez")


def test_text_is_safe_and_cancel_does_not_modify_source(
    portal, planning, fixed_day
):
    plan, _, calls, _ = planning
    text = '<img src=x onerror="window.planInjected=true">'
    plan["vacaciones"].append(
        {**plan["vacaciones"][0], "uid": "unsafe", "recurso": text}
    )
    open_planning(portal)
    form = open_editor(portal, "vacacion", "unsafe")
    expect(form.locator('[name="recurso"]')).to_have_value(text)
    assert portal.locator("#ixs-plan-modal img").count() == 0
    assert portal.evaluate("window.planInjected") is None
    form.locator('[name="recurso"]').fill("Cambio cancelado")
    form.get_by_role("button", name="Cancelar", exact=True).click()
    assert plan["vacaciones"][-1]["recurso"] == text
    assert calls == []
    open_editor(portal)
    portal.locator("#ixs-plan-modal").click(position={"x": 2, "y": 2})
    expect(portal.locator("#ixs-plan-modal")).to_have_count(0)
