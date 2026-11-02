"""Comercial en un navegador real: plantilla modular y comportamiento."""

from unittest.mock import MagicMock

import pytest
from playwright.sync_api import expect

pytestmark = pytest.mark.django_db(transaction=True)


@pytest.mark.parametrize("width", [1450, 900, 390])
@pytest.mark.parametrize("from_executive", [False, True])
def test_reference_dashboard_layout_and_existing_interactions(
    portal, backlog, width, from_executive, enforced_csp
):
    from pathlib import Path

    from tests.e2e.conftest import watch

    problems = watch(portal)
    portal.set_viewport_size({"width": width, "height": 1000})
    query = "?pipeline_year=2026"
    if from_executive:
        query += "&origen=business-overview&desde=2026-01-01&hasta=2026-12-31"
    portal.goto(portal.base + "/comercial/" + query)
    portal.locator(".service-accounts summary").first.click()
    expect(portal.locator(".service-detail-row").first).to_be_visible()
    portal.evaluate("document.fonts.ready")
    portal.mouse.move(0, 0)
    expect(portal.locator(".k4 .kx")).to_have_count(4)
    expect(portal.locator("#commercial-stage-donut svg")).to_have_count(1)
    expect(portal.locator("#commercial-pipeline-chart svg")).to_have_count(1)
    assert portal.evaluate(
        "document.documentElement.scrollWidth <= innerWidth + 1"
    )
    origin = "executive" if from_executive else "direct"
    key = f"commercial_layout_{width}_{origin}"
    path = Path(f"tmp/migration/commercial/{key}.png")
    path.parent.mkdir(parents=True, exist_ok=True)
    portal.screenshot(path=str(path), full_page=True)
    assert not problems


HEADERS = [
    "Account Name",
    "Opportunity Name",
    "Delivery Manager",
    "Opportunity Stage",
    "Fecha de cierre - Diario",
    "Service Type",
    "Invoice Name",
    "Total Hours",
    "Duration_Service",
    "Valor",
    "Currency Opportunity",
    "Account",
    "Fecha inicio",
    "Stage",
    "CIO",
    "Calculadora",
    "Arq",
    "En tiempo",
    "Observaciones",
    "Estimación",
    "Fecha último seguimiento",
    "Probabilidad",
]


def row(account, name, stage, close, service, hours, value, probability):
    return [
        account,
        name,
        "Ana",
        stage,
        close,
        service,
        "I",
        hours,
        "12",
        value,
        "USD",
        account,
        "2026-01-05",
        "Prospectos",
        "Si",
        "Si",
        "No",
        "",
        "",
        "100",
        "2026-10-01",
        probability,
    ]


@pytest.fixture
def backlog(monkeypatch, datos):
    factory = MagicMock()
    factory.return_value.read_values.return_value = [
        HEADERS,
        row(
            "ACME",
            "Portal",
            "Confirmed (Pipeline)",
            "2026-11-15",
            "SaaS",
            "120",
            30000,
            "90",
        ),
        row(
            "ACME",
            "App",
            "Discovery (Pipeline)",
            "2026-12-15",
            "AER",
            "80",
            20000,
            "70",
        ),
        row(
            "Beta",
            "ERP",
            "Closed Won",
            "2026-03-10",
            "T&M",
            "200",
            50000,
            "100",
        ),
    ]
    monkeypatch.setattr(
        "apps.portal.services.commercial_view.build_sheet_repository", factory
    )


def test_page_uses_the_modular_frontend(portal, backlog):
    portal.goto(portal.base + "/comercial/")

    expect(
        portal.get_by_role("heading", name="Comercial", exact=True)
    ).to_be_visible()
    expect(
        portal.get_by_role("button", name="↓ Descargar captura")
    ).to_have_count(1)
    assert portal.locator("main").count() == 1
    assert portal.locator("link[href*='pages/commercial.css']").count() == 1
    expect(portal.locator(".k4 .kx")).to_have_count(4)
    expect(
        portal.get_by_role("button", name="↓ Descargar captura")
    ).to_be_visible()
    expect(portal.locator("#pipeline-confirmed")).to_contain_text(
        "Total de horas"
    )


@pytest.mark.parametrize(
    "saved_link", [False, True], ids=["current_url", "obsolete_url"]
)
def test_service_rows_open_and_the_year_reloads(portal, backlog, saved_link):
    portal.goto(
        portal.base + "/comercial/" + ("?vista=anterior" if saved_link else "")
    )
    detail = portal.locator(".service-detail-row").first
    expect(detail).to_be_hidden()
    portal.locator(".service-accounts summary").first.click()
    expect(detail).to_be_visible()

    portal.select_option("#pipeline-year", "2026")
    portal.wait_for_url("**pipeline_year=2026*")


@pytest.mark.parametrize(
    "saved_link", [False, True], ids=["current_url", "obsolete_url"]
)
def test_executive_origin_keeps_dates_when_year_changes(
    portal, backlog, saved_link
):
    query = "?origen=business-overview&desde=2026-01-01&hasta=2026-12-31"
    portal.goto(
        portal.base
        + "/comercial/"
        + query
        + ("&vista=anterior" if saved_link else "")
    )
    expected = "/?periodo=rango&desde=2026-01-01&hasta=2026-12-31"
    expect(portal.locator("[data-portal-back]")).to_have_attribute(
        "href", expected
    )
    portal.select_option("#pipeline-year", "2026")
    portal.wait_for_url("**pipeline_year=2026*")
    expect(portal.locator("[data-portal-back]")).to_have_attribute(
        "href", expected
    )


@pytest.mark.parametrize("width", [1450, 900, 390])
def test_reference_dashboard_charts_controls_and_mobile(
    portal, backlog, width, enforced_csp
):
    portal.set_viewport_size({"width": width, "height": 1000})
    portal.goto(portal.base + "/comercial/?pipeline_year=2026")
    expect(portal.locator(".commercial-nav")).to_have_count(0)
    expect(portal.locator("#commercial-stage-donut svg")).to_have_count(1)
    expect(portal.locator("#commercial-pipeline-chart svg rect")).to_have_count(
        12
    )
    expect(portal.locator(".k4 .v")).to_have_text(["50K", "50K", "1", "3"])
    portal.get_by_role("button", name="Mes", exact=True).click()
    portal.get_by_role("combobox", name="Mes de carga comercial").select_option(
        "10"
    )
    expect(portal.locator("#commercial-pipeline-chart svg rect")).to_have_count(
        1
    )
    expect(portal.locator("#commercial-pipeline-chart svg")).to_contain_text(
        "120"
    )
    portal.get_by_role("button", name="Año", exact=True).click()
    expect(portal.locator("#commercial-pipeline-chart svg rect")).to_have_count(
        12
    )
    assert portal.evaluate(
        "document.documentElement.scrollWidth <= innerWidth+1"
    )
