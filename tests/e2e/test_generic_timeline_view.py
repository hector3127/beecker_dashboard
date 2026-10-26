"""Línea temporal aislada: paridad con la anterior y texto seguro."""

from pathlib import Path

import pytest
from playwright.sync_api import expect

from tests.e2e.test_aer_executive import fixed_day as fixed_day
from tests.e2e.test_ixs_effort import state as capture_state
from tests.e2e.test_ixs_executive import ixs as ixs
from tests.e2e.test_project_detail_entry import project_detail as project_detail

pytestmark = pytest.mark.django_db(transaction=True)


@pytest.mark.parametrize("width", [1450, 900, 390])
@pytest.mark.parametrize("variant", ["full", "closed", "markers", "empty"])
def test_component_matches_previous(portal, ixs, fixed_day, width, variant):
    data, _ = ixs
    if variant == "closed":
        data["proyecto"]["estadoGeneral"] = "CERRADO"
    if variant == "empty":
        data["hitos"] = []
    if variant == "markers":
        data["hitosAdicionales"] = [
            {"tipo": name, "fecha": date, "indice": i}
            for i, (name, date) in enumerate(
                [
                    ("🎥 Demo", "15/07/2026"),
                    ("QA", "01/09/2026"),
                    ("🚀 Producción", "20/11/2026"),
                ]
            )
        ]
    portal.set_viewport_size({"width": width, "height": 1000})
    directory = (
        Path("tmp/migration/project_detail/generic_timeline_view")
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
            """data => {
          cargarRaidProyectoEjecutivoAzure=()=>{};
          cargarHorasTasksProyectoClockify=()=>{};
          renderDashboardEjecutivoProyecto(data);
          const title=[...document.querySelectorAll('h3')].find(
            node=>node.textContent==='LÍNEA DE TIEMPO — HITOS PRINCIPALES');
          title.parentElement.parentElement.children[1].id='gt-comparison';
        }""",
            data,
        )
        portal.wait_for_load_state("networkidle")
        if previous:
            component_width = portal.locator("#gt-comparison").evaluate(
                "node => node.getBoundingClientRect().width"
            )
        # Isolate the component under the same original width. Pending generic
        # buttons alter its parent's min-content width on mobile, outside scope.
        portal.locator("#gt-comparison").evaluate(
            """(node, width) => {
              const host=document.createElement('div');
              host.style.width=width+'px';
              document.body.append(host);host.append(node);
            }""",
            component_width,
        )
        portal.mouse.move(0, 0)
        state = capture_state(portal, "#gt-comparison, #gt-comparison *")
        # Compare boxes relative to the component, retaining all sizes/CSS.
        x, y = state[0]["box"][:2]
        for item in state:
            box = item["box"]
            item["box"] = [round(box[0] - x, 1), round(box[1] - y, 1), *box[2:]]
        states.append(state)
        portal.locator("#gt-comparison").screenshot(
            path=str(directory / ("old.png" if previous else "new.png"))
        )
    diffs = [
        (i, {key: (a[key], b[key]) for key in a if a[key] != b[key]})
        for i, (a, b) in enumerate(zip(*states, strict=True))
        if a != b
    ]
    assert not diffs, diffs[:5]
    expect(portal.locator("#gt-comparison")).to_have_class(
        "gt-empty" if variant == "empty" else "gt-scroll"
    )
    assert not portal.locator("#gt-comparison [onclick]").count()


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
