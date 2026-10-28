"""All project tabs: new workspace, responsive containment and live controls."""

import copy
import json
from pathlib import Path

import pytest
from playwright.sync_api import expect

from tests.e2e.frozen.aer_executive_support import (
    production_site as production_site,
)
from tests.e2e.test_aer_executive import fixed_day as fixed_day
from tests.e2e.test_client_tab import CLIENT
from tests.e2e.test_ixs_client_actions_transport import (
    client_actions as client_actions,
)
from tests.e2e.test_ixs_executive import ixs as ixs
from tests.e2e.test_ixs_raid import ROWS
from tests.e2e.test_project_detail_entry import project_detail as project_detail

pytestmark = [
    pytest.mark.django_db(transaction=True),
    pytest.mark.usefixtures("production_site", "enforced_csp"),
]


@pytest.mark.parametrize("family", ["ixs", "aer"])
@pytest.mark.parametrize("width", [1450, 900, 390, 320])
def test_all_project_tabs_are_readable_and_contained(
    portal, ixs, client_actions, project_detail, fixed_day, family, width
):
    data = project_detail[1] if family == "aer" else ixs[0]
    data["cliente"] = copy.deepcopy(CLIENT)
    client_actions[0]["cliente"] = copy.deepcopy(CLIENT)
    # Only source reads are stubbed; real tab controllers/renderers still run.
    empty = {
        "data": {
            "ok": True,
            "filas": [],
            "registros": [],
            "acciones": [],
            "contactos": [],
            "carpetas": [],
            "archivos": [],
            "config": {},
        },
        "meta": {},
    }
    for pattern in (
        "**/ia/**",
        "**/ia-aer/**",
        "**/evaluaciones-aer/**",
        "**/riesgos-aer/**",
        "**/comunicados/",
    ):
        portal.route(
            "**/api/v1/screens/proyectos/" + pattern,
            lambda route: route.fulfill(json=empty),
        )
    errors = []
    portal.route(
        "**/api/v1/screens/proyectos/**/raid-registro/**",
        lambda route: route.fulfill(
            json={
                "data": {"ok": True, "registros": ROWS, "aviso": ""},
                "meta": {},
            }
        ),
    )
    portal.on("pageerror", lambda error: errors.append(str(error)))
    portal.set_viewport_size({"width": width, "height": 1000})
    portal.goto(
        portal.base
        + f"/proyectos/{data['proyecto']['id']}/?volver=%2Foperativa%2F"
    )
    nav = portal.locator(".aer-tabs" if family == "aer" else ".ixs-nav")
    expect(nav).to_be_visible()
    expect(portal.locator("body")).to_have_attribute(
        "data-project-design", "delivery-v1"
    )
    labels = nav.locator("button").all_text_contents()
    assert len(labels) == (8 if family == "aer" else 10)
    target = Path(f"tmp/design/projects/{family}/{width}")
    target.mkdir(parents=True, exist_ok=True)
    metrics = []
    for index, label in enumerate(labels):
        nav.get_by_role("button", name=label, exact=True).click()
        portal.wait_for_load_state("networkidle")
        portal.evaluate("document.fonts.ready")
        portal.evaluate(
            "() => new Promise(resolve => requestAnimationFrame("
            "() => requestAnimationFrame(resolve)))"
        )
        content = portal.locator(
            "#aer-tab-content" if family == "aer" else "#ixs-tab-contenido"
        )
        expect(content).not_to_be_empty()
        active = nav.locator("button.active")
        expect(active).to_have_attribute("aria-pressed", "true")
        assert active.evaluate(
            "e => {const a=e.getBoundingClientRect(),"
            "b=e.parentElement.getBoundingClientRect(); "
            "return a.left>=b.left-1 && a.right<=b.right+1}"
        )
        assert "Jakarta" in content.evaluate(
            "e => getComputedStyle(e).fontFamily"
        )
        portal.screenshot(path=str(target / f"{index:02d}.png"), full_page=True)
        state = portal.evaluate("""() => ({width:innerWidth,
          scroll:document.documentElement.scrollWidth,
          fonts:[...document.querySelectorAll(
            '#view-container h3,#view-container .label')].slice(0,10)
            .map(e=>({text:e.textContent,font:getComputedStyle(e).fontFamily})),
          tables:[...document.querySelectorAll('#view-container table')]
            .map(t=>({contained:!!t.closest('.pd-table-scroll'),
              rows:t.rows.length})),
          overflow:[...document.querySelectorAll('#view-container *')]
          .filter(e=>{
            const r=e.getBoundingClientRect();
            return r.width&&r.right>innerWidth+2&&
              !e.closest('.pd-table-scroll,.ixs-nav,.aer-tabs');
          }).slice(0,12).map(e=>({tag:e.tagName,cls:e.className,right:e.getBoundingClientRect().right}))})""")
        metrics.append({"tab": label, **state})
        (target / "metrics.json").write_text(
            json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        assert state["scroll"] <= width + 1, (label, state)
        assert all(t["contained"] for t in state["tables"])
    assert not errors
