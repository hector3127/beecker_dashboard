"""Consulta de las dos hojas del desglose en el navegador."""

from urllib.parse import parse_qs, urlparse

import pytest
from playwright.sync_api import expect

from tests.e2e.test_facturabilidad import facturability  # noqa: F401

pytestmark = pytest.mark.django_db(transaction=True)


@pytest.mark.usefixtures("facturability")
def test_audit_tabs_search_and_escape(portal):
    portal.route(
        "**/api/v1/screens/facturabilidad/desglose/**",
        lambda route: route.fulfill(
            json={
                "data": {
                    "ok": True,
                    "published_summary": {
                        "capacity": 6456,
                        "fixed_hours": 4673.4,
                        "variable_hours": 1279.1,
                        "free_hours": 503.5,
                        "global_percent": 92.2,
                    },
                    "synced_at": "2026-11-13T12:00:00Z",
                    "people": [
                        {
                            "name": "Ana",
                            "role": "DEV",
                            "estimated": 176,
                            "registered": 84,
                            "adjustment": 0,
                            "services": {"AER": 84},
                        }
                    ],
                    "projects": [
                        {
                            "name": "Ana",
                            "role": "DEV",
                            "project": "AER.A",
                            "service": "AER",
                            "kind": "Horas registradas",
                            "hours": 84,
                        }
                    ],
                },
                "meta": {},
            }
        ),
    )
    portal.goto(portal.base + "/operativa/facturabilidad/?mes=2026-02")
    trigger = portal.get_by_role(
        "button", name="Consultar personas y proyectos"
    )
    with portal.expect_request(
        "**/api/v1/screens/facturabilidad/desglose/**"
    ) as pending:
        trigger.click()
    query = parse_qs(urlparse(pending.value.url).query)
    assert query["mes"] == ["2026-02"]
    assert "params" not in query
    dialog = portal.get_by_role("dialog")
    expect(dialog).to_be_visible()
    expect(dialog.locator(".audit-reconciliation")).to_contain_text("6,456.00")
    expect(dialog.locator(".audit-reconciliation")).to_contain_text("4,673.40")
    expect(dialog.get_by_role("cell", name="Ana", exact=True)).to_be_visible()
    expect(dialog.locator(".audit-scroll tfoot")).to_contain_text("176.00")
    expect(dialog.locator(".audit-scroll tfoot")).to_contain_text("84.00")
    dialog.get_by_label("Filtrar Rol", exact=True).select_option("DEV")
    expect(dialog.locator(".audit-scroll tfoot")).to_contain_text("84.00")
    dialog.get_by_role("tab", name="Detalle por proyecto").click()
    expect(dialog.get_by_role("cell", name="AER.A", exact=True)).to_be_visible()
    dialog.get_by_role("searchbox").fill("inexistente")
    expect(dialog.get_by_text("Sin coincidencias", exact=False)).to_be_visible()
    expect(dialog.locator(".audit-scroll tfoot")).not_to_contain_text("84.00")
    dialog.get_by_role("button", name="Limpiar filtros").click()
    expect(dialog.locator(".audit-scroll tfoot")).to_contain_text("84.00")
    portal.keyboard.press("Escape")
    expect(dialog).not_to_be_visible()
    expect(trigger).to_be_focused()
