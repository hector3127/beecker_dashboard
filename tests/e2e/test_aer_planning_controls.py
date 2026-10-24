"""Filtros, selección y rango de Planeación AER: paridad y estado."""

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


def open_header(page, field):
    label = {
        "tipo": "Tipo",
        "actividad": "Actividad",
        "responsable": "Responsable",
        "compromiso": "Compromiso",
        "estado": "Estado",
        "cierre": "Fecha de cierre",
    }[field]
    page.locator(".plan-pretty th").filter(has_text=label).get_by_role(
        "button"
    ).click()
    expect(page.locator("#aer-plan-filter-pop")).to_be_visible()


@pytest.mark.parametrize("width", [1450, 900, 390])
@pytest.mark.parametrize(
    "field",
    ["tipo", "actividad", "responsable", "compromiso", "estado", "cierre"],
)
def test_filter_popup_matches_previous(
    portal, planning, fixed_day, width, field
):
    portal.set_viewport_size({"width": width, "height": 1000})
    directory = (
        Path("tmp/migration/project_detail/aer_planning_controls")
        / field
        / str(width)
    )
    directory.mkdir(parents=True, exist_ok=True)
    snapshots = []
    for previous in [True, False]:
        enter(portal, previous)
        open_header(portal, field)
        portal.mouse.move(0, 0)
        snapshots.append(
            state(portal, "#aer-plan-filter-pop, #aer-plan-filter-pop *")
        )
        portal.screenshot(
            path=str(directory / ("old.png" if previous else "new.png")),
            full_page=True,
        )
    assert snapshots[0] == snapshots[1]
    assert portal.locator("#aer-plan-filter-pop [onclick]").count() == 0


def test_controls_work_without_previous_helpers(portal, planning, fixed_day):
    enter(portal)
    portal.evaluate("""() => {
      const fail=()=>{throw Error('Old control called');};
      _aerInitPlanFiltroMes=aerCambiarRangoPlan=aerAbrirFiltroCabecera=fail;
      _aerPlanFilterSet=aerLimpiarFiltrosPlan=aerAplicarFiltrosPlan=fail;
      aerAplicarFiltroCabecera=aerLimpiarFiltroCabecera=aerCerrarFiltroCabecera=fail;
      aerTogglePlanAll=aerActualizarSeleccionPlan=fail;
      _aerRenderTab();
    }""")
    search = portal.get_by_placeholder("Buscar actividad…")
    search.fill("diseno")
    expect(portal.locator("#aer-plan-filter-count")).to_have_text("1 de 7")
    portal.locator("#aer-plan-select-all").check()
    expect(portal.locator("#aer-plan-selected-count")).to_have_text(
        "1 seleccionada"
    )
    portal.get_by_role("button", name="Limpiar filtros", exact=True).click()
    expect(portal.locator("#aer-plan-filter-count")).to_have_text("7 de 7")
    portal.locator(".aer-plan-range input").first.fill("2026-08")
    portal.locator(".aer-plan-range input").first.press("Tab")
    expect(portal.locator(".aer-gantt2-head")).to_contain_text("AGOSTO")
    open_header(portal, "estado")
    portal.locator("#aer-hf-estado").select_option("Completado")
    portal.locator("#aer-plan-filter-pop").get_by_role(
        "button", name="Aplicar", exact=True
    ).click()
    expect(portal.locator("#aer-plan-filter-count")).to_have_text("2 de 7")


def test_dates_clear_keyboard_and_outside_close(portal, planning, fixed_day):
    enter(portal)
    open_header(portal, "compromiso")
    expect(portal.locator("#aer-hf-comp-desde")).to_be_focused()
    portal.locator("#aer-hf-comp-desde").fill("2026-10-01")
    portal.locator("#aer-hf-comp-hasta").fill("2026-10-31")
    apply = portal.locator("#aer-plan-filter-pop").get_by_role(
        "button", name="Aplicar", exact=True
    )
    apply.focus()
    apply.press("Enter")
    expect(portal.locator("#aer-plan-filter-count")).to_have_text("2 de 7")
    open_header(portal, "compromiso")
    expect(portal.locator("#aer-hf-comp-desde")).to_have_value("2026-10-01")
    portal.locator("#aer-plan-filter-pop").get_by_role(
        "button", name="Borrar", exact=True
    ).click()
    expect(portal.locator("#aer-plan-filter-count")).to_have_text("7 de 7")
    open_header(portal, "tipo")
    portal.get_by_role(
        "heading", name="Actividades / Entregables", exact=True
    ).click()
    expect(portal.locator("#aer-plan-filter-pop")).to_have_count(0)


def test_hidden_selected_rows_and_indeterminate_are_preserved(
    portal, planning, fixed_day
):
    enter(portal)
    portal.locator(".aer-plan-row-check").first.check()
    assert portal.locator("#aer-plan-select-all").evaluate("e=>e.indeterminate")
    portal.get_by_placeholder("Buscar actividad…").fill("Desarrollo")
    portal.locator("#aer-plan-select-all").check()
    expect(portal.locator("#aer-plan-selected-count")).to_have_text(
        "2 seleccionadas"
    )
    portal.locator("#aer-plan-select-all").uncheck()
    expect(portal.locator("#aer-plan-selected-count")).to_have_text(
        "1 seleccionada"
    )
    portal.get_by_placeholder("Buscar actividad…").fill("")
    assert portal.locator("#aer-plan-select-all").evaluate("e=>e.indeterminate")


def test_options_remain_text_and_stale_popup_cannot_change_project(
    portal, planning, fixed_day
):
    unsafe = '<img src=x onerror="window.injected=true">'
    planning[0]["plan"]["filas"][0]["responsable"] = unsafe
    enter(portal)
    open_header(portal, "responsable")
    assert (
        unsafe
        in portal.locator("#aer-hf-responsable option").all_text_contents()
    )
    assert portal.locator("#aer-plan-filter-pop img").count() == 0
    portal.locator("#aer-hf-responsable").select_option(unsafe)
    portal.evaluate("() => {aerDashboardData={...aerDashboardData};}")
    portal.locator("#aer-plan-filter-pop").get_by_role(
        "button", name="Aplicar", exact=True
    ).click()
    assert portal.evaluate("aerPlanTableFilters.responsable") == ""
    assert portal.evaluate("window.injected||false") is False
