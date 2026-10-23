"""Comercial en un navegador real: plantilla modular y comportamiento."""

from unittest.mock import MagicMock

import pytest
from playwright.sync_api import expect

pytestmark = pytest.mark.django_db(transaction=True)

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
    assert portal.locator("main").count() == 1
    assert portal.locator("link[href*='pages/commercial.css']").count() == 1
    expect(portal.locator(".k4 .kx")).to_have_count(4)
    expect(
        portal.get_by_role("button", name="↓ Descargar captura")
    ).to_be_visible()
    expect(portal.locator("#pipeline-confirmed")).to_contain_text(
        "Total de horas"
    )


def test_service_rows_open_and_the_year_reloads(portal, backlog):
    portal.goto(portal.base + "/comercial/")
    detail = portal.locator(".service-detail-row").first
    expect(detail).to_be_hidden()
    portal.locator(".service-accounts summary").first.click()
    expect(detail).to_be_visible()

    portal.select_option("#pipeline-year", "2026")
    portal.wait_for_url("**pipeline_year=2026*")
