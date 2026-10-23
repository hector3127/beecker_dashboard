"""IA: vista, formularios y acciones modulares con proveedores simulados."""

import copy
from pathlib import Path

import pytest
from playwright.sync_api import expect

from tests.e2e.test_ixs_ai_sources import (
    capture_state,
    enter,
)
from tests.e2e.test_ixs_ai_sources import (
    fixed_day as fixed_day,
)
from tests.e2e.test_ixs_ai_sources import (
    ia as ia,
)
from tests.e2e.test_ixs_ai_sources import (
    ixs as ixs,
)
from tests.e2e.test_ixs_ai_sources import (
    planning as planning,
)
from tests.e2e.test_ixs_ai_sources import (
    project_detail as project_detail,
)

pytestmark = pytest.mark.django_db(transaction=True)


@pytest.fixture
def actions(portal, ia):
    responses, _ = ia
    analysis = responses["analysis"]["analisis"]
    item = {
        "titulo": "Revisar entrega",
        "detalle": "Validar fecha y responsable",
        "fuente": "Azure",
        "prioridad": "Alta",
        "evidencias": ["PR-1"],
    }
    analysis.update(
        hallazgos=[copy.deepcopy(item)] * 4,
        alertas=[copy.deepcopy(item)],
        recomendaciones=[copy.deepcopy(item)] * 5,
    )
    responses["analysis"]["evidencias"] = [
        {"id": "PR-1", "fuente": "Proyecto", "texto": "Evidencia guardada"}
    ]
    responses["files"]["files"].extend(
        [
            {
                "id": "t1",
                "nombre": "Transcripción",
                "tipo": "transcripciones",
                "fecha": "2026-10-21",
                "legible": True,
                "url": "https://drive.google.com/file/d/t1",
            },
            {
                "id": "t2",
                "nombre": "Audio",
                "tipo": "transcripciones",
                "fecha": "2026-10-21",
                "legible": False,
                "url": "https://drive.google.com/file/d/t2",
            },
        ]
    )
    responses["cliente"]["cliente"] = {
        "documentos": [
            {
                "nombre": "Documento local",
                "tipo": "Acuerdo",
                "url": "https://example.com/documento",
            }
        ]
    }
    results = {
        "analizar/": copy.deepcopy(responses["analysis"]),
        "preguntar/": {"ok": True, "texto": "Borrador simulado"},
        "memoria/guardar/": {
            "ok": True,
            "actual": {
                "fecha": "2026-10-23",
                "analisis": {},
                "snapshot": {"fuentes": ["azure", "clockify"], "horas": 0},
            },
        },
        "minutas/guardar/": {
            "ok": True,
            "filas": [
                {
                    "tema": "Guardada",
                    "fecha": "2026-10-23",
                    "contenido": "Contenido guardado",
                }
            ],
        },
        "drive/carpetas/guardar/": {"ok": True},
        "drive/carpetas/quitar/": {"ok": True},
        "drive/documento/leer/": {
            "ok": True,
            "nombre": "Documento leído",
            "fecha": "2026-10-21",
            "contenido": "Contenido original",
            "truncado": True,
        },
        "drive/minuta/generar/": {"ok": True, "texto": "Minuta generada"},
        "accion/guardar/": {"ok": True},
    }
    rpc = dict(
        zip(
            [
                "ixsIAAnalizar",
                "ixsIAPreguntar",
                "ixsIAMemoriaActualizar",
                "ixsIAMinutaGuardar",
                "ixsIADriveConfigGuardar",
                "ixsIADriveConfigQuitar",
                "ixsIADriveLeerDocumento",
                "ixsIADriveGenerarMinuta",
                "ixsClienteAccionesGuardar",
            ],
            results,
            strict=True,
        )
    )
    calls = []

    def api(route):
        if route.request.method != "POST":
            route.fallback()
            return
        path = route.request.url.split("/ia/", 1)[1]
        calls.append((path, route.request.post_data_json))
        route.fulfill(json={"data": results[path], "meta": {}})

    def previous(route):
        name = route.request.url.rstrip("/").rsplit("/", 1)[-1]
        if name in rpc:
            route.fulfill(json={"ok": True, "result": results[rpc[name]]})
        else:
            route.fallback()

    portal.route("**/api/v1/screens/proyectos/*/ia/**", api)
    portal.route("**/api/rpc/**", previous)
    return results, calls


def open_modal(page, kind):
    label = {
        "evidence": "Ver evidencias",
        "minute": "Ver minuta",
        "create": "Preparar nueva minuta",
        "report": "Generar reporte",
        "communique": "Redactar comunicado",
        "action": "Crear acción",
        "folder": "＋ Agregar carpeta",
        "transcripts": "✦ Generar borrador",
        "document": "Leer",
    }[kind]
    page.get_by_role("button", name=label, exact=True).first.click()
    expect(page.locator("#ixai-modal")).to_be_visible()
    page.wait_for_load_state("networkidle")


@pytest.mark.parametrize("width", [1450, 900, 390])
def test_rich_view_matches_previous(portal, actions, fixed_day, width):
    portal.set_viewport_size({"width": width, "height": 1000})
    states = []
    directory = Path("tmp/migration/project_detail/ixs_ai_full") / str(width)
    directory.mkdir(parents=True, exist_ok=True)
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
    expect(
        portal.locator(
            ".ixai [onclick], .ixai [oninput], "
            ".ixai [onsubmit], .ixai [onchange]"
        )
    ).to_have_count(0)


@pytest.mark.parametrize("width", [1450, 900, 390])
@pytest.mark.parametrize(
    "kind",
    [
        "evidence",
        "minute",
        "create",
        "report",
        "communique",
        "action",
        "folder",
        "transcripts",
        "document",
    ],
)
def test_modals_match_previous(portal, actions, fixed_day, width, kind):
    portal.set_viewport_size({"width": width, "height": 1000})
    states = []
    for previous in [True, False]:
        enter(portal, previous)
        open_modal(portal, kind)
        portal.mouse.move(0, 0)
        states.append(capture_state(portal, "#ixai-modal, #ixai-modal *"))
    assert states[0] == states[1]
    expect(
        portal.locator("#ixai-modal [onclick], #ixai-modal [onsubmit]")
    ).to_have_count(0)


def test_analyze_question_memory_and_draft(portal, actions, fixed_day):
    results, calls = actions
    requests = []
    portal.on("request", lambda request: requests.append(request.url))
    enter(portal)
    portal.get_by_role(
        "button", name="＋ Actualizar análisis", exact=True
    ).click()
    expect(portal.locator("#ixai-analyze")).to_be_enabled()
    portal.locator("#ixai-question").fill("¿Cómo va el proyecto?")
    portal.get_by_role("button", name="Preguntar", exact=True).click()
    expect(portal.locator(".ixai-answer")).to_have_text("Borrador simulado")
    portal.get_by_role("button", name="Actualizar memoria", exact=True).click()
    expect(portal.locator(".ixai-meta").first).to_contain_text("2026-10-23")
    open_modal(portal, "report")
    portal.locator("#ixai-audience").select_option("CTO")
    portal.get_by_role(
        "button", name="Generar borrador con IA", exact=True
    ).click()
    expect(portal.locator("#ixai-draft")).to_have_value("Borrador simulado")
    assert [p for p, _ in calls] == [
        "analizar/",
        "preguntar/",
        "memoria/guardar/",
        "preguntar/",
    ]
    assert calls[0][1]["forzar"] is True
    assert "CTO" in calls[-1][1]["pregunta"]
    assert calls[0][1]["contexto"]["proyecto"] == "AMK.008"
    assert not any("/api/rpc/" in url for url in requests)


def test_minute_save_retries_without_losing_edits(portal, actions, fixed_day):
    results, calls = actions
    results["minutas/guardar/"] = {"ok": False, "error": "Error de guardado"}
    enter(portal)
    open_modal(portal, "create")
    portal.locator("[name=contenido]").fill("Texto revisado manualmente")
    portal.get_by_role("button", name="Guardar minuta", exact=True).click()
    expect(portal.locator("#ixai-form-error")).to_have_text("Error de guardado")
    expect(portal.locator("[name=contenido]")).to_have_value(
        "Texto revisado manualmente"
    )
    results["minutas/guardar/"] = {"ok": True, "filas": []}
    portal.get_by_role("button", name="Guardar minuta", exact=True).click()
    expect(portal.locator("#ixai-modal")).to_have_count(0)
    assert calls[-1][1]["contenido"] == "Texto revisado manualmente"


def test_transcripts_generate_edit_then_save(portal, actions, fixed_day):
    _, calls = actions
    enter(portal)
    portal.locator("#ixai-transcript-results input").first.check()
    open_modal(portal, "transcripts")
    portal.locator("#ixai-modal button[type=submit]").click()
    expect(portal.locator("#ixai-minute-draft")).to_have_value(
        "Minuta generada"
    )
    assert calls[-1][0] == "drive/minuta/generar/"
    assert calls[-1][1]["archivos"] == ["t1"]
    assert not any(p == "minutas/guardar/" for p, _ in calls)
    portal.locator("#ixai-minute-draft").fill("Minuta revisada")
    portal.locator("#ixai-minute-save").click()
    expect(portal.locator("#ixai-modal")).to_have_count(0)
    assert calls[-1][1]["contenido"] == "Minuta revisada"


def test_folder_action_and_document_import(portal, actions, fixed_day):
    _, calls = actions
    enter(portal)
    open_modal(portal, "folder")
    portal.locator("[name=url]").fill(
        "https://drive.google.com/drive/folders/new"
    )
    portal.locator("#ixai-modal button[type=submit]").click()
    expect(portal.locator("#ixai-modal")).to_have_count(0)
    assert calls[-1][0] == "drive/carpetas/guardar/"
    open_modal(portal, "action")
    portal.locator("[name=responsable]").fill("Ana")
    portal.locator("#ixai-modal button[type=submit]").click()
    expect(portal.locator("#ixai-modal")).to_have_count(0)
    assert calls[-1][1]["Responsable"] == "Ana"
    open_modal(portal, "document")
    portal.locator("#ixai-import-drive").click()
    expect(portal.locator("[name=contenido]")).to_have_value(
        "Contenido original"
    )


def test_closed_dialog_ignores_late_generation(portal, actions, fixed_day):
    held = []
    portal.route("**/ia/preguntar/", lambda route: held.append(route))
    enter(portal)
    open_modal(portal, "report")
    portal.get_by_role(
        "button", name="Generar borrador con IA", exact=True
    ).click()
    portal.wait_for_timeout(100)
    portal.locator("#ixai-modal").get_by_role(
        "button", name="✕", exact=True
    ).click()
    portal.get_by_role("button", name="Redactar comunicado", exact=True).click()
    held[0].fulfill(
        json={"data": {"ok": True, "texto": "Respuesta vieja"}, "meta": {}}
    )
    portal.wait_for_load_state("networkidle")
    expect(portal.locator("#ixai-draft")).to_have_value("")


def test_modular_view_never_calls_legacy_renderers_or_forms(
    portal, actions, fixed_day
):
    enter(portal)
    portal.evaluate("""() => {
      for (const name of [
        'ixsIAExtenderVista', 'ixsIAAnalizar', 'ixsIAPreguntar',
        'ixsIAMemoriaGuardar', 'ixsIAReporteBorrador', 'ixsIAEvidencia',
        'ixsIABorradorAccion', 'ixsIACrearMinuta', 'ixsIAVerMinuta',
        'ixsIAConfigurarDrive', 'ixsIAPrepararMinutaDrive'
      ]) window[name] = () => { throw Error('Legacy action: ' + name); };
      ixsIAPintar();
    }""")
    for kind in ["evidence", "create", "action", "folder", "report"]:
        open_modal(portal, kind)
        portal.locator("#ixai-modal").get_by_role(
            "button", name="✕", exact=True
        ).click()


def test_filters_selection_limit_and_safe_recommendations(
    portal, ia, actions, fixed_day
):
    responses, _ = ia
    value = '<img src=x onerror="window.injected=true">'
    responses["analysis"]["analisis"]["recomendaciones"][0]["titulo"] = value
    for i in range(6):
        responses["files"]["files"].append(
            {
                "id": "extra" + str(i),
                "nombre": "Texto " + str(i),
                "tipo": "transcripciones",
                "fecha": "2026-10-21",
                "legible": True,
                "url": "https://example.com/transcript",
            }
        )
    enter(portal)
    expect(portal.locator(".ixai-recs")).to_contain_text(value)
    expect(portal.locator(".ixai-recs img")).to_have_count(0)
    portal.locator("#ixai-doc-filter").fill("Documento local")
    expect(portal.locator("#ixai-doc-results")).to_contain_text(
        "Documento local"
    )
    expect(portal.locator("#ixai-doc-results")).not_to_contain_text(
        "Minuta de seguimiento"
    )
    for i in range(7):
        box = portal.locator(
            "#ixai-transcript-results input:not([disabled])"
        ).nth(i)
        box.click()
    expect(
        portal.locator("#ixai-transcript-results input:checked")
    ).to_have_count(5)
    assert portal.evaluate("window.injected === undefined")
