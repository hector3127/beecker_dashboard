"""Montaje modular: ruta elegida, enlaces de estado y compatibilidad visual."""

from pathlib import Path

import pytest
from playwright.sync_api import expect

from tests.e2e.test_aer_executive import fixed_day as fixed_day
from tests.e2e.test_ixs_effort import state
from tests.e2e.test_project_detail_entry import project_detail as project_detail

pytestmark = pytest.mark.django_db(transaction=True)


def enter(page, data, previous=False):
    page.goto(
        page.base
        + f"/proyectos/{data['proyecto']['id']}/"
        + ("?vista=anterior" if previous else "")
    )
    expect(page.locator(".aer-head, .ixs-head")).to_be_visible()
    page.wait_for_load_state("networkidle")


@pytest.mark.parametrize("family", ["aer", "ixs"])
def test_known_tabs_use_modular_registry_and_lazy_contexts(
    portal, project_detail, fixed_day, family
):
    enter(portal, project_detail[1 if family == "aer" else 0])
    portal.evaluate(
        """family => {
      window.tabMounts=[];
      const mount=name=>(target,...args)=>{
        tabMounts.push([name,target.id,args[0]?.proyecto?.id||args[0]?.id]);
        target.replaceChildren(document.createTextNode('Montado '+name));
      };
      const names=family==='aer'
        ? ['beeAerPlanning','beeAerEffort','beeAerRisks','beeProjectActions',
           'beeAerResources','beeProjectClient','beeAerAiPresentation']
        : ['beeIxsPlanning','beeIxsEffort','beeIxsResources','beeIxsAzureTab',
           'beeIxsRaid','beeIxsCommunication'];
      names.forEach(name=>window[name]={mount:mount(name)});
      beeProjectExecutive=mount('aer-executive');
      beeIxsExecutive={mount:mount('ixs-executive')};
      _ixsCargarEstadosRecursos=()=>{};
      ixsIAAbrir=()=>tabMounts.push(['ixs-ia']);
      ixsCargarClienteAcciones=()=>tabMounts.push(['ixs-shared']);
      if(window.beeIxsRuntime){
        beeIxsRuntime.openAi=()=>tabMounts.push(['ixs-ia']);
        beeIxsRuntime.loadClientActions=()=>tabMounts.push(['ixs-shared']);
      }
      if(family==='aer'&&window.beeAerRuntime)beeAerRuntime.load=()=>{};
      aerIACargarAnalisis=aerIACargarMinutas=aerIACargarConfigMinutas=
        aerIACargarResumenEjecutivo=aerIACargarAccionesPartes=()=>{};
      const descriptor=Object.getOwnPropertyDescriptor(
        Element.prototype,'innerHTML');
      Object.defineProperty(Element.prototype,'innerHTML',{...descriptor,set(value){
        if(['aer-tab-content','ixs-tab-contenido'].includes(this.id))
          throw Error('old dispatcher renderer');
        descriptor.set.call(this,value);
      }});
    }""",
        family,
    )
    names = (
        [
            "Ejecutivo",
            "Planeación",
            "Esfuerzo",
            "Riesgos",
            "Acciones",
            "Recursos",
            "Cliente",
            "✦ IA",
        ]
        if family == "aer"
        else [
            "Ejecutivo",
            "Planeación",
            "Esfuerzo",
            "Recursos",
            "Gestión RAID",
            "Acciones",
            "Cliente",
            "Comunicación",
            "Azure DevOps",
            "IA",
        ]
    )
    for name in names:
        portal.locator(".aer-tabs, .ixs-nav").get_by_role(
            "button", name=name, exact=True
        ).click()
    expected = (
        [
            "aer-executive",
            "beeAerPlanning",
            "beeAerEffort",
            "beeAerRisks",
            "beeProjectActions",
            "beeAerResources",
            "beeProjectClient",
            "beeAerAiPresentation",
        ]
        if family == "aer"
        else [
            "ixs-executive",
            "beeIxsPlanning",
            "beeIxsEffort",
            "beeIxsResources",
            "beeIxsRaid",
            "ixs-shared",
            "ixs-shared",
            "beeIxsCommunication",
            "beeIxsAzureTab",
            "ixs-ia",
        ]
    )
    assert [x[0] for x in portal.evaluate("tabMounts")] == expected


@pytest.mark.parametrize("family", ["aer", "ixs"])
@pytest.mark.parametrize("width", [1450, 900, 390])
def test_unknown_tab_fallback_matches_previous(
    portal, project_detail, fixed_day, family, width
):
    data = project_detail[1 if family == "aer" else 0]
    portal.set_viewport_size({"width": width, "height": 1000})
    directory = Path("tmp/migration/project_detail/tabs") / family / str(width)
    directory.mkdir(parents=True, exist_ok=True)
    states = []
    selector = (
        "#aer-tab-content, #aer-tab-content *"
        if family == "aer"
        else "#ixs-tab-contenido, #ixs-tab-contenido *"
    )
    for previous in [True, False]:
        enter(portal, data, previous)
        portal.evaluate(
            "aerCambiarTab('unknown')"
            if family == "aer"
            else "ixsCambiarTab('unknown')"
        )
        portal.mouse.move(0, 0)
        states.append(state(portal, selector))
        portal.screenshot(
            path=str(directory / ("old.png" if previous else "new.png")),
            full_page=True,
        )
    assert states[0] == states[1]
    assert (
        portal.locator(
            "#aer-tab-content [onclick], #ixs-tab-contenido [onclick]"
        ).count()
        == 0
    )
