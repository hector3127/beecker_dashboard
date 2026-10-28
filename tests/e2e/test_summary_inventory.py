"""Real route and CSP verification for local Summary searches."""

from pathlib import Path

import pytest
from playwright.sync_api import expect

from tests.portal import test_summary_inventory as fixtures

inventory = fixtures.inventory

pytestmark = [pytest.mark.usefixtures("transactional_db", "enforced_csp")]


@pytest.mark.parametrize("width", [390, 900, 1450])
def test_summary_search_responsive(
    page, live_server, settings, inventory, width
):
    settings.ROOT_URLCONF = "config.urls"
    settings.PORTAL_LOGIN_REQUIRED = False
    page.set_viewport_size({"width": width, "height": 950})
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.goto(live_server.url + "/operativa/eva-1/summary/")
    expect(page.locator("tbody tr")).to_have_count(4)
    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
    page.get_by_label(
        "Buscar proyecto, ID, sprint, CR o Delivery Manager"
    ).fill("S2")
    page.get_by_role("button", name="Buscar", exact=True).click()
    expect(page.locator("tbody tr")).to_have_count(1)
    expect(page.locator("tbody")).to_contain_text("AMK.012_S2")
    expect(page.locator("tbody")).to_contain_text("2026-06-22")
    output = Path("tmp/summary-inventory")
    output.mkdir(parents=True, exist_ok=True)
    page.screenshot(path=str(output / f"summary-{width}.png"), full_page=True)
    assert errors == []
