"""Gráficas genéricas: referencia visual, escala completa y expansión local."""

from pathlib import Path

import pytest
from playwright.sync_api import expect

from tests.e2e.test_aer_executive import fixed_day as fixed_day
from tests.e2e.test_ixs_effort import state as capture_state
from tests.e2e.test_ixs_executive import ixs as ixs
from tests.e2e.test_project_detail_entry import project_detail as project_detail

pytestmark = pytest.mark.django_db(transaction=True)
TARGETS = {
    "area": "donut-area-ejecutivo",
    "resources": "comparativo-recurso-mini",
    "roles": "comparativo-rol-mini",
}


def many(data):
    base = data["filasRecursosCompleto"][0]
    data["filasRecursosCompleto"] += [
        {
            **base,
            "nombre": f"Extra {i}",
            "horasReales": i,
            "horasEstimadas": 1000 if i == 0 else 10,
        }
        for i in range(4)
    ]


def generic(portal, data, previous=False, block=False):
    portal.goto(
        portal.base
        + "/proyectos/AMK.008/"
        + ("?vista=anterior" if previous else "")
    )
    expect(portal.locator(".ixs-head")).to_be_visible()
    portal.wait_for_load_state("networkidle")
    portal.evaluate(
        """({data,block})=>{
      cargarRaidProyectoEjecutivoAzure=()=>{};cargarHorasTasksProyectoClockify=()=>{};
      if(block)for(const name of ['renderDonut','renderComparativo',
        'renderComparativoConVerTodos'])
        window[name]=()=>{throw Error('previous chart '+name);};
      renderDashboardEjecutivoProyecto(data);
    }""",
        {"data": data, "block": block},
    )
    portal.wait_for_load_state("networkidle")


@pytest.mark.parametrize("width", [1450, 900, 390])
@pytest.mark.parametrize("kind", TARGETS)
@pytest.mark.parametrize("variant", ["full", "empty", "many"])
def test_charts_match_previous(portal, ixs, fixed_day, width, kind, variant):
    data, _ = ixs
    if variant == "empty":
        data.update(distribucionArea=[], filasRecursosCompleto=[], porRol=[])
    if variant == "many":
        many(data)
    portal.set_viewport_size({"width": width, "height": 1000})
    directory = (
        Path("tmp/migration/project_detail/generic_charts")
        / kind
        / variant
        / str(width)
    )
    directory.mkdir(parents=True, exist_ok=True)
    states, svg_states = [], []
    for previous in [True, False]:
        generic(portal, data, previous)
        target = portal.locator("#" + TARGETS[kind])
        if previous:
            component_width = target.evaluate(
                "n=>n.getBoundingClientRect().width"
            )
        target.evaluate(
            """(node,width)=>{const host=document.createElement('div');
          host.style.width=width+'px';
          document.body.append(host);host.append(node);}""",
            component_width,
        )
        portal.mouse.move(0, 0)
        state = capture_state(
            portal, "#" + TARGETS[kind] + ", #" + TARGETS[kind] + " *"
        )
        x, y = state[0]["box"][:2]
        for item in state:
            box = item["box"]
            # Hidden descendants have a viewport rect of all zeroes, not a
            # position relative to their host. Preserve that assertion; moving
            # the component must not invent negative coordinates for them.
            if box != [0, 0, 0, 0]:
                item["box"] = [
                    round(box[0] - x, 1),
                    round(box[1] - y, 1),
                    *box[2:],
                ]
        states.append(state)
        svg_states.append(
            target.locator("svg, svg *").evaluate_all("""nodes=>nodes.map(n=>{
          const c=getComputedStyle(n);
          return [n.namespaceURI,c.fill,c.stroke,c.strokeWidth,
            c.strokeDasharray,c.strokeDashoffset];})""")
        )
        target.screenshot(
            path=str(directory / ("old.png" if previous else "new.png"))
        )
    diffs = [
        (i, {k: (a[k], b[k]) for k in a if a[k] != b[k]})
        for i, (a, b) in enumerate(zip(*states, strict=True))
        if a != b
    ]
    assert not diffs, diffs[:5]
    assert svg_states[0] == svg_states[1]
    assert not target.locator("[onclick]").count()


def test_expand_is_local_and_does_not_call_previous_helpers(
    portal, ixs, fixed_day
):
    data, _ = ixs
    many(data)
    errors = []
    portal.on("pageerror", lambda e: errors.append(str(e)))
    generic(portal, data, block=True)
    requests = []
    portal.on("request", lambda request: requests.append(request.url))
    hidden = portal.locator("#comparativo-recurso-mini-ocultos")
    expect(hidden).to_be_hidden()
    portal.locator("#comparativo-recurso-mini-toggle").click()
    expect(hidden).to_be_visible()
    expect(portal.locator("#comparativo-recurso-mini-toggle")).to_have_text(
        "Ver menos"
    )
    portal.locator("#comparativo-recurso-mini-toggle").click()
    expect(hidden).to_be_hidden()
    expect(portal.locator("#comparativo-recurso-mini-toggle")).to_have_text(
        "Ver todos (4 más)"
    )
    assert not requests
    assert not errors, errors


def test_chart_labels_use_text_and_svg_dom(portal, ixs, fixed_day):
    portal.goto(portal.base + "/proyectos/AMK.008/")
    expect(portal.locator(".ixs-head")).to_be_visible()
    result = portal.evaluate("""()=>{
      const attack='<img src=x onerror="window.chartAttack=true">';
      const root=document.createElement('div');
      for(const id of ['donut-area-ejecutivo','comparativo-recurso-mini',
        'comparativo-rol-mini']){
        document.getElementById(id)?.remove();
        const node=document.createElement('div');node.id=id;root.append(node);}
      document.body.append(root);
      const d=Object.getOwnPropertyDescriptor(Element.prototype,'innerHTML');
      Object.defineProperty(Element.prototype,'innerHTML',{...d,
        set(){throw Error('chart HTML interpolation');}});
      beeGenericCharts.mount({distribucionArea:[{nombre:attack,horas:1,pct:100}],
        filasRecursosCompleto:[{nombre:attack,posicion:attack,horasEstimadas:1,horasReales:1}],
        porRol:[{rol:attack,horasEstimadas:1,horasReales:1}]});
      return {text:root.textContent.includes(attack),
        images:root.querySelectorAll('img').length,
        svg:root.querySelector('svg').namespaceURI,attack:!!window.chartAttack};
    }""")
    assert result == {
        "text": True,
        "images": 0,
        "svg": "http://www.w3.org/2000/svg",
        "attack": False,
    }
