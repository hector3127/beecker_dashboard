"""Agrupaciones Azure: misma presentación, acciones y texto seguro."""

import copy

import pytest
from playwright.sync_api import expect

from tests.e2e.test_aer_executive import fixed_day as fixed_day
from tests.e2e.test_ixs_azure_transport import enter
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


def open_drawer(portal, mode):
    if mode == "iteration":
        person = portal.locator(".ixs-az85-person").first
        person.locator("summary").click()
        person.locator("tbody button").first.click()
    elif mode == "stage":
        portal.locator("#ixs-az84-stage tbody button").first.click()
    else:
        portal.locator(".ixs-az85-person summary button").first.click()


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
