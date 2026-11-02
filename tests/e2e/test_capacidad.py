"""La URL mensual abre el mismo reporte completo de Clockify."""

import pytest
from playwright.sync_api import expect

from tests.portal.test_clockify_capacity import (
    clockify_capacity as clockify_capacity,
)

pytestmark = pytest.mark.django_db(transaction=True)


def test_monthly_url_uses_clockify_detail(portal, datos, clockify_capacity):
    portal.goto(
        portal.base
        + "/operativa/capacidad-instalada/?mes=2026-10&vista=anterior"
    )
    expect(portal.locator("#ci-status")).to_contain_text(
        "Bandas/rol + Clockify"
    )
    expect(portal.locator(".ci-table")).to_contain_text("TYM.NYB.009")
    expect(
        portal.get_by_role("link", name="← Regresar a Operativa")
    ).to_have_attribute("href", "/operativa/")
