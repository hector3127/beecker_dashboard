"""Tabla de recursos y resumen de hitos: paridad y texto seguro."""

from pathlib import Path

import pytest
from playwright.sync_api import expect

from tests.e2e.test_aer_executive import fixed_day as fixed_day
from tests.e2e.test_ixs_effort import state as capture_state
from tests.e2e.test_ixs_executive import ixs as ixs
from tests.e2e.test_project_detail_entry import project_detail as project_detail

pytestmark = pytest.mark.django_db(transaction=True)


@pytest.mark.parametrize("width", [1450, 900, 390])
@pytest.mark.parametrize("kind", ["resources", "milestones"])
@pytest.mark.parametrize("variant", ["full", "empty", "markers"])
def test_panels_match_previous(portal, ixs, fixed_day, width, kind, variant):
    data, _ = ixs
    if variant == "empty":
        data["filasRecursosCompleto"] = []
        data["totalesRecursos"] = {}
        data["hitos"] = []
    if variant == "markers":
        data["hitosAdicionales"] = [
            {
                "tipo": "🎥 Demo",
                "fecha": "15/07/2026",
                "indice": 1,
                "observacion": "Nota con 'comillas'",
            },
            {"tipo": "QA", "fecha": "20/11/2026", "indice": 2},
        ]
        data["suspensiones"] = [
            {"fechaInicio": "2026-10-01", "fechaFin": "2026-12-01"}
        ]
    portal.set_viewport_size({"width": width, "height": 1000})
    directory = (
        Path("tmp/migration/project_detail/generic_panels")
        / kind
        / variant
        / str(width)
    )
    directory.mkdir(parents=True, exist_ok=True)
    states = []
    for previous in [True, False]:
        portal.goto(
            portal.base
            + "/proyectos/AMK.008/"
            + ("?vista=anterior" if previous else "")
        )
        expect(portal.locator(".ixs-head")).to_be_visible()
        portal.wait_for_load_state("networkidle")
        portal.evaluate(
            """({data,kind}) => {
          cargarRaidProyectoEjecutivoAzure=()=>{};
          cargarHorasTasksProyectoClockify=()=>{};
          renderDashboardEjecutivoProyecto(data);
          const root=kind==='resources'?
            document.getElementById('card-carga-trabajo-recurso'):
            [...document.querySelectorAll('h3')].find(
              n=>n.textContent==='HITOS DEL PROYECTO').parentElement;
          root.id='gp-comparison';
        }""",
            {"data": data, "kind": kind},
        )
        portal.wait_for_load_state("networkidle")
        if previous:
            component_width = portal.locator("#gp-comparison").evaluate(
                "node=>node.getBoundingClientRect().width"
            )
        portal.locator("#gp-comparison").evaluate(
            """(node,width)=>{
          const host=document.createElement('div');host.style.width=width+'px';
          document.body.append(host);host.append(node);
        }""",
            component_width,
        )
        portal.mouse.move(0, 0)
        state = capture_state(portal, "#gp-comparison, #gp-comparison *")
        x, y = state[0]["box"][:2]
        for item in state:
            box = item["box"]
            item["box"] = [round(box[0] - x, 1), round(box[1] - y, 1), *box[2:]]
        states.append(state)
        portal.locator("#gp-comparison").screenshot(
            path=str(directory / ("old.png" if previous else "new.png"))
        )
    diffs = [
        (i, {key: (a[key], b[key]) for key in a if a[key] != b[key]})
        for i, (a, b) in enumerate(zip(*states, strict=True))
        if a != b
    ]
    assert not diffs, diffs[:5]
    if kind == "resources":
        expect(portal.locator("#gp-comparison.gp-resources")).to_be_visible()
    else:
        assert (
            portal.locator(
                "#gp-comparison .gp-empty, #gp-comparison .gp-milestone-row"
            ).count()
            > 0
        )
    assert not portal.locator("#gp-comparison [onclick]").count()


def test_panels_use_safe_text_and_keep_range_target(portal, ixs, fixed_day):
    portal.goto(portal.base + "/proyectos/AMK.008/")
    expect(portal.locator(".ixs-head")).to_be_visible()
    result = portal.evaluate("""() => {
      const attack='<img src=x onerror="window.panelAttack=true">';
      const descriptor=Object.getOwnPropertyDescriptor(
        Element.prototype,'innerHTML');
      Object.defineProperty(Element.prototype,'innerHTML',{...descriptor,
        set(){throw Error('panel HTML interpolation');}});
      const resources=beeGenericPanels.resources({filasRecursosCompleto:[
        {posicion:attack,nombre:attack,banda:attack,estado:attack}]});
      const milestones=document.createElement('div');
      milestones.append(beeGenericPanels.milestones([
        {nombre:attack,estado:'Pendiente',esAdicional:true,observacion:attack}]));
      document.body.append(resources,milestones);
      return {resources:resources.textContent.includes(attack),
        milestones:milestones.textContent.includes(attack),
        images:resources.querySelectorAll('img').length+milestones.querySelectorAll('img').length,
        range:!!resources.querySelector('#rango-clockify-dashboard'),attack:!!window.panelAttack};
    }""")
    assert result == {
        "resources": True,
        "milestones": True,
        "images": 0,
        "range": True,
        "attack": False,
    }
