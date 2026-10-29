"""Frozen closes and missing historical months are explicit in the UI."""

from datetime import date
from pathlib import Path

import pytest
from playwright.sync_api import expect

from apps.datastore.models import EvaMonthlyClosePolicy
from apps.portal.services.eva_monthly_closes import close_due_months
from tests.portal.test_eva_monthly_closes import CUT, observed, today

pytestmark = pytest.mark.usefixtures("transactional_db", "enforced_csp")


@pytest.fixture
def closed_site(settings, monkeypatch):
    settings.EVA_MONTHLY_CLOSES_ENABLED = True
    Path("tmp/eva-native").mkdir(parents=True, exist_ok=True)
    settings.ROOT_URLCONF = "config.urls"
    settings.PORTAL_LOGIN_REQUIRED = False
    today(monkeypatch, date(2026, 10, 30))
    EvaMonthlyClosePolicy.objects.update_or_create(
        pk=1, defaults={"first_month": date(2026, 10, 1)}
    )
    observed()
    close_due_months()
    observed(date(2026, 10, 30), "Otro DM", "2026-12-31")


@pytest.mark.parametrize("width", [1450, 390])
def test_monthly_close_stays_fixed_and_current_dates_keep_updating(
    page, live_server, closed_site, width
):
    page.set_viewport_size({"width": width, "height": 950})
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.goto(live_server.url + f"/operativa/eva-1/?corte={CUT.isoformat()}")
    expect(page.locator('.note[role="status"]')).to_contain_text(
        "Cierre mensual fijo"
    )
    row = page.locator("#eva-table tbody tr[data-manager]")
    expect(row).to_have_count(1)
    expect(row).to_contain_text("Ana")
    expect(row).to_contain_text("31/10/26")
    assert "Otro DM" not in row.inner_text()
    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
    page.screenshot(
        path=f"tmp/eva-native/monthly-close-{width}.png", full_page=True
    )
    page.goto(live_server.url + "/operativa/eva-1/?corte=2026-10-30")
    expect(page.locator("#eva-table tbody tr[data-manager]")).to_contain_text(
        "Otro DM"
    )
    assert errors == []


def test_unvalidated_past_close_is_pending_instead_of_zero_projects(
    page, live_server, closed_site
):
    page.goto(live_server.url + "/operativa/eva-1/?corte=2026-09-30")
    expect(page.locator('.note[role="status"]')).to_contain_text(
        "pendiente de validar/cargar"
    )
    expect(page.locator("#eva-count")).to_have_text(
        "Sin cierre mensual validado"
    )
    expect(page.locator(".kp4 .kv").first).to_have_text("—")
    expect(page.locator("#eva-table tbody tr[data-manager]")).to_have_count(0)
    page.goto(
        live_server.url + "/operativa/kpis-delivery-managers/?corte=2026-10-29"
    )
    expect(page.locator("#kpi-month-history tbody tr")).to_have_count(0)
    headers = page.locator("#kpi-month-history thead tr").first.inner_text()
    assert "OCT" in headers.upper() and "OCT*" not in headers.upper()


def test_deferred_feature_restores_normal_eva_reads(
    page, live_server, closed_site, settings
):
    settings.EVA_MONTHLY_CLOSES_ENABLED = False
    page.goto(live_server.url + "/operativa/eva-1/?corte=2026-10-29")
    expect(page.locator('.note[role="status"]')).to_contain_text(
        "desactivada hasta Genesis"
    )
    expect(page.locator("#eva-table tbody tr[data-manager]")).to_contain_text(
        "Otro DM"
    )
