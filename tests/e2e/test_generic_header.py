"""Encabezado e indicadores genéricos: referencia visual y texto seguro."""

from pathlib import Path

import pytest
from playwright.sync_api import expect

from tests.e2e.test_aer_executive import fixed_day as fixed_day
from tests.e2e.test_ixs_effort import state as capture_state
from tests.e2e.test_ixs_executive import ixs as ixs
from tests.e2e.test_project_detail_entry import project_detail as project_detail

pytestmark = pytest.mark.django_db(transaction=True)


@pytest.mark.parametrize("width", [1450, 900, 390])
@pytest.mark.parametrize("kind", ["header", "kpis"])
@pytest.mark.parametrize("variant", ["full", "missing", "completed", "nonprd"])
def test_header_matches_previous(portal, ixs, fixed_day, width, kind, variant):
    data, _ = ixs
    if variant == "missing":
        data["proyecto"].update(
            sponsor="", pm="", deliveryManager="", fechaCorte=""
        )
        data["avance"].update(
            pct=0, indiceRitmo=None, pctTiempoTranscurrido=None
        )
        data["kpisExtra"] = None
    if variant == "completed":
        data["hitos"] = [
            {
                "nombre": "Deployment",
                "fechaInicioPlan": "2026-07-01",
                "fechaFinPlan": "2026-08-01",
            }
        ]
        data["historialCompleto"] = [
            {
                "fase": "Deployment",
                "fechaInicio": "2026-07-01",
                "fechaFin": "2026-08-01",
            }
        ]
        data["avance"]["indiceRitmo"] = 2
    if variant == "nonprd":
        data["proyecto"].update(nivelRiesgoFecha="Alto", estadoColor="rojo")
    portal.set_viewport_size({"width": width, "height": 1000})
    directory = (
        Path("tmp/migration/project_detail/generic_header")
        / kind
        / variant
        / str(width)
    )
    directory.mkdir(parents=True, exist_ok=True)
    states, svg_states = [], []
    for previous in [True, False]:
        portal.goto(
            portal.base
            + "/proyectos/AMK.008/"
            + ("?vista=anterior" if previous else "")
        )
        expect(portal.locator(".ixs-head")).to_be_visible()
        portal.wait_for_load_state("networkidle")
        portal.evaluate(
            """({data,kind,variant}) => {
          cargarRaidProyectoEjecutivoAzure=()=>{};
          cargarHorasTasksProyectoClockify=()=>{};
          if(variant==='nonprd')mapaMetaProyectosDashboard[data.proyecto.id]={servicio:'CUSTOM'};
          renderDashboardEjecutivoProyecto(data);
          const target=document.getElementById('dashboard-proyecto-detalle');
          (kind==='header'?target.firstElementChild:target.querySelector('.kpi-grid')).id='gh-comparison';
        }""",
            {"data": data, "kind": kind, "variant": variant},
        )
        portal.wait_for_load_state("networkidle")
        if previous:
            component_width = portal.locator("#gh-comparison").evaluate(
                "node=>node.getBoundingClientRect().width"
            )
        portal.locator("#gh-comparison").evaluate(
            """(node,width)=>{
          const host=document.createElement('div');host.style.width=width+'px';
          document.body.append(host);host.append(node);
        }""",
            component_width,
        )
        portal.mouse.move(0, 0)
        state = capture_state(portal, "#gh-comparison, #gh-comparison *")
        x, y = state[0]["box"][:2]
        for item in state:
            box = item["box"]
            item["box"] = [round(box[0] - x, 1), round(box[1] - y, 1), *box[2:]]
        states.append(state)
        svg_states.append(
            portal.locator(
                "#gh-comparison svg, #gh-comparison svg *"
            ).evaluate_all("""nodes=>nodes.map(n=>{
          const c=getComputedStyle(n);
          return [n.namespaceURI,n.getAttribute('viewBox'),
            c.fill,c.stroke,c.strokeWidth,c.strokeDasharray];})""")
        )
        portal.locator("#gh-comparison").screenshot(
            path=str(directory / ("old.png" if previous else "new.png"))
        )
    diffs = [
        (i, {key: (a[key], b[key]) for key in a if a[key] != b[key]})
        for i, (a, b) in enumerate(zip(*states, strict=True))
        if a != b
    ]
    assert not diffs, diffs[:5]
    assert svg_states[0] == svg_states[1]
    expect(portal.locator("#gh-comparison")).to_have_class(
        "card gh-header" if kind == "header" else "kpi-grid gh-kpis"
    )


def test_header_uses_text_and_svg_dom_without_html_interpolation(
    portal, ixs, fixed_day
):
    portal.goto(portal.base + "/proyectos/AMK.008/")
    expect(portal.locator(".ixs-head")).to_be_visible()
    result = portal.evaluate("""() => {
      const attack='<img src=x onerror="window.headerAttack=true">';
      const descriptor=Object.getOwnPropertyDescriptor(
        Element.prototype,'innerHTML');
      Object.defineProperty(Element.prototype,'innerHTML',{...descriptor,
        set(){throw Error('header HTML interpolation');}});
      const data={proyecto:{id:attack,nombre:attack,cliente:attack,
        sponsor:attack,pm:attack,
        deliveryManager:attack,estadoGeneral:attack},avance:{pct:43,indiceRitmo:1},
        presupuesto:{budget:100,burn:43,etc:57,pctEjecutado:43}};
      const blocks=beeGenericHeader(data,
        {color:'#2E7D32',riskClass:'badge-bajo'});
      document.body.append(blocks.header,blocks.kpis);
      return {text:blocks.header.textContent.includes(attack),
        images:blocks.header.querySelectorAll('img').length,
        svg:blocks.kpis.querySelector('svg').namespaceURI,
        financial:!!blocks.kpis.querySelector('#kpi-cumpl-financiero-card'),
        attack:!!window.headerAttack};
    }""")
    assert result == {
        "text": True,
        "images": 0,
        "svg": "http://www.w3.org/2000/svg",
        "financial": True,
        "attack": False,
    }
