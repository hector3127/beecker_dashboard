"""Real route and CSP verification for local Summary searches."""

from datetime import date
from pathlib import Path

import pytest
from playwright.sync_api import expect

from tests.portal import test_summary_inventory as fixtures

inventory = fixtures.inventory

pytestmark = [pytest.mark.usefixtures("transactional_db", "enforced_csp")]


def test_persisted_metrics_render_without_provider_calls(
    page, live_server, settings, inventory
):
    from apps.portal.services.summary_eva_metrics import enrich

    settings.ROOT_URLCONF = "config.urls"
    settings.PORTAL_LOGIN_REQUIRED = False
    source = inventory.evaazuresource_set.get(azure_id="one")
    block = source.evascopesnapshot_set.get(scope="S2")
    rows = [block.row]
    evidence = enrich(
        rows, source.payload["summary"], [], True, None, date(2026, 6, 1)
    )
    rows[0]["eva_metrics"]["clockify_project_id"] = "provider"
    evidence.update(
        observed_date="2026-06-01",
        clockify={
            "provider": [
                {
                    "id": "one",
                    "billable": True,
                    "taskName": "Discovery_S2",
                    "timeInterval": {
                        "start": "2026-06-01T16:00:00Z",
                        "duration": 3600,
                    },
                }
            ]
        },
    )
    block.row = rows[0]
    block.save()
    source.payload["summary"]["eva_evidence"] = evidence
    source.save()
    page.goto(live_server.url + "/operativa/eva-1/summary/?corte=2026-06-01")
    cells = page.locator("#summary-projects-table tbody tr").first.locator("td")
    expect(cells.nth(9)).to_have_text("1")
    expect(cells.nth(10)).to_have_text("19")
    expect(cells.nth(11)).to_have_text("0")
    expect(cells.nth(12)).to_have_text("5%")
    expect(cells.nth(13)).to_have_text("0")
    expect(cells.nth(25)).to_have_text("Sin riesgos activos")


@pytest.mark.parametrize("width", [390, 900, 1450])
def test_summary_search_responsive(
    page, live_server, settings, inventory, width
):
    settings.ROOT_URLCONF = "config.urls"
    settings.PORTAL_LOGIN_REQUIRED = False
    page.set_viewport_size({"width": width, "height": 950})
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.goto(live_server.url + "/operativa/eva-1/summary/?corte=2026-06-01")
    expect(page.locator("#summary-projects-table tbody tr")).to_have_count(1)
    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
    page.get_by_label(
        "Buscar proyecto, ID, sprint, CR o Delivery Manager"
    ).fill("S2")
    page.get_by_role("button", name="Consultar corte", exact=True).click()
    expect(page.locator("#summary-projects-table tbody tr")).to_have_count(1)
    expect(page.locator("#summary-projects-table tbody")).to_contain_text(
        "AMK.012_S2"
    )
    expect(page.locator("#summary-projects-table tbody")).to_contain_text(
        "2026-06-22"
    )
    expect(page.locator("#summary-dm-table tbody tr")).to_have_count(1)
    expect(page.locator("#summary-dm-table tfoot td").last).to_have_text("1")
    expect(page.locator("#summary-projects-table tbody")).to_contain_text(
        "Development"
    )
    expect(page.locator("#summary-projects-table thead")).not_to_contain_text(
        "Estado Azure"
    )
    page.get_by_label("Fecha de corte", exact=True).fill("2026-06-23")
    page.get_by_role("button", name="Consultar corte", exact=True).click()
    expect(page.locator("#summary-projects-table tbody")).not_to_contain_text(
        "AMK.012_S2"
    )
    expect(page.locator("#summary-dm-table tfoot td").last).to_have_text("0")
    page.get_by_label("Fecha de corte", exact=True).fill("2026-06-01")
    page.get_by_role("button", name="Consultar corte", exact=True).click()
    expect(page.locator("#summary-projects-table tbody")).to_contain_text(
        "AMK.012_S2"
    )
    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
    output = Path("tmp/summary-inventory")
    output.mkdir(parents=True, exist_ok=True)
    page.screenshot(path=str(output / f"summary-{width}.png"), full_page=True)
    assert errors == []
