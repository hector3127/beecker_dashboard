"""Carga inicial modular: mensajes, reintento y respuestas superadas."""

from pathlib import Path

import pytest
from playwright.sync_api import expect

from tests.e2e.test_aer_executive import fixed_day as fixed_day
from tests.e2e.test_ixs_effort import state
from tests.e2e.test_project_detail_entry import project_detail as project_detail
from tests.e2e.test_project_tabs import enter

pytestmark = pytest.mark.django_db(transaction=True)


@pytest.mark.parametrize("scenario", ["loading", "failure", "server_error"])
@pytest.mark.parametrize("width", [1450, 900, 390])
def test_entry_messages_match_previous(
    portal, project_detail, fixed_day, scenario, width
):
    portal.set_viewport_size({"width": width, "height": 1000})
    directory = (
        Path("tmp/migration/project_detail/loading") / scenario / str(width)
    )
    directory.mkdir(parents=True, exist_ok=True)
    states = []
    for previous in [True, False]:
        enter(portal, project_detail[1], previous)
        portal.evaluate(
            """scenario => {
          if(scenario==='server_error') {
            showError({message:'Fuente no disponible'}); return;
          }
          if(window.beeProjectData) beeProjectData.dashboard=()=>
            scenario==='failure'?Promise.reject(Error('Fuente no disponible'))
              :new Promise(()=>{});
          else readProjectDashboard=(id,aer,ok,fail)=>{
            if(scenario==='failure')fail(Error('Fuente no disponible'));
          };
          loadDashboard();
        }""",
            scenario,
        )
        if scenario == "failure":
            expect(
                portal.get_by_role("button", name="Reintentar")
            ).to_be_visible()
        selector = "#view-container, #view-container *"
        portal.mouse.move(0, 0)
        states.append(state(portal, selector))
        portal.screenshot(
            path=str(directory / ("old.png" if previous else "new.png")),
            full_page=True,
        )
    assert states[0] == states[1]
    assert portal.locator("#view-container [onclick]").count() == 0


@pytest.mark.parametrize("outcome", ["success", "failure"])
def test_newest_load_wins_and_old_response_does_not_replace_it(
    portal, project_detail, fixed_day, outcome
):
    enter(portal, project_detail[1])
    portal.evaluate(
        """outcome => {
      window.pending=[];window.renders=[];
      beeAerRuntime.initialize=data=>renders.push(data.cut);
      beeProjectData.dashboard=()=>new Promise((resolve,reject)=>
        pending.push({resolve,reject}));
      const compatibilityRequest=dashboardRequestSeq;
      loadDashboard();loadDashboard();
      if(compatibilityRequest===dashboardRequestSeq)renders.push('old-compat');
      pending[1].resolve({cut:'new'});
      if(outcome==='failure')pending[0].reject(Error('old failure'));
      else pending[0].resolve({cut:'old'});
    }""",
        outcome,
    )
    portal.wait_for_function("renders.length===1")
    assert portal.evaluate("renders") == ["new"]
    expect(portal.locator("#view-container")).not_to_contain_text("old failure")


def test_detached_target_and_error_text_cannot_restore_old_dom(
    portal, project_detail, fixed_day
):
    enter(portal, project_detail[1])
    portal.evaluate("""() => {
      window.resolveLoad=null;window.renders=[];
      beeAerRuntime.initialize=data=>renders.push(data);
      beeProjectData.dashboard=()=>new Promise(resolve=>resolveLoad=resolve);
      loadDashboard();
      showError({message:'<img src=x onerror=alert(1)>'});
      resolveLoad({ok:true});
    }""")
    expect(portal.locator("#view-container")).to_have_text(
        "Error cargando datos: <img src=x onerror=alert(1)>"
    )
    assert portal.locator("#view-container img").count() == 0
    assert portal.evaluate("renders") == []
