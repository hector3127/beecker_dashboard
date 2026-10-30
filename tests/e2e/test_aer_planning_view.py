"""Planeación AER: vista modular, calendario, tablas y controles existentes."""

import pytest
from playwright.sync_api import expect

from tests.e2e.test_aer_planning_transport import enter
from tests.e2e.test_aer_planning_transport import fixed_day as fixed_day
from tests.e2e.test_aer_planning_transport import planning as planning
from tests.e2e.test_aer_planning_transport import (
    project_detail as project_detail,
)

pytestmark = pytest.mark.django_db(transaction=True)


def test_view_does_not_call_old_renderers(portal, planning, fixed_day):
    enter(portal)
    portal.evaluate("""() => {
      const fail=()=>{throw Error('Old renderer called');};
      _aerVistaPlaneacion=_aerOpcionesEstadoPlan=_aerVacEstadoClase=fail;
      _aerRenderTab();
    }""")
    expect(portal.locator(".aer-gantt2-grid")).to_be_visible()
    portal.get_by_role("button", name="+ Actividad / Hito", exact=True).click()
    expect(portal.locator("#ap-act")).to_be_visible()
    portal.locator("#aer-modal-back").get_by_role(
        "button", name="✕", exact=True
    ).click()
    portal.get_by_role(
        "button", name="+ Registrar vacaciones", exact=True
    ).click()
    expect(portal.locator("#av-rec")).to_be_visible()


def test_search_selection_and_range_keep_behavior(portal, planning, fixed_day):
    enter(portal)
    search = portal.get_by_placeholder("Buscar actividad…")
    search.fill("diseno")
    expect(portal.locator("#aer-plan-filter-count")).to_have_text("1 de 7")
    portal.locator("#aer-plan-select-all").check()
    expect(portal.locator("#aer-plan-selected-count")).to_have_text(
        "1 seleccionada"
    )
    assert portal.locator(".aer-plan-row-check:checked").count() == 1
    portal.get_by_role("button", name="Limpiar filtros", exact=True).click()
    expect(portal.locator("#aer-plan-filter-count")).to_have_text("7 de 7")
    expect(portal.locator("#aer-plan-selected-count")).to_have_text(
        "0 seleccionadas"
    )
    portal.locator(".aer-plan-range input").first.fill("2026-08")
    portal.locator(".aer-plan-range input").first.press("Tab")
    expect(portal.locator(".aer-gantt2-head")).to_contain_text("AGOSTO")
    portal.get_by_role("button", name="⌄ Filtros", exact=True).click()
    expect(portal.locator("#aer-plan-filter-pop")).to_be_visible()


def test_source_text_and_uid_are_not_html(portal, planning, fixed_day):
    unsafe = '<img src=x onerror="window.injected=true">'
    data = planning[0]
    for row in data["plan"]["filas"]:
        row["actividad"] = unsafe
    data["plan"]["filas"][0]["uid"] = "p'9"
    enter(portal)
    expect(portal.locator(".aer-gantt2-label .name").first).to_have_text(unsafe)
    expect(portal.locator("#aer-plan-table-body tr").first).to_contain_text(
        unsafe
    )
    assert portal.locator(".aer-plan-dashboard img").count() == 0
    assert portal.evaluate("window.injected||false") is False
    portal.locator("#aer-plan-table-body tr").first.get_by_title(
        "Editar actividad completa"
    ).click()
    expect(portal.locator("#ap-act")).to_have_value(unsafe)
