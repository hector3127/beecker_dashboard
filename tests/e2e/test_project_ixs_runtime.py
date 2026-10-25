"""Navegación IXS sin ejecutar los renderizadores previos."""

import pytest
from playwright.sync_api import expect

from tests.e2e.test_aer_executive import fixed_day as fixed_day
from tests.e2e.test_ixs_ai_sources import ia as ia
from tests.e2e.test_ixs_executive import ixs as ixs
from tests.e2e.test_ixs_planning_transport import planning as planning
from tests.e2e.test_project_detail_entry import project_detail as project_detail

pytestmark = pytest.mark.django_db(transaction=True)


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
