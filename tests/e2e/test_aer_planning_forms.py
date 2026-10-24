"""Formularios modulares de Planeación: paridad, capacidad y datos seguros."""

from pathlib import Path

import pytest
from playwright.sync_api import expect

from tests.e2e.test_aer_planning_transport import enter
from tests.e2e.test_aer_planning_transport import fixed_day as fixed_day
from tests.e2e.test_aer_planning_transport import planning as planning
from tests.e2e.test_aer_planning_transport import (
    project_detail as project_detail,
)
from tests.e2e.test_ixs_effort import state

pytestmark = pytest.mark.django_db(transaction=True)


@pytest.mark.parametrize("width", [1450, 900, 390])
@pytest.mark.parametrize(
    "variant", ["overloaded", "full", "inactive", "vacation-edit"]
)
def test_editor_variants_match_previous(
    portal, planning, fixed_day, width, variant
):
    data, _, _ = planning
    data["vacaciones"]["filas"] = [
        {
            "uid": "v1",
            "recurso": "Ana",
            "inicio": "2026-10-26",
            "fin": "2026-10-30",
            "estado": "Pendiente",
            "registradoPor": "Beto",
            "comentarios": "Revisar",
        }
    ]
    if variant == "overloaded":
        data["plan"]["filas"].append(
            {
                "uid": "other",
                "responsable": "Ana",
                "esfuerzo": 6,
                "tipo": "Actividad",
                "estado": "En progreso",
                "inicioPlan": "2026-09-01",
                "finPlan": "2026-10-30",
            }
        )
    portal.set_viewport_size({"width": width, "height": 1000})
    directory = (
        Path("tmp/migration/project_detail/aer_planning_forms")
        / variant
        / str(width)
    )
    directory.mkdir(parents=True, exist_ok=True)
    states = []
    for previous in [True, False]:
        enter(portal, previous)
        portal.evaluate(
            "aerAbrirVacacion('v1')"
            if variant == "vacation-edit"
            else "aerAbrirPlan('p2')"
        )
        if variant == "full":
            portal.locator("#ap-ord").select_option("6")
        if variant == "inactive":
            portal.locator("#ap-est").select_option("Completado")
        portal.mouse.move(0, 0)
        states.append(
            (
                state(portal, "#aer-modal-back, #aer-modal-back *"),
                portal.locator("#aer-modal-back").evaluate(
                    "root=>[...root.querySelectorAll('input,textarea,select')].map(e=>({id:e.id,value:e.value,disabled:e.disabled}))"
                ),
            )
        )
        portal.screenshot(
            path=str(directory / ("old.png" if previous else "new.png")),
            full_page=True,
        )
    assert states[0] == states[1]
    assert (
        portal.locator(
            "#aer-modal-back [onclick], #aer-modal-back [onchange]"
        ).count()
        == 0
    )


def test_forms_and_model_do_not_call_old_helpers(portal, planning, fixed_day):
    enter(portal)
    portal.evaluate("""() => {
      const fail=()=>{throw Error('Old form/model helper called');};
      _aerModal=_aerActualizarAdvertenciaCapacidadModal=_aerMaxCapacidadEnRango=fail;
      _aerRecursosProyecto=_aerParsePlanText=_aerNormalizarFechaImport=fail;
    }""")
    portal.get_by_role("button", name="+ Actividad / Hito", exact=True).click()
    expect(portal.locator("#ap-cap-warning")).to_contain_text(
        "no consume capacidad activa"
    )
    portal.locator("#ap-resp").fill("Ana")
    portal.locator("#ap-ord").select_option("6")
    expect(portal.locator("#ap-cap-warning")).to_contain_text("Sobreasignación")
    portal.locator("#ap-dep").fill("Cliente")
    expect(portal.locator("#ap-dep-est")).to_be_enabled()
    expect(portal.locator("#ap-dep-est")).to_have_value("Abierta")
    portal.locator("#ap-est").select_option("Completado")
    expect(portal.locator("#ap-fr")).to_have_value("2026-10-23")
    portal.locator("#ap-est").select_option("En progreso")
    expect(portal.locator("#ap-fr")).to_have_value("")
    expect(portal.locator("#ap-fr")).to_be_disabled()
    portal.locator("#aer-modal-back").get_by_role(
        "button", name="✕", exact=True
    ).click()
    portal.get_by_role(
        "button", name="+ Registrar vacaciones", exact=True
    ).click()
    expect(portal.locator("#av-rec")).to_be_visible()
    portal.locator("#aer-modal-back").get_by_role(
        "button", name="✕", exact=True
    ).click()
    portal.get_by_role("button", name="⇧ Cargar CSV", exact=True).click()
    portal.locator("#aer-plan-text").fill("Tipo\tActividad\nHito\tEntrega")
    expect(portal.locator("#aer-plan-import-status")).to_have_text(
        "Listo: 1 actividad(es) detectada(s)."
    )


def test_file_import_preview_and_keyboard_use(portal, planning, fixed_day):
    enter(portal)
    portal.evaluate("aerAbrirImportPlan()")
    portal.locator("#aer-plan-file").set_input_files(
        {
            "name": "plan.tsv",
            "mimeType": "text/tab-separated-values",
            "buffer": b"Tipo\tActividad\nHito\tEntrega",
        }
    )
    expect(portal.locator("#aer-plan-text")).to_have_value(
        "Tipo\tActividad\nHito\tEntrega"
    )
    expect(portal.locator("#aer-plan-import-status")).to_have_text(
        "Listo: 1 actividad(es) detectada(s)."
    )
    portal.locator("#aer-modal-back").get_by_role(
        "button", name="✕", exact=True
    ).click()
    portal.evaluate("aerAbrirPlan()")
    portal.get_by_label("Responsable", exact=True).fill("Ana")
    portal.get_by_label("Responsable", exact=True).press("Tab")
    expect(portal.locator("#ap-act")).to_be_focused()


def test_untrusted_values_stay_text(portal, planning, fixed_day):
    enter(portal)
    unsafe = '<img src=x onerror="window.injected=true">'
    portal.evaluate(
        """unsafe=>{
      const row=aerDashboardData.plan.filas.find(r=>r.uid==='p2');
      row.uid="p'2";row.actividad=row.responsable=row.dependencia=row.notas=unsafe;
    }""",
        unsafe,
    )
    portal.evaluate('aerAbrirPlan("p\'2")')
    expect(portal.locator("#ap-act")).to_have_value(unsafe)
    portal.locator("#ap-ord").select_option("6")
    expect(portal.locator("#ap-cap-warning")).to_contain_text(unsafe)
    assert portal.locator("#aer-modal-back img").count() == 0
    assert portal.evaluate("window.injected||false") is False
