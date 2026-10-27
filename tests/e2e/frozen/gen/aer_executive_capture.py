"""Explicit capture of the user-approved current design.

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
from tests.e2e.frozen.aer_executive_support import (
    production_site as production_site,
)
from tests.e2e.test_aer_executive import fixed_day as fixed_day
from tests.e2e.test_project_detail_entry import project_detail as project_detail

pytestmark = [
    pytest.mark.django_db(transaction=True),
    pytest.mark.usefixtures("production_site", "enforced_csp"),
]
ROOT = Path("tests/e2e/frozen/aer_executive")


@pytest.mark.parametrize("variant", ["full", "empty", "attention"])
@pytest.mark.parametrize("width", [1450, 900, 390])
def test_capture_current_design(
    portal, project_detail, fixed_day, variant, width
):
    _, data = project_detail
    prepare(data, variant)
    portal.set_viewport_size({"width": width, "height": 1000})
    portal.goto(portal.base + PAGE)
    elements = state(portal)
    assert (
        portal.locator(".aer-exec-view").get_attribute("data-renderer")
        == "modular"
    )
    assert (
        portal.locator('script[src*="portal/js/proyecto_detalle.js"]').count()
        == 0
    )
    document = {
        "schema": 1,
        "source": "approved_current_design",
        "base_commit": "0dbb3f7",
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
                "frontend/static/scripts/pages/project_detail/sections/aer_executive.js",
                "frontend/static/styles/pages/project_detail_aer.css",
                "frontend/templates/pages/project_detail.html",
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
        path=str(screenshot / "approved-current.png")
    )
