"""Tabla de recursos y resumen de hitos: paridad y texto seguro."""

import pytest
from playwright.sync_api import expect

from tests.e2e.test_aer_executive import fixed_day as fixed_day
from tests.e2e.test_ixs_executive import ixs as ixs
from tests.e2e.test_project_detail_entry import project_detail as project_detail

pytestmark = pytest.mark.django_db(transaction=True)


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
