"""Cuenta en un navegador real: resumen, ventanas, horas y finanzas."""

import json
import re

import pytest
from playwright.sync_api import expect

from apps.access.scope import AccessScope
from tests.access.fake_provider import DictProvider

pytestmark = pytest.mark.django_db(transaction=True)

PAGE = "/cuenta/clinica-sur/?nombre=Clinica+Sur"
SUMMARY = "**/api/v1/screens/cuenta/?*"
HOURS = "**/api/v1/screens/cuenta/consumos/**"
FINANCE = "**/api/v1/screens/cuenta/finanzas/**"


def project(pid, name, **extra):
    return {
        "id": pid,
        "name": name,
        "service": "T&M",
        "stage": "Build",
        "state": "En desarrollo",
        "manager": "Ana",
        "budget": 100,
        "burn": 40,
        "nps": 60,
        "clockify_pending": False,
        "exceeded": False,
        "late": False,
        **extra,
    }


def reply(route, data, meta=None, status=200):
    route.fulfill(
        status=status,
        content_type="application/json",
        body=json.dumps({"data": data, "meta": meta or {}}),
    )


def summary(projects, **extra):
    return {
        "available": True,
        "error": "",
        "nps": 60,
        "nps_sample": len(projects),
        "roc_active": 2,
        "consumption_pending": 0,
        "projects": projects,
        "roc": [
            {
                "process": "Reporte",
                "id": "R1",
                "service": "ROC",
                "bot_id": "1",
                "state": "Activo",
            }
        ],
        "opportunities": [
            {
                "account": "Clinica Sur",
                "name": "Fase 2",
                "manager": "Ana",
                "stage": "Won",
                "close": "2026-12-01",
                "hours": 80,
            }
        ],
        **extra,
    }


@pytest.fixture
def served(portal, datos):
    """La cuenta con tres proyectos y finanzas conocidas."""
    projects = [
        project("P1", "Portal"),
        project(
            "P2",
            "Alfa",
            service="ixb",
            burn=150,
            state="Completado",
            stage="Completed",
        ),
        project("P3", "Beta", late=True, nps=None, state="Suspendido"),
    ]
    portal.route(
        SUMMARY, lambda r: reply(r, summary(projects), {"cutoff": "2026-10-20"})
    )
    portal.route(
        FINANCE,
        lambda r: reply(
            r,
            {
                "account": {
                    "revenue": 1500000,
                    "margin": 42.5,
                    "cost": 3000,
                    "pending": 1,
                    "projects": 3,
                    "collections_percent": 80,
                    "collected": 400,
                    "invoiced": 100,
                }
            },
        ),
    )
    return projects


def test_summary_kpis_charts_and_table(portal, served):
    portal.goto(portal.base + PAGE)

    expect(
        portal.get_by_role("heading", name="Clinica Sur", exact=True)
    ).to_be_visible()
    assert portal.locator("main").count() == 1
    kpis = portal.locator(".account-kpis .account-card")
    expect(kpis).to_have_count(5)
    expect(kpis.nth(2)).to_contain_text("3")  # total de proyectos
    expect(portal.locator("#account-total-consumption")).to_have_text("77%")
    expect(portal.locator("#account-total-variance")).to_have_text(
        "230 h de 300 h"
    )
    expect(portal.locator(".model-row")).to_have_count(2)
    expect(portal.locator(".state-chart p")).to_have_count(3)
    expect(portal.locator(".account-alert")).to_have_count(2)
    expect(portal.locator("#account-finance-revenue")).to_have_text("1.5M")
    expect(portal.locator("#account-finance-margin")).to_have_text("42.5%*")
    expect(portal.locator("#account-finance-collections")).to_have_text("80%")
    assert portal.locator("#account-detail-modal").count() == 1


def test_project_search_state_filter_and_pages(portal, served):
    portal.goto(portal.base + PAGE)
    label = portal.locator("#account-page-label")
    expect(label).to_have_text("Mostrando 1–3 de 3 proyectos")

    portal.fill("#account-search", "alfa")
    expect(label).to_have_text("Mostrando 1–1 de 1 proyectos")
    portal.fill("#account-search", "")
    portal.select_option("#account-state", "Suspendido")
    expect(label).to_have_text("Mostrando 1–1 de 1 proyectos")
    expect(portal.locator("tr[data-project]:visible")).to_have_attribute(
        "data-project", "P3"
    )


def test_ver_mas_windows(portal, served):
    portal.goto(portal.base + PAGE)
    dialog = portal.locator("#account-detail-modal")

    portal.click("#roc-more")
    expect(portal.locator("#account-detail-title")).to_have_text(
        "Procesos de la cuenta en ROC"
    )
    expect(dialog).to_contain_text("Reporte")
    portal.click("#account-detail-close")
    expect(dialog).to_be_hidden()

    portal.click("#backlog-more")
    expect(portal.locator("#account-detail-title")).to_have_text(
        "Backlog de la cuenta"
    )
    expect(dialog).to_contain_text("Fase 2")
    expect(dialog).to_contain_text("80 h")
    portal.click("#account-detail-close")

    portal.click("#nps-more")
    expect(portal.locator("#account-detail-title")).to_contain_text(
        "NPS por proyecto"
    )
    expect(dialog.locator("circle")).to_have_count(
        2
    )  # solo los proyectos con NPS
    portal.click("#account-detail-close")

    portal.click("#budget-more")
    expect(portal.locator("#account-detail-title")).to_have_text(
        "Presupuesto vs consumo"
    )
    expect(dialog.locator(".detail-metrics > div")).to_have_count(4)
    expect(dialog).to_contain_text("Proyectos excedidos")
    portal.get_by_role("button", name="IxB", exact=True).click()
    expect(
        dialog.locator(".budget-project-card tbody tr, .budget-project-card tr")
    ).to_have_count(2)  # encabezado y un proyecto


def test_hours_arrive_in_batches_and_update_the_page(portal, datos):
    projects = [
        project("P1", "Portal", burn=None, clockify_pending=True),
        project("P2", "Alfa", burn=None, clockify_pending=True),
    ]
    portal.route(
        SUMMARY, lambda r: reply(r, summary(projects, consumption_pending=2))
    )
    portal.route(FINANCE, lambda r: reply(r, {"account": None}))
    calls = []

    def batch(route):
        url = route.request.url
        calls.append(url)
        if "offset=0" in url:
            reply(
                route,
                {
                    "ok": True,
                    "items": [{"id": "P1", "burn": 90, "error": ""}],
                    "next": 1,
                    "total": 2,
                },
            )
        else:
            reply(
                route,
                {
                    "ok": True,
                    "items": [{"id": "P2", "burn": 130, "error": ""}],
                    "next": 2,
                    "total": 2,
                },
            )

    portal.route(HOURS, batch)
    portal.goto(portal.base + PAGE)

    expect(portal.locator("#account-refresh")).to_have_text(
        "Horas actualizadas"
    )
    expect(
        portal.locator('tr[data-project="P1"] .account-project-burn')
    ).to_have_text("90 h")
    expect(portal.locator("#account-total-consumption")).to_have_text("110%")
    expect(portal.locator(".account-alert")).to_have_count(
        1
    )  # P2 excede su presupuesto
    assert len(calls) == 2 and all("pending_id=P1" in c for c in calls)
    expect(portal.locator("#account-finance-revenue")).to_have_text("Sin datos")


def test_a_failed_hour_batch_keeps_the_cut(portal, datos):
    projects = [project("P1", "Portal", burn=None, clockify_pending=True)]
    portal.route(
        SUMMARY, lambda r: reply(r, summary(projects, consumption_pending=1))
    )
    portal.route(FINANCE, lambda r: reply(r, {"account": None}))
    portal.route(HOURS, lambda r: r.fulfill(status=500, body="x"))
    portal.goto(portal.base + PAGE)

    expect(portal.locator("#account-refresh")).to_contain_text(
        "Se conserva el corte disponible"
    )
    expect(portal.locator("tr[data-project=P1]")).to_be_visible()


def test_unreadable_account_shows_the_reason(portal, datos):
    portal.route(
        SUMMARY,
        lambda r: reply(r, {"available": False, "error": "Hoja sin acceso."}),
    )
    portal.goto(portal.base + PAGE)

    expect(portal.locator("#account-content")).to_have_text("Hoja sin acceso.")
    expect(portal.locator("#executive-agreements")).to_be_visible()


def test_request_failure_offers_a_retry(portal, datos):
    portal.route(SUMMARY, lambda r: r.fulfill(status=500, body="x"))
    portal.goto(portal.base + PAGE)

    expect(portal.get_by_role("alert")).to_contain_text("servidor")
    expect(portal.get_by_role("button", name="Reintentar")).to_be_visible()


def test_links_keep_the_way_back(portal, served):
    portal.goto(portal.base + PAGE)
    portal.locator("#account-project-table").scroll_into_view_if_needed()
    portal.get_by_role("link", name="Portal", exact=True).click()

    portal.wait_for_url(re.compile(r"/proyectos/P1/\?volver="))


def test_limited_scope_cannot_open_a_foreign_account(
    portal, datos, settings, client, django_user_model
):
    settings.ACCESS_ENFORCED = True
    settings.ACCESS_PROVIDER = "tests.access.fake_provider.DictProvider"
    client.force_login(django_user_model.objects.create_user("ana"))
    portal.context.add_cookies(
        [
            {
                "name": "sessionid",
                "value": client.cookies["sessionid"].value,
                "url": portal.base,
            }
        ]
    )
    DictProvider.GRANTS = {
        "ana": (
            frozenset({"view_operations"}),
            AccessScope.limited(accounts=["ACME"]),
        )
    }
    try:
        response = portal.goto(portal.base + PAGE)
        assert response is not None and response.status == 404
    finally:
        DictProvider.GRANTS = {}
