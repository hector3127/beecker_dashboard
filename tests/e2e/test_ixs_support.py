"""Auxiliares compartidos: una carga de recursos entre pestañas."""

import pytest
from playwright.sync_api import expect

from tests.e2e.test_aer_executive import fixed_day as fixed_day
from tests.e2e.test_ixs_executive import ixs as ixs
from tests.e2e.test_ixs_planning_transport import planning as planning
from tests.e2e.test_project_detail_entry import project_detail as project_detail

pytestmark = pytest.mark.django_db(transaction=True)


@pytest.mark.parametrize("tab", ["Ejecutivo", "Planeación", "Esfuerzo"])
def test_resource_read_is_shared_and_updates_current_modular_view(
    portal, planning, ixs, fixed_day, tab
):
    held = []
    portal.route(
        "**/screens/proyectos/AMK.008/recursos/",
        lambda route: held.append(route),
    )
    portal.goto(portal.base + "/proyectos/AMK.008/")
    expect(portal.locator(".ixs-head")).to_be_visible()
    portal.locator(".ixs-nav").get_by_role(
        "button", name=tab, exact=True
    ).click()
    portal.evaluate("""() => {
      window.resourcePaints=[];
      for(const [name,method] of [['beeIxsExecutive','resourceTable'],
        ['beeIxsPlanning','paint'],['beeIxsEffort','updateResources']]) {
        const original=window[name][method];
        window[name][method]=(...args)=>{
          resourcePaints.push(name);return original(...args);
        };
      }
      _ixsCargarEstadosRecursos();_ixsCargarEstadosRecursos();
    }""")
    assert len(held) == 1
    held[0].fulfill(
        json={
            "data": {
                "ok": True,
                "filas": [{"nombre": "  ANA PEREZ ", "activo": False}],
            },
            "meta": {},
        }
    )
    portal.wait_for_function("ixsProyectoActual._resourceStatesLoaded===true")
    expected = {
        "Ejecutivo": "beeIxsExecutive",
        "Planeación": "beeIxsPlanning",
        "Esfuerzo": "beeIxsEffort",
    }[tab]
    assert expected in portal.evaluate("resourcePaints")
    assert (
        portal.evaluate("""ixsProyectoActual.filasRecursosCompleto
      .find(row=>_ixsRecursoClave(row.nombre)==='ana perez').activo""")
        is False
    )
    assert portal.locator("#ixs-tab-contenido [onclick]").count() == 0
    portal.evaluate("_ixsCargarEstadosRecursos()")
    assert len(held) == 1
