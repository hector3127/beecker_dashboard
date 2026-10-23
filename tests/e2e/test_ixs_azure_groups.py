"""Agrupaciones Azure: misma presentación, acciones y texto seguro."""

import copy
import json
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
GROUPS = (
    "#ixs-az84-person, #ixs-az84-person *, #ixs-az84-stage, #ixs-az84-stage *"
)


@pytest.fixture
def groups(planning):
    _, azure, _, _ = planning
    base = azure["items"][0]
    azure["allItems"] = [
        {
            **base,
            "id": 100 + i,
            "titulo": f"AMK.008 · Tarea {i}",
            "estado": state,
            "asignadoA": ["Ana Pérez", "Luis", "", "Ana Pérez"][i % 4],
            "iterationPath": [
                "AMK\\Development",
                "AMK\\QA",
                "",
                "OTRO\\Development",
            ][i % 4],
        }
        for i, state in enumerate(
            [
                "Active",
                "Closed",
                "Blocked",
                "Proposed",
                "Cancelled",
                "In progress",
                "Rejected",
                "Completed",
                "Active",
            ]
        )
    ]
    return azure


@pytest.mark.parametrize("width", [1450, 900, 390])
@pytest.mark.parametrize("variant", ["full", "empty", "notice"])
def test_groups_match_previous(portal, groups, fixed_day, width, variant):
    if variant == "empty":
        groups["allItems"] = []
    if variant == "notice":
        groups["aviso"] = "Datos del último corte disponible"
    portal.set_viewport_size({"width": width, "height": 1000})
    directory = (
        Path("tmp/migration/project_detail/ixs_azure_groups")
        / variant
        / str(width)
    )
    directory.mkdir(parents=True, exist_ok=True)
    states = []
    for previous in [True, False]:
        enter(portal, previous)
        portal.wait_for_load_state("networkidle")
        if variant != "empty":
            portal.locator(".ixs-az85-person > summary").first.click()
            portal.wait_for_function(
                "getComputedStyle(document.querySelector("
                "'.ixs-az85-person[open] .ixs-az85-chev')).transform "
                "=== 'matrix(0, 1, -1, 0, 0, 0)'"
            )
        portal.mouse.move(0, 0)
        states.append(capture_state(portal, GROUPS))
        portal.screenshot(
            path=str(directory / ("old.png" if previous else "new.png")),
            full_page=True,
        )
    (directory / "states.json").write_text(json.dumps(states), encoding="utf-8")
    assert states[0] == states[1]
    assert (
        portal.locator(
            "#ixs-az84-person [onclick], #ixs-az84-person [oninput], "
            "#ixs-az84-stage [onclick]"
        ).count()
        == 0
    )


def open_drawer(portal, mode):
    if mode == "iteration":
        person = portal.locator(".ixs-az85-person").first
        person.locator("summary").click()
        person.locator("tbody button").first.click()
    elif mode == "stage":
        portal.locator("#ixs-az84-stage tbody button").first.click()
    else:
        portal.locator(".ixs-az85-person summary button").first.click()


@pytest.mark.parametrize("width", [1450, 900, 390])
@pytest.mark.parametrize("mode", ["person", "iteration", "stage"])
def test_drawers_match_previous(portal, groups, fixed_day, width, mode):
    portal.set_viewport_size({"width": width, "height": 1000})
    states = []
    directory = (
        Path("tmp/migration/project_detail/ixs_azure_groups")
        / mode
        / str(width)
    )
    directory.mkdir(parents=True, exist_ok=True)
    for previous in [True, False]:
        enter(portal, previous)
        portal.wait_for_load_state("networkidle")
        open_drawer(portal, mode)
        expect(portal.locator(".ixs-az84-drawer")).to_be_visible()
        portal.mouse.move(0, 0)
        states.append(
            capture_state(
                portal, "#ixs-az84-drawer-wrap, #ixs-az84-drawer-wrap *"
            )
        )
        portal.screenshot(
            path=str(directory / ("old.png" if previous else "new.png")),
            full_page=True,
        )
        portal.keyboard.press("Escape")
        expect(portal.locator("#ixs-az84-drawer-wrap")).to_have_count(0)
    (directory / "states.json").write_text(json.dumps(states), encoding="utf-8")
    assert states[0] == states[1]


def test_search_opens_matching_people_and_keeps_current_behavior(
    portal, groups, fixed_day
):
    enter(portal)
    search = portal.get_by_role("searchbox", name="Buscar persona o iteración")
    search.fill(" QA ")
    expect(portal.locator(".ixs-az85-person:visible")).to_have_count(1)
    expect(portal.locator(".ixs-az85-person:visible")).to_contain_text("Luis")
    expect(portal.locator(".ixs-az85-person:visible")).to_have_attribute(
        "open", ""
    )
    search.fill("PÉREZ")
    expect(portal.locator(".ixs-az85-person:visible")).to_have_count(1)
    search.fill("perez")
    expect(portal.locator(".ixs-az85-person:visible")).to_have_count(0)
    search.fill("")
    expect(portal.locator(".ixs-az85-person:visible")).to_have_count(3)


@pytest.mark.parametrize("method", ["button", "backdrop"])
def test_drawer_closes_without_inline_handlers(
    portal, groups, fixed_day, method
):
    enter(portal)
    portal.wait_for_load_state("networkidle")
    open_drawer(portal, "person")
    assert portal.locator("#ixs-az84-drawer-wrap [onclick]").count() == 0
    if method == "button":
        portal.get_by_role("button", name="Cerrar", exact=True).click()
    else:
        portal.locator("#ixs-az84-drawer-wrap").dispatch_event("click")
    expect(portal.locator("#ixs-az84-drawer-wrap")).to_have_count(0)


def test_group_text_is_not_html(portal, groups, fixed_day):
    text = '<img src=x onerror="window.injected=1">'
    groups["allItems"] = [
        {
            **copy.deepcopy(groups["items"][0]),
            "asignadoA": text,
            "titulo": text,
            "iterationPath": "AMK\\" + text,
        }
    ]
    groups["aviso"] = text
    enter(portal)
    expect(portal.locator("#ixs-az84-person")).to_contain_text(text)
    assert (
        portal.locator("#ixs-az84-person img, #ixs-az84-stage img").count() == 0
    )
    open_drawer(portal, "person")
    expect(portal.locator(".ixs-az84-drawer")).to_contain_text(text)
    assert portal.locator(".ixs-az84-drawer img").count() == 0
    assert portal.evaluate("window.injected") is None
