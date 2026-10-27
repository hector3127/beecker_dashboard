"""Con la politica obligatoria (cabecera real), las pantallas cargan."""

import pytest
from playwright.sync_api import expect

from tests.e2e.conftest import watch

pytestmark = pytest.mark.django_db(transaction=True)

PAGES = [
    ("/", "#main-content"),
    ("/operativa/", "#main-content"),
    ("/comercial/", "#main-content"),
    ("/operativa/eva-1/", "#main-content"),
    ("/ejecutiva/oportunidades/", "#main-content"),
    ("/diccionario-datos/", "#main-content"),
]


@pytest.mark.parametrize("path,marker", PAGES)
def test_pages_load_under_the_enforced_policy(
    portal, datos, settings, path, marker
):
    settings.CSP_ENFORCE = True
    problems = watch(portal)

    response = portal.goto(portal.base + path)
    expect(portal.locator(marker)).to_be_visible()
    portal.wait_for_load_state("networkidle")

    assert (
        "script-src 'self' 'nonce-"
        in (response.headers["content-security-policy"])
    )
    assert problems == []
