"""Inicio especial contrastado con el cuerpo original, sin servicios reales."""

import pytest

from tests.e2e.project_reference import load_project_reference
from tests.e2e.test_ixs_executive import ixs as ixs
from tests.e2e.test_project_detail_entry import project_detail as project_detail

pytestmark = pytest.mark.django_db(transaction=True)


@pytest.mark.parametrize("width", [1450, 390])
@pytest.mark.parametrize(
    ("query", "failure"),
    [
        ("", False),
        ("?cuenta=acme", False),
        ("?cuenta=Nueva%20cuenta", False),
        ("?cuenta=ACME&proyecto=amk.008", False),
        ("?proyecto=Missing", False),
        ("?cuenta=ACME", True),
    ],
)
def test_special_start_matches_original(portal, ixs, width, query, failure):
    portal.set_viewport_size({"width": width, "height": 1000})
    portal.goto(portal.base + "/proyectos/AMK.008/")
    portal.locator(".ixs-head").wait_for()
    load_project_reference(portal)
    result = portal.evaluate(
        """async ({query,failure}) => {
      const {createProjectEntry}=await import(
        '/static/app/scripts/pages/project_detail/sections/project_entry.js');
      const filters={clientes:['Todos los clientes','ACME'],proyectos:[
        {id:'AMK.008',nombre:'Nombre',servicio:'IXB'}]};
      const seed=document.getElementById('project-context');
      seed.remove();
      history.replaceState({},'',location.pathname+query);
      const saved={entry:window.beeProjectEntry,filters:readProjectFilters,
        load:loadDashboard};
      const run=async modern=>{
        document.getElementById('view-container').replaceChildren(
          document.getElementById('tpl-dashboard').content.cloneNode(true));
        let requests=0,loads=0;
        mapaMetaProyectosDashboard={};
        const fetch=()=>{
          requests++;
          if(failure)throw Error('Filter failure');
          return filters;
        };
        if(modern){
          const controller=createProjectEntry({filters:async()=>fetch()});
          controller.load=()=>{loads++;};
          await controller.startCompatibility({
            metadata:value=>{mapaMetaProyectosDashboard=value;},
            clientChanged:()=>{},
            previousStart:()=>{throw Error('Old startup used');},
          });
        }else{
          window.beeProjectEntry=undefined;
          readProjectFilters=(ok,fail)=>{
            try{ok(fetch());}catch(error){fail(error);}
          };
          loadDashboard=()=>{loads++;};
          initDashboard(true);
        }
        const project=document.getElementById('f-proyecto');
        const client=document.getElementById('f-cliente');
        const snapshot={requests,loads,project:project.value,
          client:client.value,
          projects:[...project.options].map(x=>[x.value,x.text]),
          clients:[...client.options].map(x=>[x.value,x.text]),
          metadata:mapaMetaProyectosDashboard,
          refresh:typeof document.getElementById('btn-refresh').onclick};
        document.getElementById('btn-refresh').onclick?.();
        snapshot.afterRefresh=loads;
        return snapshot;
      };
      try{
        const previous=await run(false),modern=await run(true);
        return {previous,modern};
      }finally{
        window.beeProjectEntry=saved.entry;
        readProjectFilters=saved.filters;loadDashboard=saved.load;
        document.body.append(seed);
      }
    }""",
        {"query": query, "failure": failure},
    )
    assert result["modern"] == result["previous"]


def test_no_project_entry_uses_modular_special_start(portal, ixs):
    portal.goto(portal.base + "/proyectos/AMK.008/")
    portal.locator(".ixs-head").wait_for()
    result = portal.evaluate(
        """async () => {
      document.getElementById('project-context').remove();
      history.replaceState({},'',location.pathname+'?cuenta=ACME');
      const {createProjectEntry}=await import(
        '/static/app/scripts/pages/project_detail/sections/project_entry.js');
      const controller=createProjectEntry({filters:async()=>({
        clientes:['Todos los clientes','ACME'],proyectos:[]})});
      let loads=0;
      controller.load=()=>{loads++;};
      await controller.start({metadata:()=>{},clientChanged:()=>{},
        previousStart:()=>{throw Error('Previous init called');}});
      return {loads,account:document.getElementById('f-cliente').value};
    }"""
    )
    assert result == {"loads": 1, "account": "ACME"}
