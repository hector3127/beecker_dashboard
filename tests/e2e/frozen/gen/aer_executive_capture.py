"""Temporary explicit capture: only the original route produces expectations.

Run from repository root with pytest and --browser-channel chrome.
Never collected by the normal test_*.py discovery.
"""

import hashlib
import json
import platform
from pathlib import Path

import pytest

from tests.e2e.frozen.aer_executive_support import (
    FIXED_DAY,
    PAGE,
    input_digest,
    prepare,
    state,
)
from tests.e2e.test_aer_executive import fixed_day as fixed_day
from tests.e2e.test_project_detail_entry import project_detail as project_detail

pytestmark = pytest.mark.django_db(transaction=True)
ROOT = Path("tests/e2e/frozen/aer_executive")


@pytest.mark.parametrize("variant", ["full", "empty", "attention"])
@pytest.mark.parametrize("width", [1450, 900, 390])
def test_capture_original(portal, project_detail, fixed_day, variant, width):
    _, data = project_detail
    prepare(data, variant)
    portal.set_viewport_size({"width": width, "height": 1000})
    portal.goto(portal.base + PAGE + "?vista=anterior")
    elements = state(portal)
    assert (
        portal.locator(".aer-exec-view").get_attribute("data-renderer")
        != "modular"
    )
    assert (
        portal.locator('script[src*="portal/js/proyecto_detalle.js"]').count()
        == 1
    )
    document = {
        "schema": 1,
        "source": "original",
        "base_commit": "3c0f9cc",
        "variant": variant,
        "viewport": {"width": width, "height": 1000},
        "fixed_day": FIXED_DAY,
        "input_sha256": input_digest(data),
        "browser": portal.context.browser.version,
        "platform": platform.system(),
        "source_sha256": {
            name: hashlib.sha256(
                Path(name).read_text(encoding="utf-8").encode()
            ).hexdigest()
            for name in [
                "tests/reference/static/portal/js/proyecto_detalle.js",
                "tests/reference/static/portal/css/proyecto_detalle.css",
                "tests/reference/templates/portal/proyecto_detalle.html",
                "tests/aer/aer_expected.json",
                "tests/ejecutivo/project_integrated_expected.json",
            ]
        },
        "elements": elements,
    }
    ROOT.mkdir(parents=True, exist_ok=True)
    (ROOT / f"{variant}-{width}.json").write_text(
        json.dumps(document, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    screenshot = Path(f"tmp/frozen-browser/aer_executive/{variant}-{width}")
    screenshot.mkdir(parents=True, exist_ok=True)
    portal.locator(".aer-exec-view").screenshot(
        path=str(screenshot / "original.png")
    )
