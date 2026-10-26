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
    expect(portal.locator("td.money").first).to_have_text("$1M")


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


def test_state_filters_reset_and_restore(portal, datos):
    portal.goto(portal.base + PAGE)
    portal.select_option("#account-state", "partial")
    expect(portal.locator("tr[data-name]:visible")).to_have_attribute(
        "data-name", "Gamma"
    )
    expect(portal.locator("#summary-healthy-percent")).to_have_text(
        "33.3% del total"
    )
    portal.reload()
    expect(portal.locator("#account-state")).to_have_value("partial")
    expect(portal.locator("#account-count")).to_have_text("1 de 3 cuentas")
    portal.get_by_role("button", name="Limpiar filtros").click()
    expect(portal.locator("#account-count")).to_have_text("3 de 3 cuentas")
    expect(portal.locator("#account-state")).to_have_value("")


def test_pagination_and_return_context(portal, datos, monkeypatch):
    from urllib.parse import parse_qs, urlparse

    data = {
        "year": 2026,
        "accounts": [
            {
                "name": f"Cuenta {n:02d}",
                "url": f"/cuenta/cuenta-{n}/?nombre=Cuenta{n}",
                "revenue": n * 1000,
                "cost": n * 100,
                "gross_profit": n * 900,
                "margin": 90,
                "projects": 2,
                "pending": 0,
                "classification": "healthy",
            }
            for n in range(1, 33)
        ],
    }
    monkeypatch.setattr(
        "apps.portal.services.account_profitability.load_account_profitability",
        lambda: data,
    )
    portal.goto(portal.base + PAGE)
    expect(portal.locator("tr[data-name]:visible")).to_have_count(15)
    portal.get_by_role("button", name="Página 2", exact=True).click()
    expect(portal.locator("#accounts-page-label")).to_have_text(
        "Mostrando 16–30 de 32 cuentas"
    )
    href = portal.locator(
        "tr[data-name]:visible .detail-link"
    ).first.get_attribute("href")
    back = parse_qs(urlparse(href).query)["volver"][0]
    assert parse_qs(urlparse(back).query)["pagina"] == ["2"]
    portal.reload()
    expect(portal.locator("#accounts-page-label")).to_have_text(
        "Mostrando 16–30 de 32 cuentas"
    )
    portal.select_option("#accounts-page-size", "25")
    expect(portal.locator("tr[data-name]:visible")).to_have_count(25)
    portal.get_by_role("button", name="Página siguiente", exact=True).click()
    expect(portal.locator("tr[data-name]:visible")).to_have_count(7)


@pytest.mark.parametrize("width", [1450, 900, 390])
def test_reference_layout_is_responsive(
    portal, datos, width, monkeypatch, enforced_csp
):
    from datetime import datetime
    from pathlib import Path

    monkeypatch.setattr(
        "django.utils.timezone.now",
        lambda: datetime.fromisoformat("2026-10-26T18:00:00+00:00"),
    )
    portal.set_viewport_size({"width": width, "height": 1000})
    portal.goto(portal.base + PAGE)
    expect(portal.locator(".account-avatar")).to_have_count(3)
    expect(portal.locator("#summary-margin")).to_have_text("50%")
    assert portal.evaluate("document.documentElement.scrollWidth <= innerWidth")
    target = Path("tmp/design/all-accounts-reference")
    target.mkdir(parents=True, exist_ok=True)
    portal.screenshot(
        path=str(target / f"accounts-{width}.png"), full_page=True
    )


def test_account_action_menu_keeps_return_context(portal, datos):
    from urllib.parse import parse_qs, urlparse

    portal.goto(portal.base + PAGE + "?buscar=Acme")
    menu = portal.locator("tr[data-name='Acme'] .account-row-menu")
    menu.locator("summary").click()
    expect(menu.get_by_role("link", name="Abrir cuenta")).to_be_visible()
    link = menu.get_by_role("link", name="Ver detalle de costos")
    expect(link).to_be_visible()
    back = parse_qs(urlparse(link.get_attribute("href")).query)["volver"][0]
    assert parse_qs(urlparse(back).query)["buscar"] == ["Acme"]
    portal.keyboard.press("Escape")
    expect(menu.get_by_role("link", name="Abrir cuenta")).to_be_hidden()


def test_saved_previous_link_retains_search_and_modular_controls(portal, datos):
    portal.goto(portal.base + PAGE + "?vista=anterior&buscar=Acme")
    expect(portal.locator("#account-search")).to_have_value("Acme")
    expect(portal.locator("tr[data-name]:visible")).to_have_count(1)
    expect(
        portal.locator('script[src*="pages/all_accounts/main.js"]')
    ).to_have_count(1)
