"""Consulta de las dos hojas del desglose en el navegador."""

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
    portal.goto(
        portal.base + "/operativa/facturabilidad/especialidad/?mes=2026-02"
    )
    trigger = portal.get_by_role(
        "button", name="Consultar personas y proyectos"
    )
    trigger.click()
    dialog = portal.get_by_role("dialog")
    expect(dialog).to_be_visible()
    expect(dialog.get_by_role("cell", name="Ana", exact=True)).to_be_visible()
    dialog.get_by_role("tab", name="Detalle por proyecto").click()
    expect(dialog.get_by_role("cell", name="AER.A", exact=True)).to_be_visible()
    dialog.get_by_role("searchbox").fill("inexistente")
    expect(dialog.get_by_text("Sin coincidencias", exact=False)).to_be_visible()
    portal.keyboard.press("Escape")
    expect(dialog).not_to_be_visible()
    expect(trigger).to_be_focused()
