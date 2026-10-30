"""Rango Clockify: mismo texto/estilos que RPC, carga segura por API."""

import pytest
from playwright.sync_api import expect

from tests.e2e.test_aer_executive import fixed_day as fixed_day
from tests.e2e.test_ixs_executive import ixs as ixs
from tests.e2e.test_project_detail_entry import project_detail as project_detail

pytestmark = pytest.mark.django_db(transaction=True)
RANGE = {
    "ok": True,
    "fechaInicio": "2026-08-01",
    "fechaFin": "2026-10-23T12:00:00",
}


def test_range_transport_error_clears_loading(portal, ixs):
    portal.goto(portal.base + "/proyectos/AMK.008/")
    expect(portal.locator(".ixs-head")).to_be_visible()
    portal.route(
        "**/clockify-rango/",
        lambda route: route.fulfill(
            status=503, json={"error": {"message": "Unavailable"}}
        ),
    )
    portal.evaluate("""() => {
      const node=document.createElement('span');node.id='range-test';
      document.body.append(node);
      _pintarRangoClockifyProyecto('AMK.008','range-test');
    }""")
    expect(portal.locator("#range-test")).to_have_text("")
