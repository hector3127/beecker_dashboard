"""Cambios de la demo: navegación por recurso y plan, con rutas reales y CSP."""

from pathlib import Path

import pytest
from playwright.sync_api import expect

from tests.e2e.test_capacidad_diaria import daily as daily
from tests.e2e.test_capacidad_diaria import ready
from tests.e2e.test_ixs_client_actions_transport import (
    client_actions as client_actions,
)
from tests.e2e.test_ixs_executive import ixs as ixs
from tests.e2e.test_project_design_sections import design_site as design_site
from tests.e2e.test_project_detail_entry import project_detail as project_detail

pytestmark = [
    pytest.mark.django_db(transaction=True),
    pytest.mark.usefixtures("design_site", "enforced_csp"),
]


@pytest.mark.parametrize("width", [1450, 900, 390])
def test_resource_drilldown_and_return(portal, daily, width):
    portal.set_viewport_size({"width": width, "height": 1000})
    errors = []
    portal.on("pageerror", lambda error: errors.append(str(error)))
    portal.goto(portal.base + "/capacidad-instalada/?mes=2026-10")
    ready(portal)
    totals = portal.locator(".ci-stat strong").all_text_contents()
    portal.get_by_role(
        "button", name="Ver horas diarias de Ana Perez"
    ).first.click()
    detail = portal.locator(".ci-person-detail")
    expect(detail).to_be_visible()
    expect(detail).to_contain_text("P1")
    expect(detail).not_to_contain_text("Luis")
    assert portal.locator(".ci-stat strong").all_text_contents() == totals
    assert portal.evaluate(
        "document.documentElement.scrollWidth <= innerWidth + 1"
    )
    path = Path(f"tmp/demo-requests/capacity-{width}.png")
    path.parent.mkdir(parents=True, exist_ok=True)
    portal.evaluate("window.scrollTo(0, 0)")
    portal.screenshot(path=str(path), full_page=True)
    portal.get_by_role("button", name="Regresar al listado").click()
    expect(portal.locator(".ci-table tbody tr")).to_have_count(2)
    portal.get_by_role(
        "button", name="Capacidad por recurso", exact=True
    ).click()
    portal.get_by_role(
        "button", name="Ver horas diarias de Luis", exact=True
    ).click()
    expect(detail).to_contain_text("P2")
    assert not errors


@pytest.mark.parametrize("width", [1450, 900, 390])
def test_ixs_planning_shows_stored_work_plan(
    portal, project_detail, client_actions, width
):
    portal.set_viewport_size({"width": width, "height": 1000})
    portal.route(
        "**/api/v1/screens/proyectos/AMK.008/cliente/",
        lambda route: route.fulfill(
            json={
                "data": {
                    "ok": True,
                    "proyectoId": "AMK.008",
                    "cliente": {
                        "documentos": [
                            {
                                "nombre": "Roadmap aprobado",
                                "tipo": "Plan de trabajo",
                                "url": "https://example.com/plan",
                            }
                        ]
                    },
                },
                "meta": {},
            }
        ),
    )
    portal.goto(portal.base + "/proyectos/AMK.008/")
    portal.locator(".ixs-nav").get_by_role(
        "button", name="Planeación", exact=True
    ).click()
    expect(
        portal.locator("[data-work-plan]").get_by_role(
            "link", name="Abrir Roadmap aprobado"
        )
    ).to_have_attribute("href", "https://example.com/plan")
    assert portal.evaluate(
        "document.documentElement.scrollWidth <= innerWidth + 1"
    )
    Path("tmp/demo-requests").mkdir(parents=True, exist_ok=True)
    portal.locator("[data-work-plan]").screenshot(
        path=f"tmp/demo-requests/ixs-plan-{width}.png"
    )


@pytest.mark.parametrize("width", [1450, 900, 390])
def test_aer_planning_uses_its_own_work_plan(portal, project_detail, width):
    portal.set_viewport_size({"width": width, "height": 1000})
    _, aer = project_detail
    aer.setdefault("cliente", {})["documentos"] = [
        {
            "tipo": "Roadmap",
            "nombre": "Plan AER",
            "url": "https://example.com/aer",
        }
    ]
    portal.goto(portal.base + "/proyectos/AER.001/")
    portal.locator(".aer-tabs").get_by_role(
        "button", name="Planeación", exact=True
    ).click()
    expect(
        portal.locator("[data-work-plan]").get_by_role(
            "link", name="Abrir Plan AER"
        )
    ).to_have_attribute("href", "https://example.com/aer")
    assert portal.evaluate(
        "document.documentElement.scrollWidth <= innerWidth + 1"
    )
    Path("tmp/demo-requests").mkdir(parents=True, exist_ok=True)
    portal.locator("[data-work-plan]").screenshot(
        path=f"tmp/demo-requests/aer-plan-{width}.png"
    )


@pytest.mark.parametrize("width", [1450, 900, 390])
def test_personnel_filter_is_visible_and_preserves_individual_values(
    portal, monkeypatch, width
):
    from apps.portal.services.facturability_loader import MonthSources
    from tests.portal.test_facturability import BILLABLE, gse

    data = gse(
        {"DEV": ["Ana", "Eva"]},
        ("Ana", "DEV", "AER", 40, BILLABLE),
        ("Eva", "DEV", "AER", 20, BILLABLE),
    )
    data.update(
        plantilla=[{"nombre": "Ana", "rol": "DEV"}], plantillaBajas=["Eva"]
    )
    monkeypatch.setattr(
        "apps.portal.views.load_year_sources",
        lambda _: [MonthSources(month="2026-01", gse=data)],
    )
    portal.set_viewport_size({"width": width, "height": 1000})
    portal.goto(portal.base + "/operativa/facturabilidad/recurso/?mes=2026-01")
    expect(portal.locator("[data-resource-row]")).to_have_count(2)
    value = (
        portal.locator("[data-resource-row]")
        .first.locator("td")
        .nth(2)
        .inner_text()
    )
    portal.locator("#resource-population").select_option("activo")
    portal.get_by_role("button", name="Aplicar plantilla", exact=True).click()
    expect(portal.locator("[data-resource-row]")).to_have_count(1)
    expect(portal.locator("[data-resource-row]").first).to_contain_text("Ana")
    assert (
        portal.locator("[data-resource-row]")
        .first.locator("td")
        .nth(2)
        .inner_text()
        == value
    )
    assert portal.evaluate(
        "document.documentElement.scrollWidth <= innerWidth + 1"
    )
    Path("tmp/demo-requests").mkdir(parents=True, exist_ok=True)
    portal.screenshot(
        path=f"tmp/demo-requests/personnel-{width}.png", full_page=True
    )


def test_concurrent_read_requests(live_server, daily, settings, tmp_path):
    import json

    from apps.datastore.models import DataRevision
    from scripts.check_load import run_load

    settings.CLOCKIFY_STORE_ENABLED = True
    DataRevision.objects.get_or_create(pk=1)
    result = run_load(
        live_server.url + "/api/v1/screens/capacidad/diaria/?mes=2026-10", 64, 8
    )
    assert result["success"] == 64, result
    assert not result["errors"]
    Path("tmp/demo-requests").mkdir(parents=True, exist_ok=True)
    Path("tmp/demo-requests/load.json").write_text(
        json.dumps(result, indent=2), encoding="utf-8"
    )
