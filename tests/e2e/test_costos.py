"""Detalle de costos por proyecto en un navegador real."""

import pytest
from playwright.sync_api import expect

pytestmark = pytest.mark.django_db(transaction=True)

PAGE = "/ejecutiva/costos/detalle/?vista=proyectos"
PROJECTS = [
    {
        "id": "AER.001",
        "hours": 120.5,
        "cost": 8000,
        "revenue": 20000,
        "margin": 60,
        "gross_profit": 12000,
        "complete": True,
    },
    {
        "id": "AER.002",
        "hours": 40,
        "cost": 3000,
        "revenue": 3500,
        "margin": 14.2,
        "gross_profit": 500,
        "complete": False,
        "margin_provisional": True,
    },
    {
        "id": "AER.003",
        "hours": None,
        "cost": None,
        "revenue": None,
        "margin": None,
        "gross_profit": None,
        "complete": False,
        "error": "Consulta pendiente",
    },
    {
        "id": "AER.004",
        "hours": None,
        "cost": None,
        "revenue": 500,
        "margin": None,
        "gross_profit": None,
        "complete": False,
        "future": True,
    },
]
DETAIL = {
    "id": "AER.001",
    "hours": 120.5,
    "cost": 8000,
    "revenue": 20000,
    "margin": 60,
    "gross_profit": 12000,
    "complete": True,
    "clockify_id": "AER.001",
    "scope_start": "2026-01-01",
    "scope_end": "2026-10-22",
    "people": [
        {
            "name": "Ana",
            "hours": 100,
            "band": "A2",
            "band_month": "2026-10",
            "rate": 20,
            "cost": 2000,
        }
    ],
    "sprints": [],
}


@pytest.fixture(autouse=True)
def sources(monkeypatch, datos):
    summary = {
        "projects": PROJECTS,
        "cost": 11000,
        "complete": False,
        "pending": 1,
        "future": 1,
        "deduplicated_entries": 321,
        "band_month": "2026-10",
        "prepared_details": {},
    }
    monkeypatch.setattr(
        "apps.portal.services.executive_refresh.request_refresh",
        lambda **kwargs: {"state": "idle"},
    )
    monkeypatch.setattr(
        "apps.portal.services.cost_audit_cache.prepared_summary",
        lambda account: summary,
    )
    monkeypatch.setattr(
        "apps.portal.services.cost_audit_cache.prepared_detail",
        lambda pid, account: DETAIL,
    )


def test_summary_and_rows_use_the_modular_page(portal):
    portal.goto(portal.base + PAGE)

    expect(portal.locator("#cost-total")).to_have_text("$11K")
    expect(portal.locator("#cost-consulted")).to_have_text("2 de 4")
    assert portal.locator("main").count() == 1
    assert portal.locator("link[href*='pages/costs.css']").count() == 1
    rows = portal.locator("#cost-audit-body > tr:not(.audit-detail-row)")
    expect(rows).to_have_count(4)
    expect(rows.nth(0)).to_contain_text("60%")
    expect(rows.nth(1)).to_contain_text("14.2%*")
    expect(rows.nth(1)).to_contain_text("Costo parcial")
    expect(rows.nth(3)).to_contain_text("Futuro")


def test_filter_and_unavailable_project_notice(portal):
    portal.goto(portal.base + PAGE)
    portal.select_option("#cost-filter", "pending")
    expect(
        portal.locator("#cost-audit-body > tr:not(.audit-detail-row)")
    ).to_have_count(1)
    portal.locator("[data-project-unavailable]").click()
    expect(portal.locator("#cost-project-notice")).to_contain_text("AER.003")
    expect(portal.locator("#cost-project-notice")).to_contain_text(
        "Consulta pendiente"
    )


def test_people_breakdown_opens_and_closes(portal):
    portal.goto(portal.base + PAGE)
    button = portal.locator("[data-persons='AER.001']")
    button.click()
    detail = portal.locator(".audit-detail").first
    expect(detail).to_contain_text("Ana")
    expect(detail).to_contain_text("$20.00")
    expect(button).to_have_text("Ocultar detalle")
    button.click()
    expect(button).to_have_text("Ver personas y tarifas")


def test_a_project_link_keeps_the_way_back(portal):
    portal.goto(portal.base + PAGE)
    href = portal.get_by_role(
        "link", name="Ver proyecto AER.001"
    ).get_attribute("href")
    assert href.startswith("/proyectos/AER.001/") and "volver=" in href
