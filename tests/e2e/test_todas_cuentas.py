"""Todas las cuentas en un navegador real: busqueda, filtro y orden."""

import pytest
from playwright.sync_api import expect

pytestmark = pytest.mark.django_db(transaction=True)

PAGE = "/ejecutiva/cuentas/"


@pytest.fixture(autouse=True)
def accounts(monkeypatch):
    def row(name, revenue, cost, margin, kind, pending=0):
        return {
            "name": name,
            "url": f"/cuenta/{name.lower()}/?nombre={name}",
            "revenue": revenue,
            "cost": cost,
            "gross_profit": revenue - cost,
            "margin": margin,
            "projects": 2,
            "pending": pending,
            "classification": kind,
        }

    data = {
        "year": 2026,
        "accounts": [
            row("Acme", 1000000, 200000, 80.0, "healthy"),
            row("Beta", 500000, 400000, 20.0, "unhealthy"),
            row("Gamma", 300000, 100000, None, "pending", pending=2),
        ],
    }
    monkeypatch.setattr(
        "apps.portal.services.account_profitability.load_account_profitability",
        lambda: data,
    )


def test_page_uses_the_modular_frontend_and_summarises(portal, datos):
    portal.goto(portal.base + PAGE)

    expect(
        portal.get_by_role("heading", name="Todas las cuentas · 2026")
    ).to_be_visible()
    assert portal.locator("main").count() == 1
    assert portal.locator("link[href*='pages/all_accounts.css']").count() == 1
    expect(portal.locator("#account-count")).to_have_text("3 de 3 cuentas")
    expect(portal.locator("#summary-healthy")).to_have_text("1")
    expect(portal.locator("#summary-pending")).to_have_text("1")
    expect(portal.locator("#summary-margin")).to_have_text("50%")
    expect(portal.locator("td.money").first).to_have_text("1M")


def test_search_filter_and_sort(portal, datos):
    portal.goto(portal.base + PAGE)
    portal.fill("#account-search", "bet")
    expect(portal.locator("#account-count")).to_have_text("1 de 3 cuentas")
    portal.fill("#account-search", "")
    portal.select_option("#account-filter", "pending")
    expect(portal.locator("tr[data-name]:visible")).to_have_attribute(
        "data-name", "Gamma"
    )
    portal.select_option("#account-filter", "")
    portal.get_by_role("button", name="Cuenta").click()
    expect(portal.locator("tr[data-name]").first).to_have_attribute(
        "data-name", "Acme"
    )
    portal.get_by_role("button", name="Cuenta").click()
    expect(portal.locator("tr[data-name]").first).to_have_attribute(
        "data-name", "Gamma"
    )


def test_links_keep_the_way_back(portal, datos):
    portal.goto(portal.base + PAGE)
    href = portal.get_by_role("link", name="Ver costos →").first.get_attribute(
        "href"
    )
    assert "volver=" in href and "nombre=" in href
