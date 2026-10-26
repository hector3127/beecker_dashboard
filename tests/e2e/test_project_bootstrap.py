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
SOURCE = Path("apps/portal/static/portal/js/proyecto_detalle.js")


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
    assert not errors, errors


@pytest.mark.parametrize("failed", ["shim", "renderer"])
def test_failed_script_download_can_retry(portal, ixs, failed):
    counts = {"shim": 0, "renderer": 0}

    def intercept(route):
        kind = (
            "renderer" if "proyecto_detalle.js" in route.request.url else "shim"
        )
        counts[kind] += 1
        if kind == failed and counts[kind] == 1:
            route.fulfill(
                status=503, body="", content_type="application/javascript"
            )
        else:
            route.fallback()

    portal.route(RENDERER, intercept)
    portal.route(SHIM, intercept)
    errors = []
    portal.on("pageerror", lambda error: errors.append(str(error)))
    portal.goto(portal.base + "/proyectos/AMK.008/")
    expect(
        portal.get_by_role("button", name="Reintentar", exact=True)
    ).to_be_visible()
    portal.get_by_role("button", name="Reintentar", exact=True).click()
    expect(portal.locator(".ixs-head")).to_be_visible()
    assert counts == {
        "shim": 2 if failed == "shim" else 1,
        "renderer": 2 if failed == "renderer" else 1,
    }
    assert not errors, errors


def test_retry_after_evaluation_keeps_loaded_script_and_lexical_state(
    portal, ixs
):
    scripts = []
    source = (
        SOURCE.read_text(encoding="utf-8")
        + """
    window.testProjectBindings=projectCompatibilityBindings;
    projectCompatibilityBindings=function(){
      if(!window.testProjectBridgeFailed){
        window.testProjectBridgeFailed=true;
        throw Error('one failed bridge setup');
      }
      return window.testProjectBindings();
    };
    """
    )

    def renderer(route):
        scripts.append(route.request.url)
        route.fulfill(body=source, content_type="application/javascript")

    portal.route(RENDERER, renderer)
    errors = []
    portal.on("pageerror", lambda error: errors.append(str(error)))
    portal.goto(portal.base + "/proyectos/AMK.008/")
    expect(
        portal.get_by_role("button", name="Reintentar", exact=True)
    ).to_be_visible()
    portal.get_by_role("button", name="Reintentar", exact=True).click()
    expect(portal.locator(".ixs-head")).to_be_visible()
    assert len(scripts) == 1
    assert not errors, errors
