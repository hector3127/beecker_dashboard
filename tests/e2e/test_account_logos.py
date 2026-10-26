"""Upload preview, persistent logo, listing and removal in a real browser."""

import re
from io import BytesIO

import pytest
from PIL import Image
from playwright.sync_api import expect

from apps.portal.models import AccountLogo

pytestmark = pytest.mark.django_db(transaction=True)
PAGE = "/cuenta/clinica-sur/?nombre=Clinica+Sur"


def test_logo_preview_with_enforced_csp(portal, datos, settings):
    """Enforce the future policy in this browser only, not in deployment."""
    settings.CSP_REPORT_ONLY = True

    def enforce_policy(route):
        response = route.fetch()
        headers = dict(response.headers)
        headers["content-security-policy"] = headers.pop(
            "content-security-policy-report-only"
        )
        route.fulfill(response=response, headers=headers)

    portal.route("**/cuenta/clinica-sur/?nombre=Clinica+Sur", enforce_policy)
    portal.goto(portal.base + PAGE)
    portal.get_by_role("button", name="Cambiar logo").click()
    image = BytesIO()
    Image.new("RGB", (80, 60), "green").save(image, "PNG")
    portal.locator("#account-logo-file").set_input_files(
        {
            "name": "logo.png",
            "mimeType": "image/png",
            "buffer": image.getvalue(),
        }
    )
    preview = portal.locator("#account-logo-preview")
    expect(preview).to_be_visible()
    expect(preview).to_have_attribute("src", re.compile(r"^blob:"))
    expect(preview).to_have_js_property("naturalWidth", 80)
    expect(
        portal.get_by_role("button", name="Guardar logo", exact=True)
    ).to_be_enabled()


@pytest.mark.parametrize("width", [1450, 390])
def test_logo_upload_and_remove(portal, datos, monkeypatch, width):
    portal.set_viewport_size({"width": width, "height": 1000})
    portal.goto(portal.base + PAGE)
    expect(portal.locator(".account-brand .account-initials")).to_have_text(
        "CS"
    )
    expect(portal.locator(".account-brand svg")).to_have_count(0)
    expect(
        portal.locator(".account-logo-anchor #account-logo-open")
    ).to_be_visible()
    portal.get_by_role("button", name="Cambiar logo").click()
    if width == 390:
        assert (
            portal.locator(".logo-editor-heading>div").bounding_box()["width"]
            > 240
        )
    image = BytesIO()
    Image.new("RGB", (80, 60), "green").save(image, "PNG")
    portal.locator("#account-logo-file").set_input_files(
        {
            "name": "logo.png",
            "mimeType": "image/png",
            "buffer": image.getvalue(),
        }
    )
    expect(portal.locator("#account-logo-preview")).to_be_visible()
    expect(portal.locator("#account-logo-filename")).to_have_text("logo.png")
    from pathlib import Path

    folder = Path("tmp/design/logo-upload-reference")
    folder.mkdir(parents=True, exist_ok=True)
    portal.locator("#account-logo-form").screenshot(
        path=str(folder / f"editor-{width}.png")
    )
    portal.get_by_role("button", name="Guardar logo", exact=True).click()
    expect(portal.locator("#account-logo-status")).to_contain_text(
        "Logo guardado"
    )
    expect(portal.locator(".account-brand img")).to_be_visible()
    assert AccountLogo.objects.count() == 1
    portal.locator(".account-hero").screenshot(
        path=str(folder / f"hero-{width}.png")
    )
    from pathlib import Path

    target = Path("tmp/design/account-logos")
    target.mkdir(parents=True, exist_ok=True)
    portal.screenshot(path=str(target / f"account-{width}.png"), full_page=True)
    assert portal.evaluate("document.documentElement.scrollWidth <= innerWidth")
    portal.reload()
    expect(portal.locator(".account-brand img")).to_be_visible()
    monkeypatch.setattr(
        "apps.portal.services.account_profitability.load_account_profitability",
        lambda: {
            "year": 2026,
            "accounts": [
                {
                    "name": "Clinica Sur",
                    "url": PAGE,
                    "revenue": 1000,
                    "cost": 100,
                    "gross_profit": 900,
                    "margin": 90,
                    "projects": 1,
                    "pending": 0,
                    "classification": "healthy",
                }
            ],
        },
    )
    portal.goto(portal.base + "/ejecutiva/cuentas/")
    expect(portal.locator(".account-avatar img")).to_be_visible()
    portal.goto(portal.base + PAGE)
    expect(
        portal.locator(".account-logo-anchor #account-logo-open")
    ).to_be_visible()
    portal.get_by_role("button", name="Cambiar logo").click()
    portal.get_by_role("button", name="Quitar logo").click()
    expect(portal.locator("#account-logo-status")).to_have_text(
        "Logo eliminado."
    )
    expect(portal.locator(".account-brand img")).to_have_count(0)
    assert not AccountLogo.objects.exists()
    expect(portal.locator(".account-brand .account-initials")).to_have_text(
        "CS"
    )


def test_drag_drop_cancel_and_recommendations(portal, datos):
    portal.goto(portal.base + PAGE)
    portal.get_by_role("button", name="Cambiar logo").click()
    expect(portal.locator("#logo-preview-empty")).to_have_text("CS")
    expect(portal.locator("#account-logo-save")).to_be_disabled()
    portal.get_by_role("button", name="Recomendaciones").click()
    expect(portal.locator("#logo-recommendations")).to_be_hidden()
    portal.get_by_role("button", name="Recomendaciones").click()
    expect(portal.locator("#logo-recommendations")).to_be_visible()
    image = BytesIO()
    Image.new("RGBA", (80, 60), "green").save(image, "PNG")
    portal.locator("#logo-dropzone").evaluate(
        """(zone, bytes) => {
            const transfer = new DataTransfer();
            transfer.items.add(new File(
                [new Uint8Array(bytes)], 'drop.png', {type: 'image/png'}
            ));
            zone.dispatchEvent(new DragEvent('drop', {
                dataTransfer: transfer, bubbles: true, cancelable: true
            }));
        }""",
        list(image.getvalue()),
    )
    expect(portal.locator("#account-logo-filename")).to_have_text("drop.png")
    expect(portal.locator("#account-logo-preview")).to_be_visible()
    expect(portal.locator("#logo-preview-badge")).to_have_text("Vista previa")
    expect(portal.locator("#account-logo-save")).to_be_enabled()
    portal.get_by_role("button", name="Cancelar", exact=True).click()
    expect(portal.locator("#account-logo-form")).to_be_hidden()
    assert not AccountLogo.objects.exists()
    portal.get_by_role("button", name="Cambiar logo").click()
    expect(portal.locator("#logo-preview-empty")).to_be_visible()
    expect(portal.locator("#account-logo-save")).to_be_disabled()
    portal.keyboard.press("Escape")
    expect(portal.locator("#account-logo-form")).to_be_hidden()
