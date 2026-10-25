"""Guardar hito → recarga/reintento por módulos, sin entradas anteriores."""

import pytest
from playwright.sync_api import expect

from tests.e2e.test_aer_executive import fixed_day as fixed_day
from tests.e2e.test_ixs_executive import ixs as ixs
from tests.e2e.test_ixs_milestones import milestones as milestones
from tests.e2e.test_ixs_planning_transport import open_planning
from tests.e2e.test_ixs_planning_transport import planning as planning
from tests.e2e.test_project_detail_entry import project_detail as project_detail

pytestmark = pytest.mark.django_db(transaction=True)


@pytest.mark.parametrize("retry", [False, True])
def test_milestone_save_reloads_directly_and_can_retry(
    portal, milestones, ixs, fixed_day, retry
):
    data, _ = ixs
    data["hitosAdicionales"] = [
        {
            "tipo": "Demo",
            "indice": 7,
            "fecha": "2026-09-10",
            "observacion": "Nota",
        }
    ]
    errors = []
    portal.on("pageerror", lambda error: errors.append(str(error)))
    open_planning(portal)
    portal.evaluate("""() => {
      for(const name of ['loadDashboard','projectEntryContext',
        'renderDashboardAERTYMProyecto','renderDashboardIXBSaaSRaaS',
        'projectTabsContext'])
        window[name]=()=>{throw Error('previous reload '+name);};
    }""")
    reloads = []

    def reload(route):
        reloads.append(route.request.method)
        if retry and len(reloads) == 1:
            route.fulfill(status=503, json={"error": {"message": "Reintenta"}})
        else:
            route.fallback()

    portal.route("**/screens/proyectos/AMK.008/ejecutivo/", reload)
    portal.locator("#ixs-gantt-historico button.ixs-time-mark").first.click()
    expect(portal.locator("#modal-hito-overlay")).to_be_visible()
    portal.locator(".mh-fecha").fill("2026-11-10")
    portal.locator("#mh-btn-guardar").click()
    expect(portal.locator("#modal-hito-overlay")).to_have_count(0)
    if retry:
        expect(portal.locator("#dashboard-proyecto-detalle")).to_contain_text(
            "Error cargando proyecto"
        )
        portal.get_by_role("button", name="Reintentar", exact=True).click()
    expect(portal.locator(".ixs-nav .active")).to_have_text("Ejecutivo")
    assert reloads == ["GET"] * (2 if retry else 1)
    assert milestones[0] == [
        ("edit", "AMK.008", "Demo", 7, "2026-11-10", "Nota")
    ]
    assert not errors, errors
