"""Explicit current-design capture, outside normal discovery."""

import json
import platform
from pathlib import Path

import pytest

from tests.e2e.frozen.aer_executive_support import (
    production_site as production_site,
)
from tests.e2e.frozen.aer_resources_support import (
    input_digest,
    measure_editor,
    measure_view,
    prepare,
)
from tests.e2e.test_aer_executive import fixed_day as fixed_day
from tests.e2e.test_aer_resources import resources as resources
from tests.e2e.test_project_detail_entry import project_detail as project_detail

pytestmark = [
    pytest.mark.django_db(transaction=True),
    pytest.mark.usefixtures("production_site", "enforced_csp"),
]
ROOT = Path("tests/e2e/frozen/aer_resources")


def save(page, data, name, width, result):
    assert (
        page.locator('script[src*="portal/js/proyecto_detalle.js"]').count()
        == 0
    )
    ROOT.mkdir(parents=True, exist_ok=True)
    value = {
        "schema": 1,
        "source": "project_redesign_delivery_v1",
        "base_commit": "007d76c",
        "viewport": {"width": width, "height": 1000},
        "input_sha256": input_digest(data),
        "browser": page.context.browser.version,
        "platform": platform.system(),
        "state": result,
    }
    (ROOT / f"{name}-{width}.json").write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


@pytest.mark.parametrize("width", [1450, 900, 390])
@pytest.mark.parametrize("variant", ["full", "empty", "selected"])
def test_capture_view(portal, resources, fixed_day, width, variant):
    prepare(resources[0], variant)
    portal.set_viewport_size({"width": width, "height": 1000})
    result = measure_view(portal, variant)
    save(portal, resources[0], f"view-{variant}", width, result)


@pytest.mark.parametrize("width", [1450, 900, 390])
@pytest.mark.parametrize("uid", ["", "e1"])
def test_capture_editor(portal, resources, fixed_day, width, uid):
    portal.set_viewport_size({"width": width, "height": 1000})
    result = measure_editor(portal, uid)
    save(portal, resources[0], f"editor-{uid or 'new'}", width, result)
