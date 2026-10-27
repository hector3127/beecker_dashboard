"""Arranque explícito y reintento sin redeclarar el script anterior."""

from pathlib import Path

import pytest
from playwright.sync_api import expect

from tests.e2e.test_aer_executive import fixed_day as fixed_day
from tests.e2e.test_ixs_executive import ixs as ixs
from tests.e2e.test_project_detail_entry import project_detail as project_detail

pytestmark = pytest.mark.django_db(transaction=True)
RENDERER = "**/portal/js/proyecto_detalle.js?*"
SHIM = "**/core/js/gas_shim.js"
SOURCE = Path("tests/reference/static/portal/js/proyecto_detalle.js")


@pytest.mark.parametrize("family", ["ixs", "aer"])
def test_main_mounts_without_old_entry_functions(
    portal, project_detail, family
):
    data = project_detail[1 if family == "aer" else 0]
    source = SOURCE.read_text(encoding="utf-8")
    for signature in (
        "function renderView(viewName) {",
        "function projectEntryContext(){",
        "function initDashboard(previous) {",
    ):
        assert signature in source
        source = source.replace(
            signature, signature + "throw Error('old startup called');", 1
        )
    portal.route(
        RENDERER,
        lambda route: route.fulfill(
            body=source, content_type="application/javascript"
        ),
    )
    errors, urls = [], []
    portal.on("pageerror", lambda error: errors.append(str(error)))
    portal.on("request", lambda request: urls.append(request.url))
    id = data["proyecto"]["id"]
    portal.goto(f"{portal.base}/proyectos/{id}/")
    expect(
        portal.locator(".aer-title" if family == "aer" else ".ixs-title")
    ).to_contain_text(id)
    portal.wait_for_load_state("networkidle")
    endpoint = f"/{id}/{'aer' if family == 'aer' else 'ejecutivo'}/"
    assert sum(endpoint in url for url in urls) == 1
    assert not any(
        "proyecto_detalle.js" in url or "gas_shim.js" in url for url in urls
    )
    assert not errors, errors


@pytest.mark.parametrize("family", ["aer", "ixs"])
def test_source_retry_is_independent_of_failed_old_scripts(
    portal, project_detail, family
):
    attempts, scripts = [], []
    data = project_detail[1 if family == "aer" else 0]
    identifier = data["proyecto"]["id"]
    endpoint = "aer" if family == "aer" else "ejecutivo"

    def old(route):
        scripts.append(route.request.url)
        route.abort()

    def source(route):
        attempts.append(route.request.url)
        if len(attempts) == 1:
            route.fulfill(
                status=503,
                json={
                    "error": {"code": "source", "message": "Fuente temporal"}
                },
            )
        else:
            route.fallback()

    portal.route(RENDERER, old)
    portal.route(SHIM, old)
    portal.route(f"**/proyectos/{identifier}/{endpoint}/", source)
    portal.goto(portal.base + f"/proyectos/{identifier}/")
    expect(portal.locator("#view-container")).to_contain_text("Fuente temporal")
    portal.get_by_role("button", name="Reintentar", exact=True).click()
    expect(portal.locator(".aer-head, .ixs-head")).to_be_visible()
    assert len(attempts) == 2
    assert not scripts


def test_reload_keeps_state_without_loading_any_old_definitions(portal, ixs):
    scripts = []

    def renderer(route):
        scripts.append(route.request.url)
        route.abort()

    portal.route(RENDERER, renderer)
    portal.route(SHIM, renderer)
    errors = []
    portal.on("pageerror", lambda error: errors.append(str(error)))
    portal.goto(portal.base + "/proyectos/AMK.008/")
    expect(portal.locator(".ixs-head")).to_be_visible()
    assert not scripts
    portal.evaluate("beeProjectState.clockify.sentinel='preserved'")
    portal.locator(".ixs-head button").first.click()
    expect(portal.locator(".ixs-head")).to_be_visible()
    assert portal.evaluate("beeProjectState.clockify.sentinel") == "preserved"
    assert not scripts
    assert not errors, errors
