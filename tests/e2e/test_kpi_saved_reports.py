"""Production KPI UI reads its own records even when provider/EVA reads fail."""

from datetime import date
from pathlib import Path
from unittest.mock import patch

import pytest
from playwright.sync_api import expect

from apps.portal.services.kpi_dm_sync import capture_current_month
from tests.portal.test_kpi_dm_store import day, project, source

pytestmark = pytest.mark.usefixtures("transactional_db", "enforced_csp")
PAGE = "/operativa/kpis-delivery-managers/"


@pytest.fixture
def saved_site(settings, monkeypatch):
    settings.ROOT_URLCONF = "config.urls"
    settings.PORTAL_LOGIN_REQUIRED = False
    settings.KPI_DM_AUTO_UPDATE_ENABLED = False
    day(monkeypatch, date(2026, 10, 29))
    run = source(date(2026, 10, 29))
    rows = [
        project("A", "Ana", -1, 150),
        project("B", "Ana", 1, None),
        project("C", "Beto", 0, 100),
    ]
    with patch(
        "apps.portal.services.kpi_dm_sync.inventory_rows",
        return_value=(run, rows),
    ):
        capture_current_month()

    def forbidden(*args, **kwargs):
        raise AssertionError("KPI page must use its saved tables only")

    monkeypatch.setattr(
        "apps.portal.services.summary_inventory.inventory_rows", forbidden
    )
    monkeypatch.setattr(
        "apps.portal.services.eva_inventory_view.load_inventory_eva", forbidden
    )
    Path("tmp/design/kpi-saved").mkdir(parents=True, exist_ok=True)


@pytest.mark.parametrize("width", [1450, 900, 390])
def test_saved_kpis_keep_layout_and_only_actual_month_has_values(
    page, live_server, saved_site, width
):
    page.set_viewport_size({"width": width, "height": 1000})
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.goto(live_server.url + PAGE)
    expect(page.locator("#kpi-cut")).to_have_value("2026-10-29")
    expect(page.locator(".two table tbody tr")).to_have_count(2)
    expect(page.locator(".two table tbody tr").first).to_contain_text("50%")
    expect(
        page.locator("#kpi-month-history thead tr").first.locator(
            "[colspan='3']"
        )
    ).to_have_count(12)
    first = page.locator("#kpi-month-history tbody tr").first
    expect(first.locator("td").first).to_have_text("—")
    expect(page.locator("#kpi-chart circle")).to_have_count(2)
    for path in page.locator("#kpi-chart path[stroke-width='2.5']").all():
        assert "C" not in path.get_attribute("d")
        assert "L" not in path.get_attribute("d")
    expect(page.locator("#kpis-notice")).to_contain_text("Meses sin datos KPI")
    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
    page.screenshot(
        path=f"tmp/design/kpi-saved/saved-{width}.png", full_page=True
    )
    assert errors == []


def test_global_filter_and_missing_date_do_not_reconstruct_from_eva(
    page, live_server, saved_site
):
    page.goto(live_server.url + PAGE)
    page.locator("#kpi-global-dms summary").click()
    page.get_by_role("checkbox", name="Beto", exact=True).uncheck()
    page.get_by_role("button", name="Aplicar DMs").click()
    expect(page.locator(".two table tbody tr")).to_have_count(1)
    expect(page.locator("#kpi-month-history tbody tr")).to_have_count(1)
    expect(page.locator("#kpi-quarter-history tbody tr")).to_have_count(1)
    expect(page.locator("#kpi-legend button")).to_have_count(1)
    page.locator("#kpi-cut").fill("2026-10-28")
    page.get_by_role("button", name="Consultar corte").click()
    expect(page.locator("#kpis-notice")).to_contain_text(
        "No hay una captura KPI guardada"
    )
    expect(page.locator(".kp .kc").nth(1).locator(".kv")).to_have_text("—")
    expect(page.locator("#kpi-month-history tbody tr")).to_have_count(1)
