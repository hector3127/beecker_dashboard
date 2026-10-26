"""Fuentes del Ejecutivo genérico: paridad visual, API y cargas tardías."""

from pathlib import Path

import pytest
from playwright.sync_api import expect

from tests.e2e.test_aer_executive import fixed_day as fixed_day
from tests.e2e.test_ixs_effort import state as capture_state
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
@pytest.mark.parametrize("variant", ["full", "empty", "error"])
@pytest.mark.parametrize("width", [1450, 900, 390])
def test_sources_match_previous(portal, ixs, fixed_day, kind, variant, width):
    data, responses = ixs
    key = "tasks_dashboard" if kind == "tasks" else "get_project_raid"
    if variant != "full":
        responses[key] = (
            {"ok": True}
            if variant == "empty"
            else {"ok": False, "error": "Fuente temporalmente no disponible"}
        )
    elif kind == "raid":
        responses[key]["riesgos"][0].update(
            {"severity": "Critical", "probabilidad": "Alta"}
        )
    else:
        responses[key]["tasks"].append({"nombre": "Negativas", "horas": -2})
    portal.set_viewport_size({"width": width, "height": 1000})
    directory = (
        Path("tmp/migration/project_detail/generic_sources")
        / kind
        / variant
        / str(width)
    )
    directory.mkdir(parents=True, exist_ok=True)
    states = []
    for previous in [True, False]:
        calls = []
        portal.on(
            "request", lambda request, calls=calls: calls.append(request.url)
        )
        open_generic(portal, data, previous)
        target = portal.locator("#" + TARGETS[kind])
        expect(
            target.locator(
                ".gs-error"
                if variant == "error" and not previous
                else ":scope > *"
            ).first
        ).to_be_attached()
        if previous:
            component_width = target.evaluate(
                "n=>n.getBoundingClientRect().width"
            )
        target.evaluate(
            """(node,width)=>{
          const host=document.createElement('div');host.style.width=width+'px';
          document.body.append(host);host.append(node);
        }""",
            component_width,
        )
        if kind == "tasks" and variant == "full":
            target.locator("summary").click()
            expect(target.locator("details")).to_have_attribute("open", "")
        state = capture_state(
            portal, "#" + TARGETS[kind] + ", #" + TARGETS[kind] + " *"
        )
        x, y = state[0]["box"][:2]
        for item in state:
            box = item["box"]
            item["box"] = [round(box[0] - x, 1), round(box[1] - y, 1), *box[2:]]
        states.append(state)
        target.screenshot(
            path=str(directory / ("old.png" if previous else "new.png"))
        )
        if not previous:
            assert any(f"/AMK.008/{kind}/" in url for url in calls)
            assert not any(
                "rpc/obtenerRaidProyectoEjecutivoAzure/" in url
                or "rpc/obtenerResumenTasksTagsClockifyProyecto/" in url
                for url in calls
            )
            assert not target.locator("[style], [onclick]").count()
            if kind == "raid":
                expect(portal.locator("#raid-proyecto-riesgos")).to_have_text(
                    "—"
                    if variant == "error"
                    else str(responses[key].get("totalRiesgos", 0))
                )
    diffs = [
        (index, {k: (a[k], b[k]) for k in a if a[k] != b[k]})
        for index, (a, b) in enumerate(zip(*states, strict=True))
        if a != b
    ]
    assert not diffs, diffs[:5]


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
