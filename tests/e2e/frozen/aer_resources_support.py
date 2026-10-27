"""Current approved AER Resources inputs and read-only browser measurements."""

from playwright.sync_api import expect

from tests.e2e.frozen.aer_executive_support import input_digest
from tests.e2e.test_ixs_effort import state

PAGE = "/proyectos/AER.001/"


def prepare(data, variant):
    if variant == "empty":
        data.update(
            {
                "evaluaciones": {},
                "detalleRecursos": [],
                "plan": {},
                "vacaciones": {},
            }
        )


def enter(page):
    page.goto(page.base + PAGE)
    page.locator(".aer-tabs").get_by_role(
        "button", name="Recursos", exact=True
    ).click()
    expect(page.locator(".aer-eval-kpis")).to_be_visible()
    page.evaluate("document.fonts.ready")


def measure_view(page, variant):
    enter(page)
    if variant == "selected":
        page.locator(".aer-eval-select").select_option("Beto")
    page.mouse.move(0, 0)
    return state(page, ".aer-vivid-grid, .aer-vivid-grid *")


def measure_editor(page, uid):
    enter(page)
    page.evaluate("uid=>aerAbrirEvaluacion(uid)", uid)
    page.mouse.move(0, 0)
    return {
        "elements": state(page, "#aer-modal-back, #aer-modal-back *"),
        "values": page.locator("#aer-modal-back").evaluate(
            "r=>[...r.querySelectorAll('input,select,textarea')].map(x=>[x.id,x.value])"
        ),
    }


__all__ = ["enter", "prepare", "measure_view", "measure_editor", "input_digest"]
