"""Resumen Azure: cifras, estilo, límites y controles iguales al anterior."""

from pathlib import Path

import pytest
from playwright.sync_api import expect

from tests.e2e.test_aer_executive import fixed_day as fixed_day
from tests.e2e.test_ixs_azure_transport import enter
from tests.e2e.test_ixs_effort import state as capture_state
from tests.e2e.test_ixs_executive import ixs as ixs
from tests.e2e.test_ixs_planning_transport import planning as planning
from tests.e2e.test_project_detail_entry import project_detail as project_detail

pytestmark = pytest.mark.django_db(transaction=True)
IDS = [
    "ixs-azure-kpis",
    "ixs-azure-health",
    "ixs-azure-stale",
    "ixs-azure-by-assignee",
    "ixs-azure-dates",
    "ixs-azure-status-summary",
]
SELECTOR = ", ".join(f"#{key}, #{key} *" for key in IDS)


@pytest.fixture
def summary(planning):
    _, azure, _, _ = planning
    rows = [
        {
            "id": 101 + i,
            "titulo": f"AMK.008 - Entrega {i}",
            "tipo": "To Be" if i % 2 else "Issue",
            "estado": [
                "Active",
                "Closed",
                "Cancelled",
                "Proposed",
                "Blocked",
                "Resolved",
                "Other",
            ][i % 7],
            "asignadoA": f"Persona {i}",
            "avanceTotal": i * 12,
            "qaListo": i % 3 == 0,
            "fechaLimiteDev": f"2026-10-{i + 1:02}",
            "ultimoSeguimiento": "2026-10-01",
            "diasSinActualizar": i * 3,
            "url": f"https://dev.azure.com/org/proj/_workitems/edit/{101 + i}",
            "iterationPath": "AMK\\Development",
        }
        for i in range(10)
    ]
    azure.update(items=rows, allItems=rows, stale=rows)
    return azure


@pytest.mark.parametrize("width", [1450, 900, 390])
@pytest.mark.parametrize("variant", ["full", "empty", "closed", "no-detail"])
def test_summary_matches_previous(portal, summary, fixed_day, width, variant):
    if variant == "empty":
        summary.update(items=[], allItems=[], stale=[])
    elif variant == "closed":
        for row in summary["items"]:
            row.update(estado="Closed", avanceTotal=100, qaListo=True)
        summary["stale"] = []
    elif variant == "no-detail":
        summary.update(items=[], stale=[])
    portal.set_viewport_size({"width": width, "height": 1000})
    states = []
    directory = (
        Path("tmp/migration/project_detail/ixs_azure_summary")
        / variant
        / str(width)
    )
    directory.mkdir(parents=True, exist_ok=True)
    for previous in [True, False]:
        enter(portal, previous)
        portal.wait_for_load_state("networkidle")
        portal.mouse.move(0, 0)
        states.append(capture_state(portal, SELECTOR))
        portal.screenshot(
            path=str(directory / ("old.png" if previous else "new.png")),
            full_page=True,
        )
    assert states[0] == states[1]
    assert (
        portal.locator(", ".join(f"#{key} [onclick]" for key in IDS)).count()
        == 0
    )


@pytest.mark.parametrize(
    "panel,visible,total",
    [("stale", 3, 8), ("by-assignee", 5, 10), ("dates", 5, 8)],
)
def test_expand_collapse_and_refresh_reset(
    portal, summary, fixed_day, panel, visible, total
):
    enter(portal)
    box = portal.locator("#ixs-azure-" + panel)
    extra = box.locator("[data-ixs-more]:visible")
    button = box.get_by_role("button")
    expect(button).to_have_text(f"Ver más ({total - visible})")
    expect(extra).to_have_count(0)
    button.click()
    expect(extra).to_have_count(total - visible)
    expect(button).to_have_text("Ver menos")
    button.click()
    expect(extra).to_have_count(0)
    button.click()
    portal.get_by_text("↻ Actualizar Azure", exact=True).click()
    expect(button).to_have_text(f"Ver más ({total - visible})")
    expect(extra).to_have_count(0)


def test_summary_renders_source_text_safely(portal, summary, fixed_day):
    text = '<img src=x onerror="window.injected=1">'
    for row in summary["items"]:
        row.update(titulo=text, asignadoA=text, tipo=text, estado=text)
    enter(portal)
    expect(portal.locator("#ixs-azure-stale")).to_contain_text(text)
    expect(portal.locator("#ixs-azure-by-assignee")).to_contain_text(text)
    expect(portal.locator("#ixs-azure-dates")).to_contain_text(text)
    assert portal.locator(", ".join(f"#{key} img" for key in IDS)).count() == 0
    assert portal.evaluate("window.injected") is None
