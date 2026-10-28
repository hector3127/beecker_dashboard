"""Evaluaciones AER: diseño actual, selección, API y formularios seguros."""

import json
from pathlib import Path

import pytest
from playwright.sync_api import expect

from tests.e2e.frozen.aer_executive_support import (
    production_site as production_site,
)
from tests.e2e.frozen.aer_resources_support import (
    enter,
    input_digest,
    measure_editor,
    measure_view,
    prepare,
)
from tests.e2e.test_aer_executive import fixed_day as fixed_day
from tests.e2e.test_project_detail_entry import project_detail as project_detail

pytestmark = [
    pytest.mark.django_db(transaction=True),
    pytest.mark.usefixtures("production_site", "enforced_csp"),
]


@pytest.fixture
def resources(portal, project_detail):
    _, data = project_detail
    rows = [
        {
            "uid": f"e{i}",
            "recurso": "Ana" if i % 2 else "Beto",
            "evaluador": "DM",
            "fechaEvaluacion": f"2026-10-{i + 1:02}",
            "proximaEvaluacion": "2026-11-01",
            "score": 60 + i * 5,
            "calidad": 95,
            "cumplimiento": 80,
            "comunicacion": 70,
            "colaboracion": 90,
            "autonomia": 60,
            "comentario": f"Comentario {i}",
            "planAccion": "Seguimiento",
            "periodo": "Octubre",
        }
        for i in range(7)
    ]
    data["evaluaciones"] = {"filas": rows}
    responses = {
        op: {"ok": True, "evaluaciones": data["evaluaciones"]}
        for op in ["guardar", "eliminar"]
    }
    calls = []

    def dispatch(route):
        op = route.request.url.split("/evaluaciones-aer/")[1].strip("/")
        calls.append((op, route.request.post_data_json))
        route.fulfill(json={"data": responses[op], "meta": {}})

    portal.route("**/evaluaciones-aer/**", dispatch)
    return data, responses, calls


def approved(name, width, data):
    reference = json.loads(
        Path(f"tests/e2e/frozen/aer_resources/{name}-{width}.json").read_text(
            encoding="utf-8"
        )
    )
    assert reference["source"] == "project_redesign_delivery_v2"
    assert reference["viewport"] == {"width": width, "height": 1000}
    assert reference["input_sha256"] == input_digest(data)
    return reference["state"]


@pytest.mark.parametrize("width", [1450, 900, 390])
@pytest.mark.parametrize("variant", ["full", "empty", "selected"])
def test_view_keeps_current_design(
    portal, resources, fixed_day, width, variant
):
    data, _, _ = resources
    prepare(data, variant)
    portal.set_viewport_size({"width": width, "height": 1000})
    expected = approved(f"view-{variant}", width, data)
    actual = measure_view(portal, variant)
    assert actual == expected
    assert (
        portal.locator(
            ".aer-vivid-grid [onchange], .aer-vivid-grid [onclick]"
        ).count()
        == 0
    )


@pytest.mark.parametrize("width", [1450, 900, 390])
@pytest.mark.parametrize("uid", ["", "e1"])
def test_editor_keeps_current_design(portal, resources, fixed_day, width, uid):
    portal.set_viewport_size({"width": width, "height": 1000})
    expected = approved(f"editor-{uid or 'new'}", width, resources[0])
    actual = measure_editor(portal, uid)
    assert actual == expected
    assert portal.locator("#aer-modal-back [onclick]").count() == 0


def test_save_retry_delete_and_selection(portal, resources, fixed_day):
    _, responses, calls = resources
    urls = []
    portal.on("request", lambda request: urls.append(request.url))
    enter(portal)
    portal.evaluate("aerAbrirEvaluacion('e1')")
    portal.locator("#ae-com").fill("Actualizado")
    portal.locator("#ae-rec").select_option("Beto")
    responses["guardar"] = {"ok": False, "error": "Fallo simulado"}
    save = portal.get_by_role("button", name="Guardar evaluación", exact=True)
    save.click()
    expect(portal.locator(".aer-toast")).to_contain_text("Fallo simulado")
    expect(portal.locator("#ae-com")).to_have_value("Actualizado")
    responses["guardar"] = {
        "ok": True,
        "evaluaciones": resources[0]["evaluaciones"],
    }
    save.click()
    expect(portal.locator("#aer-modal-back")).to_have_count(0)
    expect(portal.locator(".aer-eval-select")).to_have_value("Beto")
    assert calls[-1] == (
        "guardar",
        {
            "UID": "e1",
            "ID_Proyecto": "AER.001",
            "Recurso": "Beto",
            "Evaluador": "DM",
            "Fecha_Evaluacion": "2026-10-02",
            "Proxima_Evaluacion": "2026-11-01",
            "Calidad": "95",
            "Cumplimiento": "80",
            "Comunicacion": "70",
            "Colaboracion": "90",
            "Autonomia": "60",
            "Comentario": "Actualizado",
            "Plan_Accion": "Seguimiento",
        },
    )
    portal.evaluate("aerAbrirEvaluacion('e1')")
    portal.once("dialog", lambda d: d.dismiss())
    portal.get_by_role("button", name="Eliminar", exact=True).click()
    assert len(calls) == 2
    responses["eliminar"] = {"ok": True, "evaluaciones": {"filas": []}}
    portal.once("dialog", lambda d: d.accept())
    portal.get_by_role("button", name="Eliminar", exact=True).click()
    expect(portal.locator("#aer-modal-back")).to_have_count(0)
    expect(portal.locator(".aer-eval-history").last).to_contain_text(
        "Sin historial."
    )
    assert calls[-1] == ("eliminar", {"uid": "e1"})
    assert not any("/api/rpc/" in url for url in urls)


def test_safe_text_and_no_old_renderers(portal, resources, fixed_day):
    resources[0]["evaluaciones"]["filas"][0]["comentario"] = (
        '<img src=x onerror="alert(1)">'
    )
    enter(portal)
    portal.evaluate("""() => {
      const fail=()=>{throw Error('old renderer')};
      _aerVistaRecursos=_aerEvalCategoria=_aerEvalClase=_aerModal=fail;
      _aerRenderTab();aerAbrirEvaluacion('e0');
    }""")
    expect(portal.locator("#ae-com")).to_have_value(
        '<img src=x onerror="alert(1)">'
    )
    assert (
        portal.locator(".aer-vivid-grid img, #aer-modal-back img").count() == 0
    )
    portal.locator("#aer-modal-back").get_by_role("button", name="✕").click()
    portal.locator(".aer-eval-select").select_option("Beto")
    expect(portal.locator(".aer-eval-name b")).to_have_text("Beto")


def test_late_save_preserves_new_editor_and_project(
    portal, resources, fixed_day
):
    held = []
    portal.route(
        "**/evaluaciones-aer/guardar/", lambda route: held.append(route)
    )
    enter(portal)
    portal.evaluate("aerAbrirEvaluacion('e1')")
    with portal.expect_request("**/evaluaciones-aer/guardar/"):
        portal.get_by_role(
            "button", name="Guardar evaluación", exact=True
        ).click()
    portal.evaluate("aerAbrirEvaluacion('e2')")
    held[0].fulfill(json={"data": resources[1]["guardar"], "meta": {}})
    expect(portal.locator("#ae-fecha")).to_have_value("2026-10-03")
    with portal.expect_request("**/evaluaciones-aer/guardar/"):
        portal.get_by_role(
            "button", name="Guardar evaluación", exact=True
        ).click()
    portal.evaluate(
        "() => {aerDashboardData={...aerDashboardData,"
        "evaluaciones:{sentinel:true}};}"
    )
    held[1].fulfill(json={"data": resources[1]["guardar"], "meta": {}})
    portal.wait_for_timeout(150)
    assert portal.evaluate("aerDashboardData.evaluaciones") == {
        "sentinel": True
    }
    expect(portal.locator("#ae-fecha")).to_have_value("2026-10-03")
