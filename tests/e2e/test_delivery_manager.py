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
