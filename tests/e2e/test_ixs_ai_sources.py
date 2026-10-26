"""IA parcial: cargas por API y estilos externos, con la vista anterior."""

import copy
from pathlib import Path

import pytest
from playwright.sync_api import expect

from tests.e2e.test_aer_executive import fixed_day as fixed_day
from tests.e2e.test_ixs_effort import state as capture_state
from tests.e2e.test_ixs_executive import PAGE
from tests.e2e.test_ixs_executive import ixs as ixs
from tests.e2e.test_ixs_planning_transport import planning as planning
from tests.e2e.test_project_detail_entry import project_detail as project_detail

pytestmark = pytest.mark.django_db(transaction=True)


@pytest.fixture
def ia(portal, planning, monkeypatch):
    from apps.portal.api import project_ai as api
    from apps.portal.api import project_detail as detail

    plan, azure, _, _ = planning
    responses = {
        "azure": azure,
        "plan": plan,
        "resources": {
            "ok": True,
            "filas": [
                {"nombre": "Ana Pérez", "activo": True, "horasEstimadas": 20}
            ],
        },
        "clockify": {
            "ok": True,
            "registros": [
                {"recurso": "Ana Pérez", "duracion": 8, "fecha": "2026-10-21"}
            ],
        },
        "cliente": {
            "ok": True,
            "cliente": {"cliente": {"documentos": []}},
            "acciones": {"filas": []},
        },
        "raid": {"ok": True, "registros": []},
        "memoria": {"ok": True, "actual": None, "anterior": None},
        "minutas": {
            "ok": True,
            "filas": [
                {
                    "uid": "m1",
                    "tema": "Seguimiento semanal",
                    "fecha": "2026-10-21",
                    "contenido": "Acuerdos documentados de la reunión",
                }
            ],
        },
        "analysis": {
            "ok": True,
            "fecha": "21/10/2026",
            "analisis": {
                "resumen": [{"texto": "Análisis guardado", "evidencias": []}],
                "hallazgos": [],
                "alertas": [],
                "recomendaciones": [],
            },
            "evidencias": [],
        },
        "folders": {
            "ok": True,
            "carpetas": ["documentos-001"],
            "transcripciones": ["transcripciones-001"],
        },
        "files": {
            "ok": True,
            "files": [
                {
                    "id": "documento-001",
                    "nombre": "Minuta de seguimiento",
                    "tipo": "documentos",
                    "fecha": "2026-10-21",
                    "url": "https://drive.google.com/file/d/documento-001",
                    "legible": True,
                    "minuta": True,
                }
            ],
        },
    }
    calls = []

    def source(key):
        def read(*args):
            calls.append((key, args))
            return copy.deepcopy(responses[key])

        return read

    monkeypatch.setattr(api.ai_rpc, "build_ixs_store", lambda: None)
    monkeypatch.setattr(api.ai_rpc, "build_drive_context", lambda: None)
    monkeypatch.setattr(api.ixs_rpc, "build_store_sheets", lambda: None)

    def forbidden():
        raise AssertionError("Unexpected model access")

    monkeypatch.setattr(api.ai_rpc, "build_claude", forbidden)
    for module, name, key in [
        (detail, "get_ixs_panel", "azure"),
        (detail, "planning_dashboard", "plan"),
        (detail, "resources_dashboard", "resources"),
        (detail, "records_dashboard", "clockify"),
        (detail.ixs_rpc, "list_raid", "raid"),
        (api.ixs_client, "read_client_actions", "cliente"),
        (api.ixs_ai, "read_memory", "memoria"),
        (api.ixs_ai, "read_minutes", "minutas"),
        (api.ixs_ai, "read_analysis", "analysis"),
        (api.ixs_drive, "read_config", "folders"),
        (api.ixs_drive, "list_files", "files"),
    ]:
        monkeypatch.setattr(module, name, source(key))
    methods = dict(
        zip(
            [
                "obtenerPanelAzureProyectoIXS",
                "ixsPlanLeer",
                "ixsRecursosLeer",
                "getRegistrosClockifyProyecto",
                "ixsClienteAccionesLeer",
                "ixsRaidListarProyecto",
                "ixsIAMemoriaLeer",
                "ixsIAMinutasLeer",
                "ixsIAAnalisisLeer",
                "ixsIADriveConfigLeer",
                "ixsIADriveListar",
            ],
            [
                "azure",
                "plan",
                "resources",
                "clockify",
                "cliente",
                "raid",
                "memoria",
                "minutas",
                "analysis",
                "folders",
                "files",
            ],
            strict=True,
        )
    )

    def rpc(route):
        name = route.request.url.rstrip("/").rsplit("/", 1)[-1]
        if name in methods:
            route.fulfill(json={"ok": True, "result": responses[methods[name]]})
        else:
            route.fallback()

    portal.route("**/api/rpc/**", rpc)
    return responses, calls


def enter(portal, previous=False, wait=True):
    portal.goto(portal.base + PAGE + ("?vista=anterior" if previous else ""))
    portal.locator(".ixs-nav").get_by_role(
        "button", name="IA", exact=True
    ).click()
    expect(
        portal.get_by_text("Centro de Inteligencia del Proyecto", exact=True)
    ).to_be_visible()
    if wait:
        portal.wait_for_load_state("networkidle")


@pytest.mark.parametrize("width", [1450, 900, 390])
@pytest.mark.parametrize(
    "variant", ["full", "empty", "partial", "comparable", "incomplete"]
)
def test_same_view_and_external_styles(portal, ia, fixed_day, width, variant):
    responses, _ = ia
    if variant == "empty":
        responses["analysis"] = {"ok": True, "analisis": None}
        responses["minutas"]["filas"] = []
        responses["files"]["files"] = []
        responses["folders"].update(carpetas=[], transcripciones=[])
    elif variant == "partial":
        responses["clockify"] = {"ok": False, "error": "Clockify no disponible"}
        responses["analysis"] = {"ok": False, "error": "Análisis no disponible"}
    elif variant in {"comparable", "incomplete"}:
        responses["memoria"]["actual"] = {
            "fecha": "2026-10-01",
            "analisis": {},
            "snapshot": {
                "fuentes": ["azure", "clockify"]
                if variant == "comparable"
                else [],
                "horas": 12,
                "workItems": [],
                "raidIds": [],
                "acciones": [],
            },
        }
        responses["resources"]["filas"].extend(
            [
                {"nombre": "Sin presupuesto", "horasEstimadas": 0},
                {"nombre": "Excedido", "horasEstimadas": 2},
                {"nombre": "Inactivo", "activo": False, "horasEstimadas": 5},
            ]
        )
        responses["clockify"]["registros"].append(
            {"recurso": "Excedido", "duracion": 5, "fecha": "2026-10-21"}
        )
    portal.set_viewport_size({"width": width, "height": 1000})
    directory = (
        Path("tmp/migration/project_detail/ixs_ai_sources")
        / variant
        / str(width)
    )
    directory.mkdir(parents=True, exist_ok=True)
    states = []
    for previous in [True, False]:
        enter(portal, previous)
        portal.mouse.move(0, 0)
        states.append(
            capture_state(portal, "#ixs-tab-contenido, #ixs-tab-contenido *")
        )
        portal.screenshot(
            path=str(directory / ("old.png" if previous else "new.png")),
            full_page=True,
        )
    assert states[0] == states[1]
    for id in ["ixs-ia-styles", "ixai-ref-styles", "ixs-ia-extended-style"]:
        expect(portal.locator("link#" + id)).to_have_count(1)
        expect(portal.locator("style#" + id)).to_have_count(0)


def test_modular_panels_safe_text_and_resource_navigation(
    portal, ia, fixed_day
):
    responses, _ = ia
    text = '<img src=x onerror="window.injected=true">'
    responses["resources"]["filas"][0]["nombre"] = text
    responses["memoria"]["actual"] = {
        "fecha": text,
        "analisis": {},
        "snapshot": {
            "fuentes": ["azure", "clockify"],
            "horas": 0,
        },
    }
    enter(portal)
    panel = portal.locator(".ixai-two")
    expect(panel).to_contain_text(text)
    expect(panel.locator("img, [onclick]")).to_have_count(0)
    assert portal.evaluate("window.injected === undefined")
    portal.evaluate("""() => {
      const view=window.beeIxsAiView,render=view.render;
      window.panelCalls = 0;
      view.render=(target,state,env)=>render(target,state,{
        ...env,panels:(...args)=>{
          window.panelCalls++;return env.panels(...args);
        }
      });
      try {ixsIAPintar();} finally {view.render=render;}
    }""")
    assert portal.evaluate("window.panelCalls") == 1
    portal.get_by_role("button", name="Ver recursos", exact=True).click()
    expect(
        portal.locator(".ixs-nav").get_by_role(
            "button", name="Recursos", exact=True
        )
    ).to_have_class("active")


def test_initial_reads_use_api_without_model_or_rpc(portal, ia, fixed_day):
    requests = []
    portal.on("request", lambda request: requests.append(request.url))
    enter(portal)
    expect(portal.locator(".ixai-meta").first).to_contain_text(
        "Sincronizado correctamente"
    )
    expect(portal.locator("#ixs-tab-contenido")).to_contain_text(
        "Análisis guardado"
    )
    for path in [
        "/planeacion/azure/",
        "/planeacion/",
        "/recursos/",
        "/registros/",
        "/cliente/",
        "/raid-registro/",
        "/ia/memoria/",
        "/ia/minutas/",
        "/ia/analisis/",
        "/ia/drive/carpetas/",
        "/ia/drive/archivos/",
    ]:
        assert any(path in url for url in requests), path
    assert not any("/api/rpc/" in url for url in requests)


def test_calculations_use_modular_model_with_original_results(
    portal, ia, fixed_day
):
    enter(portal)
    from tests.e2e.project_reference import load_project_reference

    load_project_reference(portal)
    result = portal.evaluate("""() => {
      const model = window.beeIxsAiModel, adapters=window.beeIxsAdapters;
      const calls=[];
      window.beeIxsAdapters={...adapters};
      for(const key of ['context','snapshot','changes','capacity'])
        window.beeIxsAdapters[key]=(...args)=>{
          calls.push(key);return adapters[key](...args);
        };
      const read = () => JSON.parse(JSON.stringify({
        context: ixsIAContexto(), snapshot: ixsIASnapshot(),
        changes: ixsIACambios(), capacity: ixsIACapacidad()
      }));
      try {
        const modern = read();
        window.beeIxsAiModel = null;
        window.beeIxsAdapters = null;
        return { modern, original: read(), calls };
      } finally {
        window.beeIxsAiModel = model;window.beeIxsAdapters=adapters;
      }
    }""")
    assert result["modern"] == result["original"]
    assert set(result["calls"]) == {
        "context",
        "snapshot",
        "changes",
        "capacity",
    }


def test_partial_source_can_retry_without_losing_other_sources(
    portal, ia, fixed_day
):
    responses, _ = ia
    responses["clockify"] = {"ok": False, "error": "Clockify no disponible"}
    enter(portal)
    expect(portal.locator(".ixai-sources")).to_contain_text(
        "Clockify no disponible"
    )
    responses["clockify"] = {"ok": True, "registros": []}
    portal.evaluate("ixsIACargarFuentes()")
    expect(portal.locator(".ixai-meta").first).to_contain_text(
        "Sincronizado correctamente"
    )


def test_drive_does_not_list_files_without_folders(portal, ia, fixed_day):
    responses, calls = ia
    responses["folders"].update(carpetas=[], transcripciones=[])
    enter(portal)
    assert not any(key == "files" for key, _ in calls)


def test_old_history_cannot_replace_reentered_history(portal, ia, fixed_day):
    held = []
    path = "**/screens/proyectos/AMK.008/ia/analisis/"

    def first(route):
        if not held:
            held.append(route)
        else:
            route.fallback()

    portal.route(path, first)
    enter(portal, wait=False)
    portal.locator(".ixs-nav").get_by_role(
        "button", name="Ejecutivo", exact=True
    ).click()
    portal.locator(".ixs-nav").get_by_role(
        "button", name="IA", exact=True
    ).click()
    expect(portal.locator("#ixs-tab-contenido")).to_contain_text(
        "Análisis guardado"
    )
    held[0].fulfill(
        json={
            "data": {
                "ok": True,
                "analisis": {"resumen": [{"texto": "Análisis viejo"}]},
            },
            "meta": {},
        }
    )
    portal.wait_for_load_state("networkidle")
    expect(portal.locator("#ixs-tab-contenido")).not_to_contain_text(
        "Análisis viejo"
    )
