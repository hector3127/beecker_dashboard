"""Shared PNG export on modular screens, including obsolete saved links."""

import re
from pathlib import Path

import pytest
from playwright.sync_api import expect

pytestmark = pytest.mark.django_db(transaction=True)

STUB = """window.html2canvas = async (target, options) => {
  window.captureTarget = target.id;
  const doc = document.implementation.createHTMLDocument('clone');
  doc.body.appendChild(target.cloneNode(true));
  options.onclone(doc);
  const hidden = doc.querySelectorAll('[hidden], dialog:not([open])');
  window.captureHidden = hidden.length;
  const canvas = document.createElement('canvas');
  canvas.width = 120; canvas.height = 80;
  canvas.getContext('2d').fillRect(0, 0, 120, 80);
  return canvas;
};"""


@pytest.mark.parametrize("width", [1450, 390])
@pytest.mark.parametrize(
    "path",
    [
        "/diccionario-datos/",
        "/diccionario-datos/?vista=anterior",
        "/operativa/eva-4/",
        "/cuenta/clinica-sur/?nombre=Clinica+Sur",
        "/ejecutiva/oportunidades/?periodo=anio&anio=2026",
        "/proyectos/AMK.008/",
    ],
)
def test_every_layout_exports_its_current_content(portal, datos, width, path):
    portal.add_init_script(STUB)
    portal.set_viewport_size({"width": width, "height": 1000})
    portal.goto(portal.base + path)
    button = portal.get_by_role("button", name="↓ Descargar captura")
    expect(button).to_have_count(1)
    expect(button).to_be_visible()
    original = portal.url
    with portal.expect_download() as result:
        button.click()
    assert re.fullmatch(
        r"[a-z0-9-]+-\d{4}-\d{2}-\d{2}\.png", result.value.suggested_filename
    )
    assert (
        Path(result.value.path()).read_bytes().startswith(b"\x89PNG\r\n\x1a\n")
    )
    assert portal.evaluate("window.captureTarget") == "main-content"
    assert portal.evaluate("window.captureHidden") == 0
    assert portal.url == original
    expect(button).to_be_enabled()
    expect(portal.locator(".capture-status")).to_have_text(
        "Captura descargada."
    )


@pytest.mark.parametrize("policy", ["default", "enforced"])
def test_real_library_downloads_a_valid_png_and_loads_only_on_demand(
    portal, datos, request, policy
):
    from tests.e2e.conftest import watch

    if policy == "enforced":
        request.getfixturevalue("enforced_csp")
    problems = watch(portal)
    portal.goto(portal.base + "/guia-de-interfaz/")
    assert portal.locator('script[src*="html2canvas"]').count() == 0
    with portal.expect_download(timeout=60000) as result:
        portal.get_by_role("button", name="↓ Descargar captura").click()
    assert (
        Path(result.value.path()).read_bytes().startswith(b"\x89PNG\r\n\x1a\n")
    )
    assert portal.locator('script[src*="html2canvas"]').count() == 1
    expect(portal.locator(".capture-status")).to_have_text(
        "Captura descargada."
    )
    assert problems == []


def test_failed_library_download_allows_retry(portal, datos):
    attempts = []

    def library(route):
        attempts.append(1)
        if len(attempts) == 1:
            route.abort()
        else:
            route.fulfill(content_type="application/javascript", body=STUB)

    portal.route("**/html2canvas-1.4.1.min.js", library)
    portal.goto(portal.base + "/guia-de-interfaz/")
    button = portal.get_by_role("button", name="↓ Descargar captura")
    button.click()
    expect(portal.locator(".capture-status")).to_contain_text(
        "Vuelve a intentarlo"
    )
    expect(button).to_be_enabled()
    with portal.expect_download() as result:
        button.click()
    assert result.value.suggested_filename.endswith(".png")
    expect(portal.locator(".capture-status")).to_have_text(
        "Captura descargada."
    )
    assert len(attempts) == 2
