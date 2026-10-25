"""Navegación y fuentes AER con las entradas anteriores bloqueadas."""

import pytest
from playwright.sync_api import expect

from tests.e2e.test_aer_ai_sources import ia as ia
from tests.e2e.test_aer_executive import fixed_day as fixed_day
from tests.e2e.test_project_detail_entry import project_detail as project_detail

pytestmark = pytest.mark.django_db(transaction=True)


def test_navigation_ai_and_refresh_do_not_use_previous_entries(
    portal, ia, fixed_day
):
    errors, requests = [], []
    portal.on("pageerror", lambda error: errors.append(str(error)))
    portal.on("request", lambda request: requests.append(request.url))
    portal.goto(portal.base + "/proyectos/AER.001/")
    expect(portal.locator(".aer-head")).to_be_visible()
    portal.wait_for_load_state("networkidle")
    portal.evaluate("""() => {
      for(const name of ['_aerRenderShell','_aerRenderTab','aerCambiarTab',
        'aerRecargarProyecto','renderDashboardAERTYMProyecto',
        'aerIAFuentesModulares','aerIAAccionesModulares',
        'aerIAPresentacionModular','aerIAPresentacionContexto','aerIAContexto',
        'aerIACargarAnalisis','aerIACargarMinutas','aerIACargarConfigMinutas',
        'aerIACargarResumenEjecutivo','aerIACargarAccionesPartes'])
        window[name]=()=>{throw Error('previous AER runtime '+name);};
    }""")
    portal.locator(".aer-tabs").get_by_role(
        "button", name="✦ IA", exact=True
    ).click()
    expect(portal.locator(".aeri")).to_be_visible()
    expect(portal.locator(".aeri")).to_contain_text("Comité")
    portal.wait_for_load_state("networkidle")
    portal.locator(".aer-head button").click()
    expect(portal.locator(".aer-tabs .active")).to_have_text("✦ IA")
    portal.wait_for_load_state("networkidle")
    portal.locator(".aer-tabs").get_by_role(
        "button", name="Ejecutivo", exact=True
    ).click()
    expect(portal.locator(".aer-tabs .active")).to_have_text("Ejecutivo")
    assert sum("/AER.001/aer/" in url for url in requests) == 2
    assert not errors, errors
