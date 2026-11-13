"""Detalle de críticos y riesgo al pasar el mouse o enfocar con teclado."""

import pytest
from playwright.sync_api import expect

from apps.portal.api import screens
from tests.e2e.test_operativa import ready

pytestmark = pytest.mark.django_db(transaction=True)


def test_critical_and_risk_details_on_hover_and_focus(
    portal, datos, monkeypatch
):
    original = screens.operativa_screen

    def response(*args, **kwargs):
        result = original(*args, **kwargs)
        result["data"]["project_details"] = [
            {
                "id": "AER.CRIT",
                "name": "Crítico de prueba",
                "health": "Crítica",
                "reason": "Consumo superior al presupuesto en horas.",
            },
            {
                "id": "AER.RISK",
                "name": "Riesgo de prueba",
                "health": "En Riesgo",
                "reason": "Quedan 5 días y como máximo el 10% del presupuesto.",
            },
        ]
        return result

    monkeypatch.setattr(screens, "operativa_screen", response)
    portal.goto(portal.base + "/operativa/")
    ready(portal)
    health = portal.locator("#ops-health")
    critical = health.locator(".ops-health-state:has(.critical)")
    popup = critical.locator(".ops-risk-popup")
    expect(popup).not_to_be_visible()
    critical.get_by_role("button", name="Críticos", exact=True).hover()
    expect(popup).to_be_visible()
    expect(popup).to_contain_text("AER.CRIT · Crítico de prueba")
    expect(popup).to_contain_text("Consumo superior al presupuesto")
    expect(popup).not_to_contain_text("AER.RISK")
    portal.mouse.move(0, 0)
    critical.get_by_role("button", name="Críticos", exact=True).focus()
    expect(popup).to_be_visible()
    risk = health.locator(".ops-health-state:has(.at_risk)")
    risk.get_by_role("button", name="En riesgo", exact=True).focus()
    expect(popup).not_to_be_visible()
    expect(risk.locator(".ops-risk-popup")).to_contain_text("AER.RISK")
