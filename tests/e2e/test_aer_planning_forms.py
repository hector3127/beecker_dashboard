"""Formularios modulares de Planeación: paridad, capacidad y datos seguros."""

import pytest
from playwright.sync_api import expect

from tests.e2e.test_aer_planning_transport import enter
from tests.e2e.test_aer_planning_transport import fixed_day as fixed_day
from tests.e2e.test_aer_planning_transport import planning as planning
from tests.e2e.test_aer_planning_transport import (
    project_detail as project_detail,
)

pytestmark = pytest.mark.django_db(transaction=True)


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
