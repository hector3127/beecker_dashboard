"""Línea temporal aislada: paridad con la anterior y texto seguro."""

import pytest
from playwright.sync_api import expect

from tests.e2e.test_aer_executive import fixed_day as fixed_day
from tests.e2e.test_ixs_executive import ixs as ixs
from tests.e2e.test_project_detail_entry import project_detail as project_detail

pytestmark = pytest.mark.django_db(transaction=True)


def test_component_does_not_interpolate_html(portal, ixs, fixed_day):
    portal.goto(portal.base + "/proyectos/AMK.008/")
    expect(portal.locator(".ixs-head")).to_be_visible()
    result = portal.evaluate("""() => {
      const attack='<img src=x onerror="window.genericAttack=true">';
      const data={proyecto:{estadoGeneral:'CERRADO'},
        hitos:[{nombre:attack,fechaInicioPlan:'2026-07-01',fechaFinPlan:'2026-08-01'}],
        historialCompleto:[{fase:attack,fechaInicio:'2026-07-01',fechaFin:'2026-08-01'}],
        hitosAdicionales:[{tipo:attack,fecha:'15/07/2026',indice:1}]};
      const descriptor=Object.getOwnPropertyDescriptor(
        Element.prototype,'innerHTML');
      Object.defineProperty(Element.prototype,'innerHTML',{...descriptor,
        set(){throw Error('timeline HTML interpolation');}});
      const root=beeGenericTimelineView(beeGenericTimeline(data));
      document.body.append(root);
      return {text:root.textContent.includes(attack),
        images:root.querySelectorAll('img').length,
        attack:!!window.genericAttack};
    }""")
    assert result == {"text": True, "images": 0, "attack": False}
