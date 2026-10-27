"""Ejecutivo AER: paridad, navegación, fuentes vacías y texto seguro."""

import json
from itertools import zip_longest
from pathlib import Path

import pytest
from playwright.sync_api import expect

from tests.e2e.frozen.aer_executive_support import input_digest, prepare, state
from tests.e2e.frozen.aer_executive_support import (
    production_site as production_site,
)
from tests.e2e.test_project_detail_entry import project_detail as project_detail

pytestmark = [
    pytest.mark.django_db(transaction=True),
    pytest.mark.usefixtures("production_site", "enforced_csp"),
]
PAGE = "/proyectos/AER.001/"


@pytest.fixture
def fixed_day(portal):
    portal.add_init_script("""{
      const OriginalDate = Date;
      window.Date = class extends OriginalDate {
        constructor(...args) {
          super(...(args.length ? args : ['2026-10-23T18:00:00Z']));
        }
        static now() { return +new OriginalDate('2026-10-23T18:00:00Z'); }
      };
    }""")


@pytest.mark.parametrize("variant", ["full", "empty", "attention"])
@pytest.mark.parametrize("width", [1450, 900, 390])
def test_all_executive_elements_match(
    portal, project_detail, fixed_day, variant, width
):
    _, data = project_detail
    prepare(data, variant)
    portal.set_viewport_size({"width": width, "height": 1000})
    reference = json.loads(
        Path(
            f"tests/e2e/frozen/aer_executive/{variant}-{width}.json"
        ).read_text(encoding="utf-8")
    )
    assert (
        reference["schema"] == 1
        and reference["source"] == "approved_current_design"
    )
    assert reference["variant"] == variant
    assert reference["viewport"] == {"width": width, "height": 1000}
    assert reference["input_sha256"] == input_digest(data)
    requests = []
    portal.on("request", lambda request: requests.append(request.url))
    portal.goto(portal.base + PAGE)
    before, after = reference["elements"], state(portal)
    out = Path(f"tmp/frozen-browser/aer_executive/{variant}-{width}")
    out.mkdir(parents=True, exist_ok=True)
    portal.locator(".aer-exec-view").screenshot(path=str(out / "current.png"))
    (out / "differences.json").write_text(
        json.dumps(
            {
                "approved_count": len(before),
                "current_count": len(after),
                "elements": [
                    {"index": i, "approved": a, "current": b}
                    for i, (a, b) in enumerate(zip_longest(before, after))
                    if a != b
                ],
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    assert after == before
    assert not any(
        "/api/rpc/" in url or "/static/portal/js/" in url for url in requests
    )
    expect(portal.locator(".aer-exec-view")).to_have_attribute(
        "data-renderer", "modular"
    )
    assert portal.locator(".aer-exec-view [onclick]").count() == 0
    assert portal.locator("style#aer-dashboard-styles").count() == 0
    assert portal.locator("link#aer-dashboard-styles").count() == 1


@pytest.mark.parametrize(
    "label,tab",
    [
        ("Ver todas las acciones →", "Acciones"),
        ("Próximos hitos / decisiones (30 días)", "Planeación"),
        ("Riesgos y dependencias", "Riesgos"),
    ],
)
def test_links_keep_tab_navigation_with_keyboard(
    portal, project_detail, label, tab
):
    portal.goto(portal.base + PAGE)
    if label.startswith("Ver todas"):
        link = portal.get_by_role("link", name=label)
    else:
        link = (
            portal.locator(".aer-exec-grid3 .aer-card")
            .filter(has_text=label)
            .get_by_role("link", name="Ver todos →")
        )
    link.focus()
    link.press("Enter")
    expect(portal.locator(".aer-tabs .active")).to_have_text(tab)
    portal.locator(".aer-tabs").get_by_role(
        "button", name="Ejecutivo", exact=True
    ).click()
    expect(portal.locator(".aer-exec-view")).to_have_attribute(
        "data-renderer", "modular"
    )


def test_source_text_is_not_html(portal, project_detail):
    _, data = project_detail
    text = '<img src=x onerror="window.executiveInjected=true">'
    data["kpis"]["healthLabel"] = text
    data["riesgos"]["criticos"][0]["riesgo"] = text
    portal.goto(portal.base + PAGE)
    expect(portal.locator(".aer-exec-view")).to_contain_text(text)
    assert portal.locator(".aer-exec-view img").count() == 0
    assert portal.evaluate("window.executiveInjected") is None
