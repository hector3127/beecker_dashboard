"""Encabezado e indicadores genéricos: referencia visual y texto seguro."""

import pytest
from playwright.sync_api import expect

from tests.e2e.test_aer_executive import fixed_day as fixed_day
from tests.e2e.test_ixs_executive import ixs as ixs
from tests.e2e.test_project_detail_entry import project_detail as project_detail

pytestmark = pytest.mark.django_db(transaction=True)


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
