"""Inversion conserva datos, filtros y apariencia al separar el frontend."""

from pathlib import Path
from types import SimpleNamespace

import pytest
from playwright.sync_api import expect

from apps.portal.services.investment import classify_investment
from tests.portal.test_investment import GSE

pytestmark = pytest.mark.django_db(transaction=True)
PAGE = "/operativa/inversion/?mes=2026-10"


@pytest.fixture
def investment(monkeypatch, datos):
    state = {"data": GSE, "error": ""}

    def accumulated(*args):
        records = []
        for row in state["data"]["detalle"]:
            if not isinstance(row, dict):
                continue
            kind, _ = classify_investment(row.get("categorias", []))
            if not kind:
                continue
            name = row.get("recurso", "X")
            if name == "X":
                name += row.get("area", "")
            records.append(
                {
                    "resource": name,
                    "project": row.get("proyecto", ""),
                    "category": "commercial"
                    if kind == "comercial"
                    else "operational",
                    "hours": row["horas"],
                    "day": "2025-01-01",
                }
            )
        return {
            "complete": not state["error"],
            "error": state["error"],
            "records": records,
            "projects": 3,
        }

    def roster(*args):
        rows = []
        for row in state["data"]["detalle"]:
            if not isinstance(row, dict):
                continue
            name = row.get("recurso", "X")
            if name == "X":
                name += row.get("area", "")
            rows.append([name, row.get("area", "")])
        return SimpleNamespace(
            headers=["nombre", "rol"], data_rows=rows, role_column=1
        )

    monkeypatch.setattr("apps.portal.views._operativa_investment", accumulated)
    monkeypatch.setattr("apps.portal.views.load_eva1", lambda **kw: None)
    monkeypatch.setattr("apps.portal.views.load_eva2", lambda **kw: None)
    monkeypatch.setattr(
        "core.sheets.factory.build_sheet_repository", lambda: None
    )
    monkeypatch.setattr("apps.gse.services.roster.read_roster_sheet", roster)
    return state


def test_month_totals_bars_and_return(portal, investment):
    portal.goto(portal.base + PAGE)
    expect(
        portal.get_by_role("heading", name="Por especialidad")
    ).to_be_visible()
    assert portal.locator("main").count() == 1
    assert portal.locator("link[href*='pages/investment.css']").count() == 1
    expect(portal.locator(".kp .kv")).to_have_text(
        ["70 horas", "100 horas", "170 horas"]
    )
    expect(portal.locator(".inv-filter")).to_contain_text(
        "Acumulado de proyectos activos"
    )
    expect(portal.locator("tfoot")).to_contain_text("170 h")
    bar = portal.locator(".inv-commercial-types .fill-commercial").first
    track = portal.locator(".inv-commercial-types .tr").first
    assert abs(bar.bounding_box()["width"] - track.bounding_box()["width"]) < 1
    back = portal.get_by_role("link", name="← Regresar a Operativa")
    expect(back).to_have_attribute("href", "/operativa/")
    expect(portal.locator("#mes")).to_have_count(0)
    portal.goto(portal.base + "/operativa/inversion/?mes=2020-01")
    expect(portal.locator(".kp .kv")).to_have_text(
        ["70 horas", "100 horas", "170 horas"]
    )


def test_page_has_no_tabs_and_keeps_its_own_content(portal, investment):
    portal.goto(portal.base + PAGE)

    assert portal.locator(".tabs").count() == 0
    for name in ("EVA 1", "EVA 2", "KPIs de Delivery Managers"):
        assert portal.get_by_role("link", name=name, exact=True).count() == 0
    expect(portal.locator(".inv-kpi")).to_have_count(3)
    expect(portal.locator(".inv-panel")).to_have_count(6)
    expect(portal.locator("#inv-history-chart svg")).to_have_count(1)
    expect(portal.locator("#inv-donut svg")).to_have_count(1)


@pytest.mark.parametrize("width", [1450, 900, 390])
def test_layout_fits_the_screen_without_csp_violations(
    portal, investment, width, enforced_csp
):
    problems = []
    portal.on(
        "console",
        lambda m: (
            problems.append(m.text) if "Content Security" in m.text else None
        ),
    )
    portal.set_viewport_size({"width": width, "height": 1000})
    portal.goto(portal.base + PAGE)

    expect(portal.locator(".inv-kpi").first).to_be_visible()
    assert portal.evaluate(
        "document.documentElement.scrollWidth <= innerWidth + 1"
    )
    assert not problems, problems
    output = Path(f"tmp/migration/investment/{width}")
    output.mkdir(parents=True, exist_ok=True)
    portal.screenshot(path=str(output / "current.png"), full_page=True)


def test_missing_source_is_explained(portal, investment, monkeypatch):
    investment["error"] = "Clockify no disponible"
    portal.goto(portal.base + PAGE)
    expect(portal.locator(".err")).to_contain_text("Clockify no disponible")
    expect(portal.locator(".inv-kpi")).to_have_count(0)
    expect(portal.locator("main")).to_contain_text(
        "No se muestran totales parciales"
    )


def test_saved_previous_link_retains_month_and_current_module(
    portal, investment
):
    portal.goto(portal.base + PAGE + "&vista=anterior")
    expect(portal.locator("#mes")).to_have_count(0)
    expect(portal.locator(".kp .kv")).to_have_text(
        ["70 horas", "100 horas", "170 horas"]
    )
    expect(
        portal.locator('script[src*="pages/investment/main.js"]')
    ).to_have_count(1)


@pytest.mark.parametrize("width", [1450, 900, 390])
def test_person_project_panel_filters_pages_exports_and_closes(
    portal, investment, monkeypatch, width, enforced_csp
):
    details = [
        {
            "recurso": "Analista Uno",
            "area": "DEV",
            "proyecto": "=Demo",
            "categorias": ["Pre-Venta"],
            "horas": 2,
        },
        {
            "recurso": "Analista Uno",
            "area": "DEV",
            "proyecto": "=Demo",
            "categorias": ["Internos"],
            "horas": 3,
        },
    ]
    details += [
        {
            "recurso": "Analista Uno",
            "area": "DEV",
            "proyecto": f"Proyecto {i}",
            "categorias": ["Internos"],
            "horas": 1,
        }
        for i in range(12)
    ]
    details += [
        {
            "recurso": "Otra persona",
            "area": "QA",
            "proyecto": "Otro proyecto",
            "categorias": ["Internos"],
            "horas": 100,
        }
    ]
    investment["data"] = {"ok": True, "detalle": details}
    portal.set_viewport_size({"width": width, "height": 1000})
    portal.goto(portal.base + PAGE)
    trigger = portal.get_by_role("button", name="Analista Uno", exact=True)
    trigger.click()
    panel = portal.locator("#inv-resource-detail")
    expect(panel).to_be_visible()
    expect(panel.locator("h3")).to_have_text("Analista Uno")
    expect(panel.locator(".inv-person-totals strong")).to_have_text(
        ["2 h", "15 h", "17 h"]
    )
    expect(panel.locator(".inv-person-project-table tbody tr")).to_have_count(5)
    expect(panel.locator(".inv-detail-count")).to_have_text(
        "Horas por proyecto (13)"
    )
    expect(trigger).to_have_attribute("aria-pressed", "true")
    panel.get_by_role("button", name="Página siguiente").click()
    expect(panel.locator(".inv-detail-pagination")).to_contain_text("2 / 3")
    panel.get_by_role("combobox", name="Proyectos por página").select_option(
        "25"
    )
    expect(panel.locator(".inv-person-project-table tbody tr")).to_have_count(
        13
    )
    panel.get_by_role("searchbox", name="Buscar proyecto del recurso").fill(
        "=Demo"
    )
    expect(panel.locator(".inv-person-project-table tbody tr")).to_have_count(1)
    expect(panel.locator(".inv-person-project-table tbody")).to_contain_text(
        "5 h"
    )
    expect(panel.locator(".inv-person-project-table")).not_to_contain_text(
        "Otro proyecto"
    )
    with portal.expect_download() as download:
        panel.get_by_role(
            "button", name="Descargar proyectos del recurso"
        ).click()
    text = Path(download.value.path()).read_text(encoding="utf-8-sig")
    assert "'=Demo" in text and "Otra persona" not in text
    assert "Comercial (h)" in text and "Operativa (h)" in text
    assert portal.evaluate(
        "document.documentElement.scrollWidth <= innerWidth + 1"
    )
    output = Path("tmp/design/investment-resource")
    output.mkdir(parents=True, exist_ok=True)
    portal.locator(".inv-resources").screenshot(
        path=str(output / f"detail-{width}.png")
    )
    panel.get_by_role("button", name="Cerrar detalle del recurso").click()
    expect(panel).to_be_hidden()
    expect(trigger).to_be_focused()
    expect(trigger).to_have_attribute("aria-pressed", "false")


def test_bottom_panels_keep_the_compact_two_column_distribution(
    portal, investment
):
    portal.set_viewport_size({"width": 1450, "height": 1000})
    portal.goto(portal.base + PAGE)
    commercial = portal.locator(".inv-commercial-types").bounding_box()
    resources = portal.locator(".inv-resources").bounding_box()
    operational = portal.locator(".inv-operational-projects").bounding_box()
    assert abs(commercial["x"] - resources["x"]) < 2
    assert resources["y"] > commercial["y"]
    assert resources["y"] - commercial["y"] - commercial["height"] < 20
    assert operational["x"] > commercial["x"] + commercial["width"]
    assert abs(operational["y"] - commercial["y"]) < 2
    document_y = portal.locator(".inv-operational-projects").evaluate(
        "e => e.getBoundingClientRect().top + scrollY"
    )
    portal.locator(".inv-person-button").first.click()
    expect(portal.locator("#inv-resource-detail")).to_be_visible()
    after = portal.locator(".inv-operational-projects").bounding_box()
    assert abs(after["x"] - operational["x"]) < 2
    after_y = portal.locator(".inv-operational-projects").evaluate(
        "e => e.getBoundingClientRect().top + scrollY"
    )
    assert abs(after_y - document_y) < 2
