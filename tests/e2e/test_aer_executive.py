"""Ejecutivo AER: paridad, navegación, fuentes vacías y texto seguro."""

import pytest
from playwright.sync_api import expect

from tests.e2e.aer_executive_support import (
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
