"""Prueba de humo del diseno de Proyectos: cada pestana a cinco anchos.

Sin desbordamiento horizontal, tablas contenidas, tarjetas y textos legibles,
sin errores de pagina, avisos de CSP ni cargas locales caidas.
"""
# ruff: noqa: F401

import copy
import json
from pathlib import Path

import pytest
from playwright.sync_api import expect

from tests.e2e.conftest import watch
from tests.e2e.frozen.aer_executive_support import production_site
from tests.e2e.test_actions_transport import board as actions_board
from tests.e2e.test_aer_ai_sources import ia as aer_ia
from tests.e2e.test_aer_ai_view import rich as enrich_aer
from tests.e2e.test_aer_effort import effort as aer_effort
from tests.e2e.test_aer_executive import fixed_day as fixed_day
from tests.e2e.test_aer_planning_transport import planning as aer_planning
from tests.e2e.test_aer_resources import resources as aer_resources
from tests.e2e.test_client_tab import CLIENT
from tests.e2e.test_ixs_ai_actions import actions as ai_actions
from tests.e2e.test_ixs_ai_sources import ia as ia
from tests.e2e.test_ixs_client_actions_transport import (
    client_actions as client_actions,
)
from tests.e2e.test_ixs_communication import board as communication
from tests.e2e.test_ixs_effort import effort as effort
from tests.e2e.test_ixs_executive import ixs as ixs
from tests.e2e.test_ixs_planning_transport import planning as planning
from tests.e2e.test_ixs_raid import raid as raid
from tests.e2e.test_ixs_raid_create import alta as alta
from tests.e2e.test_ixs_resources import resources as resources
from tests.e2e.test_project_detail_entry import project_detail as project_detail

pytestmark = [
    pytest.mark.django_db(transaction=True),
    pytest.mark.usefixtures("design_site", "enforced_csp"),
]


@pytest.fixture
def design_site(settings):
    production_site.__wrapped__(settings)


@pytest.fixture
def family(request):
    return request.node.callspec.params["case"].split("/", 1)[0]


CASES = {
    "ixs/Ejecutivo": "ixs",
    "ixs/Planeación": "planning",
    "ixs/Esfuerzo": "effort",
    "ixs/Recursos": "resources",
    "ixs/Gestión RAID": "raid",
    "ixs/Acciones": "actions_board",
    "ixs/Cliente": "client_actions",
    "ixs/Comunicación": "communication",
    "ixs/Azure DevOps": "planning",
    "ixs/IA": "ai_actions",
    "aer/Ejecutivo": "project_detail",
    "aer/Planeación": "aer_planning",
    "aer/Esfuerzo": "aer_effort",
    "aer/Recursos": "aer_resources",
    "aer/Riesgos": "project_detail",
    "aer/Acciones": "actions_board",
    "aer/Cliente": "project_detail",
    "aer/✦ IA": "aer_ia",
}


def capture(page, target):
    page.evaluate("document.fonts.ready")
    page.evaluate("() => new Promise(r => requestAnimationFrame(r))")
    page.mouse.move(0, 0)
    page.screenshot(path=str(target.with_suffix(".png")), full_page=True)
    metrics = page.evaluate("""() => {
      const root=document.querySelector('#view-container');
      const visible=e=>e.getClientRects().length;
      return {viewport:innerWidth,scroll:document.documentElement.scrollWidth,
        metricWidths:[...root.querySelectorAll(
          '.ixs-kpi,.aer-plan-kpi,.aer-exec-kpi,.ixai-grid6>.ixai-card')]
          .filter(visible).map(e=>e.getBoundingClientRect().width),
        truncated:[...root.querySelectorAll('.value,.aer-vivid-value')]
          .filter(e=>visible(e)&&e.clientWidth&&e.scrollWidth>e.clientWidth+1)
          .map(e=>e.textContent),
        tiny:[...root.querySelectorAll('p,td,label,h3,small')]
          .filter(e=>visible(e)&&parseFloat(getComputedStyle(e).fontSize)<12)
          .slice(0,35).map(e=>({cls:e.className,text:e.textContent.slice(0,70),
            size:getComputedStyle(e).fontSize})),
        overflow:[...root.querySelectorAll('*')].filter(e=>{
          const r=e.getBoundingClientRect();
          return r.width&&r.right>innerWidth+1&&
            !e.closest('.pd-table-scroll,.ixs-nav,.aer-tabs,.ixs-timeline');
        }).slice(0,15).map(e=>({cls:e.className,text:e.textContent.slice(0,70),
          right:e.getBoundingClientRect().right})),
        headings:[...root.querySelectorAll('h2,h3')].map(e=>({
          text:e.textContent,font:getComputedStyle(e).fontFamily,
          size:getComputedStyle(e).fontSize})),
        tables:[...root.querySelectorAll('table')].map(t=>({
          rows:t.rows.length,contained:!!t.closest('.pd-table-scroll')}))};
    }""")
    target.with_suffix(".json").write_text(
        json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return metrics


@pytest.mark.parametrize("case", CASES)
def test_populated_section_at_each_size(
    portal, project_detail, fixed_day, request, family, case
):
    fixture = request.getfixturevalue(CASES[case])
    if case == "aer/✦ IA":
        enrich_aer.__wrapped__(fixture)
    if case.endswith("/Cliente"):
        data = fixture[0] if family == "ixs" else fixture[1]
        data["cliente"] = copy.deepcopy(CLIENT)
    tab = case.split("/", 1)[1]
    project = "AMK.008" if family == "ixs" else "AER.001"
    problems = watch(
        portal
    )  # errores de pagina, avisos de CSP, cargas locales caidas
    root = Path("tmp/design-review") / family / tab.replace("✦ ", "")
    root.mkdir(parents=True, exist_ok=True)
    for width in (1450, 900, 600, 390, 320):
        portal.set_viewport_size({"width": width, "height": 1000})
        portal.goto(portal.base + f"/proyectos/{project}/")
        nav = portal.locator(".ixs-nav" if family == "ixs" else ".aer-tabs")
        nav.get_by_role("button", name=tab, exact=True).click()
        portal.wait_for_load_state("networkidle")
        result = capture(portal, root / str(width))
        assert result["scroll"] <= width + 1, (case, width, result)
        assert all(t["contained"] for t in result["tables"])
        assert all(w >= 128 for w in result["metricWidths"]), result
        assert not result["tiny"], (case, width, result["tiny"])
        assert not result["truncated"], (case, width, result["truncated"])
    assert not problems, problems


def test_business_overview_visual_reference(portal, datos):
    target = Path("tmp/design-review/business")
    target.mkdir(parents=True, exist_ok=True)
    for width in (1450, 900, 390):
        portal.set_viewport_size({"width": width, "height": 1000})
        portal.goto(portal.base + "/")
        expect(portal.locator(".executive-cards")).to_be_visible()
        portal.wait_for_load_state("networkidle")
        portal.screenshot(path=str(target / f"{width}.png"), full_page=True)


@pytest.mark.usefixtures("aer_resources")
def test_evaluation_chart_keeps_values_and_round_markers_on_resize(
    portal, fixed_day
):
    portal.goto(portal.base + "/proyectos/AER.001/")
    portal.locator(".aer-tabs").get_by_role(
        "button", name="Recursos", exact=True
    ).click()
    chart = portal.locator("svg[data-evaluation-points]")
    expect(chart).to_be_visible()
    for width in (1450, 900, 390, 320):
        portal.set_viewport_size({"width": width, "height": 1000})
        portal.evaluate("""() => new Promise(resolve => requestAnimationFrame(
          () => requestAnimationFrame(resolve)))""")
        result = chart.evaluate("""svg => ({
          width:svg.viewBox.baseVal.width,
          host:svg.parentElement.clientWidth,
          scores:[...svg.querySelectorAll('text')].map(e=>e.textContent),
          markers:[...svg.querySelectorAll('circle')].map(e=>{
            const r=e.getBoundingClientRect();return [r.width,r.height];
          }),
          positions:[...svg.querySelectorAll('circle')].map(e=>
            e.cx.baseVal.value / svg.viewBox.baseVal.width * 100)
        })""")
        assert abs(result["width"] - result["host"]) <= 1
        assert result["scores"] == ["70", "75", "80", "85", "90"]
        assert result["positions"] == pytest.approx([10, 30, 50, 70, 90])
        assert all(abs(w - h) < 0.5 for w, h in result["markers"])
        assert all(w >= 7 for w, _ in result["markers"])


@pytest.mark.usefixtures("resources")
def test_mobile_resource_table_keeps_names_visible_while_scrolling(
    portal, fixed_day
):
    portal.set_viewport_size({"width": 390, "height": 900})
    portal.goto(portal.base + "/proyectos/AMK.008/")
    portal.locator(".ixs-nav").get_by_role(
        "button", name="Recursos", exact=True
    ).click()
    wrapper = portal.locator(".pd-table-scroll").first
    expect(wrapper).to_be_visible()
    cell = wrapper.locator("tbody tr").first.locator("td").first
    before = cell.bounding_box()
    wrapper.evaluate("e => e.scrollLeft = e.scrollWidth")
    after = cell.bounding_box()
    assert wrapper.evaluate("e => e.scrollLeft") > 0
    assert before and after and abs(before["x"] - after["x"]) <= 1
    expect(cell).to_contain_text("Ana Pérez")


@pytest.mark.parametrize(
    "case",
    [
        "ixs/Planeación",
        "ixs/Recursos",
        "ixs/Gestión RAID",
        "ixs/Acciones",
        "ixs/Cliente",
        "ixs/Comunicación",
        "ixs/IA",
        "aer/Planeación",
        "aer/Recursos",
        "aer/Cliente",
        "aer/✦ IA",
    ],
)
def test_section_editor_fits_and_remains_usable(
    portal, project_detail, fixed_day, request, family, case
):
    fixture = request.getfixturevalue(
        "alta" if case == "ixs/Gestión RAID" else CASES[case]
    )
    if case == "aer/✦ IA":
        enrich_aer.__wrapped__(fixture)
    if case.endswith("/Cliente"):
        data = fixture[0] if family == "ixs" else fixture[1]
        data["cliente"] = copy.deepcopy(CLIENT)
    tab = case.split("/", 1)[1]
    project = "AMK.008" if family == "ixs" else "AER.001"
    root = Path("tmp/design-review/editors") / family / tab.replace("✦ ", "")
    root.mkdir(parents=True, exist_ok=True)
    commands = {
        "ixs/Planeación": "ixsAbrirPlanEditor('vacacion','','')",
        "ixs/Acciones": "aerAbrirAccion()",
        "aer/Planeación": "aerAbrirPlan('p2')",
        "aer/Recursos": "aerAbrirEvaluacion('e1')",
        "aer/✦ IA": "aerIAAbrirConfigMinutas()",
    }
    buttons = {
        "ixs/Recursos": "+ Agregar recurso",
        "ixs/Gestión RAID": "+ Riesgo",
        "ixs/Cliente": "＋ Agregar contacto",
        "aer/Cliente": "＋ Agregar contacto",
        "ixs/Comunicación": "＋ Nuevo comunicado",
        "ixs/IA": "Preparar nueva minuta",
    }
    selector = ".aer-modal,.ixs-recurso-dialog,.ixs-raid-modal,"
    selector += ".bee-com-dialog,.ixai-dialog,.ixs-plan-dialog"
    for width in (1450, 900, 390, 320):
        portal.set_viewport_size({"width": width, "height": 900})
        portal.goto(portal.base + f"/proyectos/{project}/")
        nav = portal.locator(".ixs-nav" if family == "ixs" else ".aer-tabs")
        nav.get_by_role("button", name=tab, exact=True).click()
        portal.wait_for_load_state("networkidle")
        if case in commands:
            portal.evaluate(commands[case])
        else:
            portal.get_by_role("button", name=buttons[case], exact=True).click()
        dialog = portal.locator(selector).filter(visible=True)
        expect(dialog).to_be_visible()
        portal.wait_for_load_state("networkidle")
        box = dialog.bounding_box()
        assert box and box["x"] >= -1 and box["x"] + box["width"] <= width + 1
        assert box["y"] >= -1 and box["y"] + box["height"] <= 901
        assert dialog.evaluate("e => e.scrollWidth <= e.clientWidth+1")
        portal.screenshot(path=str(root / f"{width}.png"), full_page=True)
        controls = dialog.locator("input:not([type=hidden]),select,textarea")
        assert controls.count()
        first = controls.first
        first.focus()
        expect(first).to_be_focused()
        assert dialog.evaluate("""e => [...e.querySelectorAll(
          'input:not([type=hidden]):not([type=checkbox]):not([type=radio]),'
          +'select,textarea')].filter(x=>x.getClientRects().length)
          .every(x=>x.getBoundingClientRect().height>=40)""")
