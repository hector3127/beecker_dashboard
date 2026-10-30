"""Fuentes del Ejecutivo genérico: paridad visual, API y cargas tardías."""

import pytest
from playwright.sync_api import expect

from tests.e2e.test_aer_executive import fixed_day as fixed_day
from tests.e2e.test_ixs_executive import ixs as ixs
from tests.e2e.test_project_detail_entry import project_detail as project_detail

pytestmark = pytest.mark.django_db(transaction=True)
TARGETS = {
    "tasks": "clockify-task-hours-proyecto",
    "raid": "riesgos-criticos-proyecto-azure",
}


def open_generic(portal, data, previous=False):
    portal.goto(
        portal.base
        + "/proyectos/AMK.008/"
        + ("?vista=anterior" if previous else "")
    )
    expect(portal.locator(".ixs-head")).to_be_visible()
    portal.wait_for_load_state("networkidle")
    portal.evaluate("data=>renderDashboardEjecutivoProyecto(data)", data)
    portal.wait_for_load_state("networkidle")


@pytest.mark.parametrize("kind", ["tasks", "raid"])
def test_transport_errors_preserve_messages_and_totals(portal, ixs, kind):
    data, _ = ixs
    portal.goto(portal.base + "/proyectos/AMK.008/")
    expect(portal.locator(".ixs-head")).to_be_visible()
    portal.route(
        f"**/AMK.008/{kind}/",
        lambda route: route.fulfill(
            status=503, json={"error": {"message": "Fuente no disponible"}}
        ),
    )
    portal.evaluate("data=>renderDashboardEjecutivoProyecto(data)", data)
    target = portal.locator("#" + TARGETS[kind])
    expect(target).to_contain_text(
        "Error cargando RAID de Azure:"
        if kind == "raid"
        else "Error cargando horas por task:"
    )
    if kind == "raid":
        expect(portal.locator("#raid-proyecto-riesgos")).to_have_text("—")


def test_safe_text_without_html_interpolation(portal, ixs):
    data, _ = ixs
    open_generic(portal, data)
    result = portal.evaluate("""async () => {
      const attack='<img src=x onerror="window.sourcesAttack=true">';
      const descriptor=Object.getOwnPropertyDescriptor(
        Element.prototype,'innerHTML');
      Object.defineProperty(Element.prototype,'innerHTML',{...descriptor,
        set(){throw Error('HTML interpolation');}});
      const data={tasks:async()=>({ok:true,nomenclatura:attack,tasks:[
        {nombre:attack,horas:1},{nombre:attack,horas:0}]}),
        raid:async()=>({ok:true,riesgos:[{id:attack,descripcion:attack,
          severity:attack,estado:attack,impacto:attack,probabilidad:attack}]})};
      const path='/static/app/scripts/pages/project_detail/sections/';
      const {createGenericSources}=await import(path+'generic_sources.js');
      const sources=createGenericSources(data);
      await sources.tasks('A');await sources.raid('A');
      const nodes=['clockify-task-hours-proyecto',
        'riesgos-criticos-proyecto-azure'].map(id=>document.getElementById(id));
      return {text:nodes.every(n=>n.textContent.includes(attack)),
        images:nodes.reduce((a,n)=>a+n.querySelectorAll('img').length,0),
        attack:!!window.sourcesAttack};
    }""")
    assert result == {"text": True, "images": 0, "attack": False}


def test_late_response_cannot_replace_reloaded_project(portal, ixs):
    data, _ = ixs
    open_generic(portal, data)
    result = portal.evaluate("""async () => {
      const path='/static/app/scripts/pages/project_detail/sections/';
      const {createGenericSources}=await import(path+'generic_sources.js');
      let finish;
      const old=document.getElementById('riesgos-criticos-proyecto-azure');
      const sources=createGenericSources({
        raid:()=>new Promise(resolve=>finish=resolve)});
      const pending=sources.raid('old');
      const replacement=old.cloneNode(false);
      replacement.textContent='New project';
      old.replaceWith(replacement);
      const total=document.getElementById('raid-proyecto-riesgos');
      total.textContent='42';
      finish({ok:true,totalRiesgos:999});await pending;
      return {text:replacement.textContent,total:total.textContent};
    }""")
    assert result == {"text": "New project", "total": "42"}
