"""Inicialización, estado conservado y presentación de errores del proyecto."""

import pytest
from playwright.sync_api import expect

from tests.e2e.test_aer_executive import fixed_day as fixed_day
from tests.e2e.test_project_detail_entry import project_detail as project_detail
from tests.e2e.test_project_tabs import enter

pytestmark = pytest.mark.django_db(transaction=True)


@pytest.mark.parametrize("family", ["aer", "ixs"])
def test_session_preserves_same_project_and_resets_changed_project(
    portal, project_detail, fixed_day, family
):
    enter(portal, project_detail[1 if family == "aer" else 0])
    result = portal.evaluate(
        """family => {
      const env=projectSessionContext();
      const aer=family==='aer';
      const data=aer?env.aer():env.ixs();
      const oldState=aer?env.aerAi():env.clockify();
      oldState.sentinel='cached';
      if(aer) _aerRenderShell=()=>{}; else _ixsRenderShell=()=>{};
      if(!aer&&window.beeIxsRuntime)beeIxsRuntime.mount=()=>{};
      if(aer&&window.beeAerRuntime)beeAerRuntime.mount=()=>{};
      data.hitos=[{}];data.historialCompleto=[{}];
      const render=aer?renderDashboardAERTYMProyecto:renderDashboardIXBSaaSRaaS;
      render(data);
      const same=(aer?env.aerAi():env.clockify())===oldState;
      const changed={...data,proyecto:{...data.proyecto,id:'OTHER-PROJECT'}};
      render(changed);
      const next=aer?env.aerAi():env.clockify();
      return {same,reset:next!==oldState,removed:next.sentinel===undefined,
        id:aer?next.id:next.proyectoId,tab:aer?env.aerTab():env.ixsTab()};
    }""",
        family,
    )
    assert result == {
        "same": True,
        "reset": True,
        "removed": True,
        "id": "OTHER-PROJECT",
        "tab": "ejecutivo" if family == "aer" else "resumen",
    }


def test_ixs_ai_keeps_same_state_then_clears_sources_in_original_load_order(
    portal, project_detail, fixed_day
):
    enter(portal, project_detail[0])
    result = portal.evaluate("""() => {
      const calls=[];
      ixsIAStyles=()=>calls.push('styles');
      ixsIAPintar=()=>calls.push('view');
      ixsIACargarFuentes=()=>calls.push('sources');
      ixsIACargarHistoria=()=>calls.push('history');
      ixsIACargarDrive=()=>calls.push('drive');
      if(window.beeIxsRuntime) {
        beeIxsRuntime.paintAi=()=>calls.push('view');
        beeIxsAdapters.load=source=>calls.push(source);
      }
      ixsIAAbrir();
      const saved=ixsIAState;saved.driveSelected=['saved'];
      ixsIAAbrir();
      const same=ixsIAState===saved;
      ixsProyectoActual={...ixsProyectoActual,proyecto:{id:'NEW'}};
      ixsIAAbrir();
      return {same,reset:ixsIAState!==saved,
        selected:ixsIAState.driveSelected,calls};
    }""")
    assert result == {
        "same": True,
        "reset": True,
        "selected": [],
        # Styles are linked by the modern template; no injector call remains.
        "calls": ["view", "sources", "history", "drive"] * 3,
    }
    for style_id in ["ixs-ia-styles", "ixs-v74-styles", "aer-dashboard-styles"]:
        expect(portal.locator(f"link#{style_id}")).to_have_attribute(
            "rel", "stylesheet"
        )


def test_client_actions_keeps_shared_state_and_rejects_an_inactive_family(
    portal, project_detail, fixed_day
):
    enter(portal, project_detail[0])
    result = portal.evaluate("""() => {
      let options;
      beeIxsClientActions.load=value=>{options=value;};
      const saved=aerIAState;
      saved.sentinel='preserved';
      ixsTabActual='cliente';
      _aerRenderTab=()=>{};
      if(window.beeIxsRuntime)beeProjectTabs.aer=()=>{};
      ixsCargarClienteAcciones();
      const id=ixsProyectoActual.proyecto.id;
      const active=options.current(id);
      const response={partes:[{uid:'part'}]};
      options.apply(response);
      const same=aerIAState===saved;
      const bound=aerDashboardData===response;
      const cache=options.cache===ixsClienteAccionesCache;
      const preserved=aerIAState.sentinel==='preserved';
      const parts=aerIAState.accionesPartes===response.partes;
      const wrongProject=options.current('OTHER');
      ixsTabActual='resumen';
      const wrongTab=options.current(id);
      ixsTabActual='cliente';
      document.querySelector('.ixs-shell').className='aer-shell';
      const inactive=options.current(id);
      return {active,same,bound,cache,preserved,parts,
        wrongProject,wrongTab,inactive};
    }""")
    assert result == {
        "active": True,
        "same": True,
        "bound": True,
        "cache": True,
        "preserved": True,
        "parts": True,
        "wrongProject": False,
        "wrongTab": False,
        "inactive": False,
    }
