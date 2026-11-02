"""Integración v9 con la plantilla operativa y CSV detallado conservados."""

from pathlib import Path

import pytest
from playwright.sync_api import expect

from tests.portal.test_clockify_capacity import (
    clockify_capacity as clockify_capacity,
)

pytestmark = pytest.mark.django_db(transaction=True)


@pytest.mark.parametrize("width", [1450, 900, 390])
def test_team_matrix_keeps_roster_and_detailed_export(
    portal, datos, clockify_capacity, width, enforced_csp
):

    portal.set_viewport_size({"width": width, "height": 1000})
    portal.goto(portal.base + "/capacidad-instalada/?mes=2026-10")
    expect(portal.locator("#ci-status")).to_contain_text(
        "Bandas/rol + Clockify"
    )
    expect(portal.locator(".ci-table")).to_contain_text("Ana")
    expect(portal.locator(".ci-table")).to_contain_text("B2")
    expect(
        portal.get_by_role("columnheader", name="ID Clockify", exact=True)
    ).to_be_visible()
    expect(portal.locator(".ci-table")).to_contain_text("TYM.NYB.009")
    expect(portal.locator(".ci-table")).not_to_contain_text("Only Food")
    portal.locator("#ci-search").fill("NYB")
    with portal.expect_download() as download:
        portal.get_by_role("button", name="↓ Registros CSV", exact=True).click()
    text = Path(download.value.path()).read_text(encoding="utf-8-sig")
    assert "TYM.NYB.009" in text and "Registro completo" in text
    assert "Administrative Activities" not in text
    assert portal.evaluate("document.documentElement.scrollWidth <= innerWidth")
