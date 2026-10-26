"""Rango Clockify: mismo texto/estilos que RPC, carga segura por API."""

from pathlib import Path

import pytest
from playwright.sync_api import expect

from tests.e2e.test_aer_executive import fixed_day as fixed_day
from tests.e2e.test_ixs_effort import state as capture_state
from tests.e2e.test_ixs_executive import ixs as ixs
from tests.e2e.test_project_detail_entry import project_detail as project_detail

pytestmark = pytest.mark.django_db(transaction=True)
RANGE = {
    "ok": True,
    "fechaInicio": "2026-08-01",
    "fechaFin": "2026-10-23T12:00:00",
}


@pytest.mark.parametrize("width", [1450, 900, 390])
@pytest.mark.parametrize("variant", ["dates", "missing", "error"])
def test_range_matches_previous(portal, ixs, fixed_day, width, variant):
    data, _ = ixs
    payload = RANGE if variant == "dates" else {"ok": variant == "missing"}
    calls = []
    portal.on("request", lambda request: calls.append(request.url))
    portal.route(
        "**/api/v1/screens/proyectos/AMK.008/clockify-rango/",
        lambda route: route.fulfill(json={"data": payload, "meta": {}}),
    )
    portal.route(
        "**/api/rpc/obtenerRangoClockifyProyecto/",
        lambda route: route.fulfill(json={"ok": True, "result": payload}),
    )
    portal.set_viewport_size({"width": width, "height": 1000})
    states = []
    directory = (
        Path("tmp/migration/project_detail/clockify_range")
        / variant
        / str(width)
    )
    directory.mkdir(parents=True, exist_ok=True)
    for previous in [True, False]:
        portal.goto(
            portal.base
            + "/proyectos/AMK.008/"
            + ("?vista=anterior" if previous else "")
        )
        expect(portal.locator(".ixs-head")).to_be_visible()
        portal.wait_for_load_state("networkidle")
        calls.clear()
        portal.evaluate(
            """data => {
          cargarRaidProyectoEjecutivoAzure=()=>{};
          cargarHorasTasksProyectoClockify=()=>{};
          renderDashboardEjecutivoProyecto(data);
        }""",
            data,
        )
        portal.wait_for_load_state("networkidle")
        target = portal.locator("#rango-clockify-dashboard")
        expect(target).not_to_have_text("Consultando rango…")
        if variant == "dates":
            expect(target).to_contain_text("Clockify:")
        else:
            expect(target).to_have_text("")
        # Isolate the same source panel width, while its outer shell migrates.
        parent = target.locator("..")
        if previous:
            component_width = parent.evaluate(
                "node=>node.getBoundingClientRect().width"
            )
        parent.evaluate(
            """(node,width)=>{
          const host=document.createElement('div');host.style.width=width+'px';
          document.body.append(host);host.append(node);node.id='range-comparison';
        }""",
            component_width,
        )
        state = capture_state(portal, "#range-comparison, #range-comparison *")
        x, y = state[0]["box"][:2]
        for item in state:
            box = item["box"]
            item["box"] = [round(box[0] - x, 1), round(box[1] - y, 1), *box[2:]]
        states.append(state)
        parent.screenshot(
            path=str(directory / ("old.png" if previous else "new.png"))
        )
        assert any(
            (
                "rpc/obtenerRangoClockifyProyecto/"
                if previous
                else "/clockify-rango/"
            )
            in url
            for url in calls
        )
        if not previous:
            assert not any(
                "rpc/obtenerRangoClockifyProyecto/" in url for url in calls
            )
    assert states[0] == states[1]


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
