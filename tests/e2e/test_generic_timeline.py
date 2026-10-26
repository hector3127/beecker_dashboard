"""Modelo/fallback en la misma plantilla; vista genérica pendiente."""

from pathlib import Path

import pytest
from playwright.sync_api import expect

from tests.e2e.test_aer_executive import fixed_day as fixed_day
from tests.e2e.test_ixs_effort import state as capture_state
from tests.e2e.test_ixs_executive import ixs as ixs
from tests.e2e.test_project_detail_entry import project_detail as project_detail

pytestmark = pytest.mark.django_db(transaction=True)


@pytest.mark.parametrize("width", [1450, 900, 390])
@pytest.mark.parametrize("variant", ["full", "closed", "suspended", "empty"])
def test_generic_timeline_model_preserves_the_existing_modern_view(
    portal, ixs, fixed_day, width, variant
):
    data, _ = ixs
    if variant == "closed":
        data["proyecto"]["estadoGeneral"] = "CERRADO"
    elif variant == "suspended":
        data["suspensiones"] = [
            {"fechaInicio": "2026-08-01", "fechaFin": "2026-12-01"}
        ]
    elif variant == "empty":
        data["hitos"] = []
    portal.set_viewport_size({"width": width, "height": 1000})
    states = []
    directory = (
        Path("tmp/migration/project_detail/generic_timeline")
        / variant
        / str(width)
    )
    directory.mkdir(parents=True, exist_ok=True)
    for previous in [True, False]:
        portal.goto(portal.base + "/proyectos/AMK.008/")
        expect(portal.locator(".ixs-head")).to_be_visible()
        portal.wait_for_load_state("networkidle")
        if previous:
            # Use the untouched calculation block with the same template CSS.
            # Generic old-vs-new template styling has not been migrated yet.
            portal.evaluate("window.beeGenericTimeline = undefined")
            portal.evaluate("window.beeGenericTimelineView = undefined")
        portal.evaluate(
            """data => {
          cargarRaidProyectoEjecutivoAzure=()=>{};
          cargarHorasTasksProyectoClockify=()=>{};
          window.genericModelCalls=0;
          if(window.beeGenericTimeline){
            const original=beeGenericTimeline;
            beeGenericTimeline=(...args)=>{
              genericModelCalls++;return original(...args);
            };
          }
          renderDashboardEjecutivoProyecto(data);
        }""",
            data,
        )
        expect(portal.locator("#dashboard-proyecto-detalle")).to_contain_text(
            "LÍNEA DE TIEMPO — HITOS PRINCIPALES"
        )
        portal.wait_for_load_state("networkidle")
        portal.mouse.move(0, 0)
        states.append(
            capture_state(
                portal,
                "#dashboard-proyecto-detalle, #dashboard-proyecto-detalle *",
            )
        )
        portal.screenshot(
            path=str(directory / ("fallback.png" if previous else "model.png")),
            full_page=True,
        )
    assert states[0] == states[1]
    assert portal.evaluate("genericModelCalls") == (
        0 if variant == "empty" else 1
    )
