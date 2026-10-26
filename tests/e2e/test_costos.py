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


def test_project_name_band_search_sort_and_csv(portal, monkeypatch):
    import csv
    from copy import deepcopy
    from pathlib import Path

    from apps.datastore.models import Project

    Project.objects.create(
        internal_id="AER.001", base_id="AER.001", name="Análisis Planta Norte"
    )
    summary = {
        "projects": deepcopy(PROJECTS),
        "cost": 11000,
        "complete": False,
        "pending": 1,
        "future": 1,
        "deduplicated_entries": 321,
        "band_month": "2026-10",
        "prepared_details": {
            "aer.001": deepcopy(DETAIL),
            "aer.002": {"people": [{"band": "B1"}]},
        },
    }
    monkeypatch.setattr(
        "apps.portal.services.cost_audit_cache.prepared_summary",
        lambda account: summary,
    )
    portal.goto(portal.base + PAGE)
    expect(portal.locator("#cost-total")).to_have_text("$11K")
    expect(portal.locator("#cost-audit-body")).to_contain_text(
        "Análisis Planta Norte"
    )
    portal.fill("#cost-search", "analisis planta")
    expect(portal.locator("#cost-page-label")).to_have_text(
        "Mostrando 1–1 de 1 resultados"
    )
    portal.fill("#cost-search", "")
    portal.select_option("#cost-band-filter", "A2")
    expect(portal.locator("#cost-page-label")).to_have_text(
        "Mostrando 1–1 de 1 resultados"
    )
    assert "banda=A2" in portal.url
    portal.reload()
    expect(portal.locator("#cost-band-filter")).to_have_value("A2")
    with portal.expect_download() as result:
        portal.click("#cost-export")
    records = list(
        csv.DictReader(
            Path(result.value.path())
            .read_text(encoding="utf-8-sig")
            .splitlines()
        )
    )
    assert len(records) == 1
    assert records[0]["Project ID"] == "AER.001"
    assert records[0]["Proyecto"] == "Análisis Planta Norte"
    assert records[0]["Costo (USD)"] == "8000"
    portal.select_option("#cost-band-filter", "")
    portal.locator('[data-cost-sort="cost"]').click()
    expect(portal.locator("#cost-audit-body > tr").first).to_contain_text(
        "AER.002"
    )
    portal.locator('[data-cost-sort="cost"]').click()
    expect(portal.locator("#cost-audit-body > tr").first).to_contain_text(
        "AER.001"
    )


def test_numbered_pagination_and_page_size(portal, monkeypatch):
    projects = [
        {**PROJECTS[0], "id": f"AER.{index:03d}"} for index in range(1, 22)
    ]
    monkeypatch.setattr(
        "apps.portal.services.cost_audit_cache.prepared_summary",
        lambda account: {
            "projects": projects,
            "cost": 8000,
            "complete": True,
            "pending": 0,
            "future": 0,
            "deduplicated_entries": 321,
            "band_month": "2026-10",
            "prepared_details": {},
        },
    )
    portal.goto(portal.base + PAGE)
    expect(portal.locator("#cost-page-label")).to_have_text(
        "Mostrando 1–10 de 21 resultados"
    )
    portal.get_by_role("button", name="Página 3", exact=True).click()
    expect(portal.locator("#cost-page-label")).to_have_text(
        "Mostrando 21–21 de 21 resultados"
    )
    assert "pagina=3" in portal.url
    portal.select_option("#cost-page-size", "25")
    expect(portal.locator("#cost-page-label")).to_have_text(
        "Mostrando 1–21 de 21 resultados"
    )
    expect(portal.locator("#cost-next")).to_be_disabled()
    scroll = portal.locator(".cost-scroll")
    header = scroll.locator("thead th").first
    before = header.bounding_box()["y"]
    scroll.evaluate("e => {e.scrollTop = 240;}")
    assert scroll.evaluate("e => e.scrollTop") > 0
    assert abs(header.bounding_box()["y"] - before) <= 1
    portal.reload()
    expect(portal.locator("#cost-page-size")).to_have_value("25")
    expect(portal.locator("#cost-page-label")).to_have_text(
        "Mostrando 1–21 de 21 resultados"
    )


@pytest.mark.parametrize("width", [1450, 900, 390])
def test_cost_reference_design_is_responsive(portal, width):
    from pathlib import Path

    portal.set_viewport_size({"width": width, "height": 1000})
    portal.goto(portal.base + PAGE)
    expect(portal.locator("#cost-total")).to_have_text("$11K")
    expect(portal.locator(".cost-summary article")).to_have_count(4)
    expect(portal.locator(".cost-summary")).not_to_contain_text(
        "Caché de costos"
    )
    expect(portal.locator("#cost-progress")).to_have_attribute("value", "50")
    expect(portal.locator(".cost-scroll thead th")).to_have_count(8)
    expect(portal.locator("#cost-consulted-percent")).to_have_text(
        "50.0% del total"
    )
    expect(portal.locator("#cost-pending-percent")).to_have_text(
        "25.0% del total"
    )
    assert portal.evaluate(
        "document.documentElement.scrollWidth <= window.innerWidth"
    )
    output = Path("tmp/design/costs-reference")
    output.mkdir(parents=True, exist_ok=True)
    portal.screenshot(path=str(output / f"costs-{width}.png"), full_page=True)
