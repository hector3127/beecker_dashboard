"""Actions overview: aligned metrics and real controls in both families."""

from pathlib import Path

import pytest
from playwright.sync_api import expect

from tests.e2e.test_actions_transport import board as board
from tests.e2e.test_actions_transport import family as family
from tests.e2e.test_aer_executive import fixed_day as fixed_day
from tests.e2e.test_ixs_client_actions_transport import (
    client_actions as client_actions,
)
from tests.e2e.test_ixs_executive import ixs as ixs
from tests.e2e.test_project_design_sections import design_site as design_site
from tests.e2e.test_project_detail_entry import project_detail as project_detail

pytestmark = [
    pytest.mark.django_db(transaction=True),
    pytest.mark.usefixtures("design_site", "enforced_csp"),
]


@pytest.mark.parametrize("width", [1450, 900, 390, 320])
@pytest.mark.parametrize("empty", [False, True])
def test_overview_metrics_align(portal, board, family, fixed_day, width, empty):
    portal.set_viewport_size({"width": width, "height": 1000})
    project = "AMK.008" if family == "ixs" else "AER.001"
    portal.goto(portal.base + f"/proyectos/{project}/")
    portal.locator(".ixs-nav" if family == "ixs" else ".aer-tabs").get_by_role(
        "button", name="Acciones", exact=True
    ).click()
    portal.wait_for_load_state("networkidle")
    if empty:
        portal.evaluate("""() => {
          aerDashboardData.acciones = {};
          aerIAState.accionesPartes = [];
          _aerRenderTab();
        }""")
    overview = portal.locator(".aer-action-overview")
    expect(overview).to_be_visible()
    expect(overview.locator(".aer-action-kpi2")).to_have_count(5)
    expect(overview).not_to_contain_text("[object")
    assert overview.locator(".aer-action-kpi2 .top").count() == 0
    assert overview.locator(".aer-action-metric-head svg").count() == 5
    values = overview.locator(".value")
    expect(values.first).to_have_text("0" if empty else "1")
    boxes = [values.nth(i).bounding_box() for i in range(5)]
    if width >= 1100:
        assert max(b["y"] for b in boxes) - min(b["y"] for b in boxes) <= 1
    assert portal.evaluate("document.documentElement.scrollWidth") <= width + 1
    assert overview.evaluate("e => e.scrollWidth <= e.clientWidth+1")
    target = Path(f"tmp/actions-overview/{family}/{empty}")
    target.mkdir(parents=True, exist_ok=True)
    overview.screenshot(path=str(target / f"{width}.png"))
    clean = overview.get_by_role(
        "button", name="Limpiar duplicados", exact=True
    )
    expect(clean).to_be_visible()
    assert clean.locator("svg").count() == 1
    overview.get_by_role("button", name="+ Agregar acción", exact=True).click()
    expect(portal.locator("#aer-modal-back")).to_be_visible()
