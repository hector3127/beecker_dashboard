"""Carga inicial modular: mensajes, reintento y respuestas superadas."""

import pytest
from playwright.sync_api import expect

from tests.e2e.test_aer_executive import fixed_day as fixed_day
from tests.e2e.test_project_detail_entry import project_detail as project_detail
from tests.e2e.test_project_tabs import enter

pytestmark = pytest.mark.django_db(transaction=True)


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
