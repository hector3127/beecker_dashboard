"""Planeación modular: modelos, presentación, carga y navegación."""

import copy
from pathlib import Path

import pytest
from playwright.sync_api import expect

from tests.e2e.test_aer_executive import fixed_day as fixed_day
from tests.e2e.test_ixs_effort import state as capture_state
from tests.e2e.test_ixs_executive import ixs as ixs
from tests.e2e.test_ixs_planning_transport import open_planning
from tests.e2e.test_ixs_planning_transport import planning as planning
from tests.e2e.test_project_detail_entry import project_detail as project_detail

pytestmark = pytest.mark.django_db(transaction=True)
PAGE = "/proyectos/AMK.008/"


def enter(portal, previous=False):
    portal.goto(portal.base + PAGE + ("?vista=anterior" if previous else ""))
    portal.locator(".ixs-nav").get_by_role(
        "button", name="Planeación", exact=True
    ).click()


@pytest.mark.parametrize("width", [1450, 900, 390])
@pytest.mark.parametrize(
    "variant",
    [
        "empty",
        "plan_error",
        "azure_error",
        "attention",
        "markers",
        "missing_text",
    ],
)
def test_all_planning_elements_match_previous(
    portal, planning, ixs, fixed_day, width, variant
):
    plan, azure, _, _ = planning
    data, _ = ixs
    if variant == "empty":
        data.clear()
        data.update({"proyecto": {"id": "AMK.008"}})
        plan["vacaciones"] = plan["compromisos"] = []
        azure["items"] = azure["allItems"] = []
        ixs[1]["stages_dashboard"].update(
            hitos=[], historialCompleto=[], suspensiones=[]
        )
    elif variant == "plan_error":
        plan.update(ok=False, error="No se pudo cargar la planeación.")
    elif variant == "azure_error":
        azure.update(ok=False, error="Azure no disponible.")
    elif variant == "attention":
        plan["vacaciones"].append(
            {
                "uid": "cancel",
                "recurso": "ANA PEREZ",
                "inicio": "2026-10-26",
                "fin": "2026-10-30",
                "estado": "Cancelada",
            }
        )
        azure["items"].append(
            {
                "id": 103,
                "titulo": "Entrega próxima",
                "asignadoA": "Luis",
                "estado": "Blocked",
                "fechaLimiteDev": "2026-10-26",
                "iterationPath": "AMK\\QA",
            }
        )
    elif variant == "markers":
        data["hitosAdicionales"].append(
            {
                **data["hitosAdicionales"][0],
                "tipo": "QA",
                "observacion": "Mismo día",
            }
        )
    if variant == "missing_text":
        azure["items"][0].update(id=None, titulo=None, asignadoA=None)
    portal.set_viewport_size({"width": width, "height": 1000})
    states = []
    directory = (
        Path("tmp/migration/project_detail/ixs_planning_view")
        / variant
        / str(width)
    )
    directory.mkdir(parents=True, exist_ok=True)
    for previous in [True, False]:
        enter(portal, previous)
        portal.wait_for_load_state("networkidle")
        states.append(
            capture_state(portal, "#ixs-tab-contenido, #ixs-tab-contenido *")
        )
        portal.screenshot(
            path=str(directory / ("old.png" if previous else "new.png")),
            full_page=True,
        )
    assert states[0] == states[1]
    expect(portal.locator("#ixs-tab-contenido")).to_have_attribute(
        "data-renderer", "modular-planning"
    )
    assert (
        portal.locator(
            "#ixs-tab-contenido [onclick], #ixs-tab-contenido [onchange], "
            "#ixs-tab-contenido [oninput]"
        ).count()
        == 0
    )


@pytest.mark.parametrize("width", [1450, 390])
def test_loading_matches_previous(portal, planning, fixed_day, width):
    plan, azure, _, _ = planning
    portal.set_viewport_size({"width": width, "height": 1000})
    states = []
    directory = Path(
        "tmp/migration/project_detail/ixs_planning_view/loading"
    ) / str(width)
    directory.mkdir(parents=True, exist_ok=True)

    def capture_into(routes):
        return lambda route: routes.append(route)

    for previous in [True, False]:
        held = []
        hold = capture_into(held)

        paths = (
            [
                "**/api/rpc/ixsPlanLeer/",
                "**/api/rpc/obtenerPanelAzureProyectoIXS/",
            ]
            if previous
            else [
                "**/screens/proyectos/AMK.008/planeacion/",
                "**/screens/proyectos/AMK.008/planeacion/azure/",
            ]
        )
        for path in paths:
            portal.route(path, hold)
        enter(portal, previous)
        expect(portal.locator("#ixs-tab-contenido")).to_contain_text(
            "Cargando planeación…"
        )
        portal.wait_for_function(
            "ixsProyectoActual._resourceStatesLoaded === true"
        )
        assert len(held) == 2
        states.append(
            capture_state(portal, "#ixs-tab-contenido, #ixs-tab-contenido *")
        )
        portal.screenshot(
            path=str(directory / ("old.png" if previous else "new.png")),
            full_page=True,
        )
        for route in held:
            result = (
                azure
                if "Azure" in route.request.url
                or "/azure/" in route.request.url
                else plan
            )
            route.fulfill(
                json={"ok": True, "result": result}
                if previous
                else {"data": result, "meta": {}}
            )
        portal.wait_for_load_state("networkidle")
        for path in paths:
            portal.unroute(path, hold)
    assert states[0] == states[1]


def test_late_reads_do_not_replace_reentered_planning(
    portal, planning, fixed_day
):
    plan, azure, _, _ = planning
    portal.goto(portal.base + PAGE)
    portal.wait_for_load_state("networkidle")
    held = []

    def hold_first(route):
        if len(held) < 2:
            held.append(route)
        else:
            route.fallback()

    portal.route("**/screens/proyectos/AMK.008/planeacion/**", hold_first)
    portal.locator(".ixs-nav").get_by_role(
        "button", name="Planeación", exact=True
    ).click()
    expect(portal.locator("#ixs-tab-contenido")).to_contain_text(
        "Cargando planeación…"
    )
    portal.locator(".ixs-nav").get_by_role(
        "button", name="Ejecutivo", exact=True
    ).click()
    portal.locator(".ixs-nav").get_by_role(
        "button", name="Planeación", exact=True
    ).click()
    expect(portal.locator("#ixs-plan-vacaciones")).to_contain_text("Ana Pérez")
    assert len(held) == 2
    for route in held:
        route.fulfill(
            json={
                "data": {
                    "ok": True,
                    "items": [],
                    "vacaciones": [],
                    "compromisos": [],
                },
                "meta": {},
            }
        )
    portal.wait_for_load_state("networkidle")
    expect(portal.locator("#ixs-plan-vacaciones")).to_contain_text("Ana Pérez")
    expect(portal.locator("#ixs-azure-table tbody tr")).to_have_count(2)


def test_buttons_and_work_item_events_keep_their_existing_actions(
    portal, planning, fixed_day, monkeypatch
):
    from apps.portal.api import project_detail as api

    open_planning(portal)
    calls = []

    def save(*args):
        calls.append(args)
        return {"ok": True}

    monkeypatch.setattr(api.daily, "save_work_item_progress", save)
    first = portal.locator("#wi-row-101")
    first.locator("td:nth-child(5) input").fill("60")
    first.locator("td:nth-child(5) input").dispatch_event("change")
    expect(portal.locator("#wi-avance-101")).to_contain_text("48%")
    assert calls[0] == (101, "devConstruido", 60)
    portal.get_by_role("button", name="Ver todas", exact=True).click()
    expect(portal.locator("#ixs-plan-vacaciones")).to_be_in_viewport()
    portal.get_by_role("button", name="Comunicados", exact=False).click()
    expect(portal.locator("#ixe-overlay")).to_have_count(1)
    portal.evaluate("ixsCerrarExtension()")
    portal.get_by_role(
        "button", name="Ver en Azure DevOps ↗", exact=True
    ).click()
    expect(portal.locator(".ixs-nav button.active")).to_have_text(
        "Azure DevOps"
    )


def test_timeline_click_opens_existing_milestone_editor(
    portal, planning, ixs, fixed_day
):
    data, _ = ixs
    data["hitosAdicionales"] = [
        {
            "tipo": "Demo",
            "indice": 7,
            "fecha": "2026-09-10",
            "observacion": "Validación con cliente",
        }
    ]

    def types(route):
        route.fulfill(json={"ok": True, "result": ["Demo"]})

    portal.route("**/api/rpc/obtenerTiposHitosExistentes/", types)
    open_planning(portal)
    portal.locator("#ixs-gantt-historico button.ixs-time-mark").first.click()
    expect(portal.locator("#modal-hito-overlay")).to_have_count(1)
    expect(portal.locator(".mh-fecha")).to_have_value("2026-09-10")
    expect(portal.locator(".mh-obs")).to_have_value("Validación con cliente")
    expect(portal.locator("#mh-filas-container > div")).to_have_attribute(
        "data-edit-indice", "7"
    )


def test_historical_response_updates_gantt_without_restoring_legacy_dom(
    portal, planning, ixs, fixed_day
):
    data, responses = ixs
    data["hitos"] = data["historialCompleto"] = []
    held = []
    portal.route(
        "**/screens/proyectos/AMK.008/etapas/", lambda route: held.append(route)
    )
    enter(portal)
    expect(portal.locator("#ixs-plan-vacaciones")).to_contain_text("Ana Pérez")
    expect(portal.locator("#ixs-gantt-historico")).not_to_contain_text(
        "Ejecución real"
    )
    assert len(held) == 1
    held[0].fulfill(json={"data": responses["stages_dashboard"], "meta": {}})
    expect(portal.locator("#ixs-gantt-historico")).to_contain_text(
        "Ejecución real"
    )
    expect(portal.locator("#ixs-tab-contenido")).to_have_attribute(
        "data-renderer", "modular-planning"
    )
    assert portal.locator("#ixs-gantt-historico [onclick]").count() == 0


def test_source_text_is_rendered_safely(portal, planning, fixed_day):
    plan, azure, _, _ = planning
    text = '<img src=x onerror="window.planningInjected=true">'
    plan["vacaciones"][0]["comentarios"] = text
    azure["items"][0]["titulo"] = text
    azure["items"][0]["iterationPath"] = text
    open_planning(portal)
    expect(portal.locator("#ixs-plan-vacaciones")).to_contain_text(text)
    expect(portal.locator("#ixs-azure-table")).to_contain_text(text)
    assert portal.locator("#ixs-tab-contenido img").count() == 0
    assert portal.evaluate("window.planningInjected") is None


def test_late_response_cannot_replace_another_project(
    portal, planning, ixs, fixed_day
):
    portal.goto(portal.base + PAGE)
    portal.wait_for_load_state("networkidle")
    held = []
    portal.route(
        "**/screens/proyectos/AMK.008/planeacion/**",
        lambda route: held.append(route),
    )
    portal.locator(".ixs-nav").get_by_role(
        "button", name="Planeación", exact=True
    ).click()
    expect(portal.locator("#ixs-tab-contenido")).to_contain_text(
        "Cargando planeación…"
    )
    other = copy.deepcopy(ixs[0])
    other["proyecto"]["id"] = "OTHER"
    portal.evaluate("data=>renderDashboardIXBSaaSRaaS(data)", other)
    portal.locator(".ixs-nav").get_by_role(
        "button", name="Planeación", exact=True
    ).click()
    expect(portal.locator("#ixs-plan-vacaciones")).to_contain_text("Ana Pérez")
    assert len(held) == 2
    for route in held:
        route.fulfill(
            json={
                "data": {
                    "ok": True,
                    "items": [],
                    "vacaciones": [],
                    "compromisos": [],
                },
                "meta": {},
            }
        )
    portal.wait_for_load_state("networkidle")
    expect(portal.locator(".ixs-title")).to_contain_text("OTHER")
    expect(portal.locator("#ixs-plan-vacaciones")).to_contain_text("Ana Pérez")
    expect(portal.locator("#ixs-azure-table tbody tr")).to_have_count(2)
