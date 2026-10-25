"""Navegación IXS sin ejecutar los renderizadores previos."""

import pytest
from playwright.sync_api import expect

from tests.e2e.test_aer_executive import fixed_day as fixed_day
from tests.e2e.test_ixs_ai_sources import ia as ia
from tests.e2e.test_ixs_executive import ixs as ixs
from tests.e2e.test_ixs_planning_transport import open_planning
from tests.e2e.test_ixs_planning_transport import planning as planning
from tests.e2e.test_project_communiques import gmail as gmail
from tests.e2e.test_project_detail_entry import project_detail as project_detail

pytestmark = pytest.mark.django_db(transaction=True)


def test_planning_editors_and_communiques_do_not_use_previous_callbacks(
    portal, planning, gmail, fixed_day
):
    errors = []
    portal.on("pageerror", lambda error: errors.append(str(error)))
    open_planning(portal)
    portal.evaluate("""() => {
      for(const name of ['ixsAbrirPlanEditor','ixsAbrirExtension','_ixeAuto',
        '_ixsEnsureStyles','_aerEnsureStyles','ixsIAStyles','_ixsPintarPlaneacion'])
        window[name]=()=>{throw Error('previous tool '+name);};
    }""")
    portal.get_by_role(
        "button", name="+ Registrar vacaciones", exact=True
    ).click()
    form = portal.locator("#ixs-plan-form")
    expect(form).to_be_visible()
    form.locator('[name="recurso"]').fill("Ana Pérez")
    form.locator('[name="inicio"]').fill("2026-10-26")
    form.locator('[name="fin"]').fill("2026-10-30")
    form.get_by_role("button", name="Guardar", exact=True).click()
    expect(portal.locator("#ixs-plan-modal")).to_have_count(0)
    assert planning[2][-1][0:2] == ("save", "vacacion")
    assert planning[2][-1][2]["recurso"] == "Ana Pérez"
    portal.get_by_role("button", name="Comunicados", exact=True).click()
    expect(portal.locator(".ixe-dialog")).to_be_visible()
    expect(portal.locator(".ixe-thread")).to_have_count(1)
    assert not gmail
    assert not errors, errors


def test_navigation_ai_and_refresh_do_not_use_previous_renderers(
    portal, ia, fixed_day
):
    errors, requests = [], []
    portal.on("pageerror", lambda error: errors.append(str(error)))
    portal.on("request", lambda request: requests.append(request.url))
    portal.goto(portal.base + "/proyectos/AMK.008/")
    expect(portal.locator(".ixs-head")).to_be_visible()
    portal.wait_for_load_state("networkidle")
    portal.evaluate("""() => {
      for(const name of ['_ixsRenderShell','_ixsRenderTab','ixsCambiarTab',
        'ixsRecargarProyecto','renderDashboardIXBSaaSRaaS','ixsIAAbrir',
        'ixsIAPintar','ixsIAAccionesVista','ixsIACargarFuentes',
        'ixsIACargarHistoria','ixsIACargarDrive','ixsIAContexto',
        'ixsIASnapshot','ixsIACambios','ixsIACapacidad'])
        window[name]=()=>{throw Error('previous runtime '+name);};
    }""")
    portal.locator(".ixs-nav").get_by_role(
        "button", name="IA", exact=True
    ).click()
    expect(portal.locator(".ixai")).to_be_visible()
    portal.wait_for_load_state("networkidle")
    assert portal.evaluate("ixsIAState.azure !== null")
    portal.locator(".ixs-nav").get_by_role(
        "button", name="Ejecutivo", exact=True
    ).click()
    expect(portal.locator(".ixs-nav .active")).to_have_text("Ejecutivo")
    portal.locator(".ixs-head button").click()
    expect(portal.locator(".ixs-head")).to_be_visible()
    portal.wait_for_load_state("networkidle")
    assert sum("/AMK.008/ejecutivo/" in url for url in requests) == 2
    assert not errors, errors
