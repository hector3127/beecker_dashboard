"""Delivery Manager en un navegador real: pasos, tabla, horas y regreso."""

import re

import pytest
from playwright.sync_api import expect

pytestmark = pytest.mark.django_db(transaction=True)

PAGE = "/operativa/delivery-manager/alberto/?nombre=Alberto"
HOURS = "apps.portal.services.operational_sources.manager_monthly_history"


def month(label, billable, operational, commercial):
    projects = [
        {
            "id": "2",
            "name": "Portal Pacientes",
            "client": "Clinica Sur",
            "service": "T&M",
            "project_budget": 100,
            "billable": billable,
            "operational": operational,
            "commercial": commercial,
            "total": billable + operational + commercial,
        },
        {
            "id": "3",
            "name": "=HIS",
            "client": "",
            "service": "AER",
            "project_budget": None,
            "billable": 1,
            "operational": 0,
            "commercial": 0,
            "total": 1,
        },
    ]
    return {
        "label": label,
        "total": sum(p["total"] for p in projects),
        "budget": 60,
        "budget_missing": 1,
        "billable": billable + 1,
        "operational": operational,
        "commercial": commercial,
        "projects": projects,
    }


@pytest.fixture
def hours(monkeypatch):
    data = {
        "monthly": [
            month("Septiembre 2026", 20, 4, 2),
            month("Octubre 2026", 30, 5, 3),
        ],
        "complete": True,
        "error": "",
        "monthly_has_data": True,
    }
    monkeypatch.setattr(HOURS, lambda *a, **k: data)


def test_page_fills_by_steps_with_the_previous_layout(portal, datos, hours):
    portal.goto(portal.base + PAGE)

    expect(
        portal.get_by_role("heading", name="Alberto", exact=True)
    ).to_be_visible()
    expect(portal.locator(".sub")).to_have_text(
        "Delivery Manager · 2 proyectos asignados"
    )
    assert portal.locator("main").count() == 1
    assert portal.locator("#dm-kpis .kc").count() == 6
    table = portal.locator("#dm-table table")
    expect(table).to_contain_text("Portal Pacientes")
    expect(table.locator("th")).to_have_count(15)
    expect(portal.locator("#dm-table tr.rs")).to_have_count(2)
    expect(portal.locator("#hours-chart")).to_be_visible()


def test_links_carry_the_way_back(portal, datos, hours):
    portal.goto(portal.base + PAGE)
    link = (
        portal.locator("#dm-table")
        .get_by_role("link", name="Portal Pacientes")
        .first
    )
    link.click()

    portal.wait_for_url(re.compile(r"/proyectos/2/\?volver="))
    assert "delivery-manager%2Falberto" in portal.url


def test_month_detail_opens_filters_and_downloads_a_safe_csv(
    portal, datos, hours
):
    portal.goto(portal.base + PAGE)
    portal.locator("#hours-chart g[role=button]").last.click()

    dialog = portal.locator("#hours-modal")
    expect(dialog).to_be_visible()
    expect(portal.locator("#hours-modal-title")).to_have_text(
        "Detalle de horas · Octubre 2026"
    )
    expect(portal.locator("#hours-projects tr")).to_have_count(2)

    portal.select_option("#hours-month", "0")
    expect(portal.locator("#hours-modal-title")).to_contain_text("Septiembre")

    with portal.expect_download() as download:
        portal.click("#hours-download")
    text = open(download.value.path(), encoding="utf-8-sig").read()
    assert text.splitlines()[0].startswith('"ID","Proyecto"')
    assert '"\'=HIS"' in text  # una formula del Sheet no se ejecuta en Excel

    portal.click("#hours-close")
    expect(dialog).to_be_hidden()


def test_clockify_failure_keeps_the_rest_of_the_page(
    portal, datos, monkeypatch
):
    monkeypatch.setattr(
        HOURS,
        lambda *a, **k: {
            "monthly": [],
            "complete": False,
            "error": "Sin respuesta.",
            "monthly_has_data": False,
        },
    )
    portal.goto(portal.base + PAGE)

    expect(portal.locator("#dm-monthly")).to_contain_text(
        "No se pudo completar la consulta de Clockify. Sin respuesta."
    )
    expect(portal.locator("#dm-table table")).to_contain_text("HIS")
    expect(portal.locator("#hours-detail")).to_have_count(0)


def test_sources_down_goes_back_to_operativa(portal, datos):
    portal.route(
        "**/api/v1/screens/delivery-managers/**",
        lambda route: route.fulfill(
            status=502,
            content_type="application/json",
            body='{"error":{"code":"upstream","message":"Sin fuentes"}}',
        ),
    )
    portal.goto(portal.base + PAGE)

    portal.wait_for_url(re.compile(r"/operativa/$"))


def test_unknown_manager_says_it_does_not_exist(portal, datos):
    portal.goto(f"{portal.base}/operativa/delivery-manager/nadie/")

    expect(portal.get_by_role("alert")).to_be_visible()
    expect(portal.locator("#dm-table table")).to_have_count(0)


@pytest.mark.parametrize("width", [1450, 900, 390])
def test_reference_layout_is_responsive(portal, datos, hours, width):
    from pathlib import Path

    portal.set_viewport_size({"width": width, "height": 1000})
    portal.goto(portal.base + PAGE)
    expect(portal.locator("#hours-chart")).to_be_visible()
    expect(portal.locator("#dm-period")).to_contain_text("Octubre 2026")
    expect(portal.locator("#dm-table tbody tr")).to_have_count(2)
    assert portal.evaluate("document.documentElement.scrollWidth <= innerWidth")
    target = Path("tmp/design/dm-reference")
    target.mkdir(parents=True, exist_ok=True)
    portal.screenshot(path=str(target / f"dm-{width}.png"), full_page=True)


def test_project_filters_and_csv_export(portal, datos, hours):
    from pathlib import Path

    portal.goto(portal.base + PAGE)
    expect(portal.locator("#dm-project-search")).to_be_visible()
    portal.locator("#dm-project-search").fill("Portal")
    expect(portal.locator("#dm-table tbody tr")).to_have_count(1)
    expect(portal.locator(".dm-project-count")).to_have_text("1 de 2 proyectos")
    assert "dm_buscar=Portal" in portal.url
    with portal.expect_download() as download:
        portal.locator("#dm-project-export").click()
    text = Path(download.value.path()).read_text(encoding="utf-8-sig")
    assert "Portal Pacientes" in text
    assert '"HIS"' not in text
    portal.locator(".dm-filter-clear").click()
    expect(portal.locator("#dm-table tbody tr")).to_have_count(2)
    portal.select_option("#dm-project-service", "T&M")
    expect(portal.locator("#dm-table tbody tr")).to_have_count(1)
    expect(portal.locator("#dm-table tbody")).to_contain_text(
        "Portal Pacientes"
    )


def test_monthly_percentage_and_range_keep_original_detail(
    portal, datos, hours
):
    portal.goto(portal.base + PAGE)
    portal.locator("#hours-view-percent").click()
    expect(portal.locator("#hours-view-percent")).to_have_attribute(
        "aria-pressed", "true"
    )
    expect(portal.locator("#hours-chart")).to_contain_text("65%")
    portal.select_option("#hours-range", "3")
    portal.locator("#hours-chart g[role=button]").last.click()
    expect(portal.locator("#hours-modal-title")).to_have_text(
        "Detalle de horas · Octubre 2026"
    )
    expect(portal.locator("#hours-totals")).to_contain_text("39 h")
    portal.locator("#hours-close").click()
    portal.locator("#hours-view-hours").click()
    expect(portal.locator("#hours-chart")).to_contain_text("39 h")


def test_hours_detail_filters_keep_month_denominator(portal, datos, hours):
    portal.goto(portal.base + PAGE)
    portal.locator("#hours-detail").click()
    expect(portal.locator(".hours-share").first).to_have_text("97.4%")
    portal.select_option("#hours-service", "AER")
    expect(portal.locator("#hours-projects tr")).to_have_count(1)
    expect(portal.locator(".hours-share")).to_have_text("2.6%")
    expect(portal.locator("#hours-totals")).to_contain_text("39 h")
    portal.locator("#hours-search").fill("no existe")
    expect(portal.locator("#hours-projects")).to_contain_text(
        "No hay proyectos"
    )
    portal.locator("#hours-search").fill("")
    portal.select_option("#hours-service", "")
    portal.locator('#hours-modal th[data-sort="total"] button').click()
    expect(portal.locator("#hours-projects tr").first).to_contain_text("=HIS")
    portal.keyboard.press("Escape")
    expect(portal.locator("#hours-modal")).to_be_hidden()


@pytest.mark.parametrize("width", [1450, 390])
def test_hours_detail_pagination_and_responsive(
    portal, datos, monkeypatch, width
):
    from pathlib import Path

    data = month("Octubre 2026", 30, 5, 3)
    prototype = data["projects"][0]
    data["projects"] = [
        dict(
            prototype,
            id=str(i),
            name=f"Proyecto {i}",
            total=i,
            billable=i,
            operational=0,
            commercial=0,
        )
        for i in range(1, 13)
    ]
    data.update(total=78, billable=78, operational=0, commercial=0)
    monkeypatch.setattr(
        HOURS,
        lambda *a, **k: {
            "monthly": [data],
            "complete": True,
            "error": "",
            "monthly_has_data": True,
        },
    )
    portal.set_viewport_size({"width": width, "height": 1000})
    portal.goto(portal.base + PAGE)
    portal.locator("#hours-detail").click()
    expect(portal.locator("#hours-projects tr")).to_have_count(10)
    expect(portal.locator("#hours-count")).to_have_text(
        "Mostrando 1–10 de 12 proyectos"
    )
    dialog = portal.locator("#hours-modal")
    box = dialog.bounding_box()
    assert box["x"] >= 0 and box["x"] + box["width"] <= width
    target = Path("tmp/design/dm-hours-detail")
    target.mkdir(parents=True, exist_ok=True)
    portal.screenshot(path=str(target / f"hours-{width}.png"))
    portal.get_by_role("button", name="Página siguiente", exact=True).click()
    expect(portal.locator("#hours-projects tr")).to_have_count(2)
    expect(portal.locator("#hours-count")).to_have_text(
        "Mostrando 11–12 de 12 proyectos"
    )
    portal.locator("#hours-search").fill("Proyecto 12")
    expect(portal.locator("#hours-projects tr")).to_have_count(1)
    expect(portal.locator("#hours-count")).to_have_text(
        "Mostrando 1–1 de 1 proyectos"
    )
