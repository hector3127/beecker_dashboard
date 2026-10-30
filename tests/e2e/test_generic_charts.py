"""Gráficas genéricas: referencia visual, escala completa y expansión local."""

import pytest
from playwright.sync_api import expect

from tests.e2e.test_aer_executive import fixed_day as fixed_day
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


def generic(portal, data, block=False):
    portal.goto(portal.base + "/proyectos/AMK.008/")
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
