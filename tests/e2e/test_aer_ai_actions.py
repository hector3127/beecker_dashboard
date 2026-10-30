"""IA AER: acciones por API, firmas, respuestas tardías y paridad visual."""

import copy

import pytest
from playwright.sync_api import expect

from tests.e2e.test_aer_ai_sources import enter
from tests.e2e.test_aer_ai_sources import ia as ia
from tests.e2e.test_aer_ai_view import rich as rich
from tests.e2e.test_aer_executive import fixed_day as fixed_day
from tests.e2e.test_project_detail_entry import project_detail as project_detail

pytestmark = pytest.mark.django_db(transaction=True)


@pytest.fixture
def actions(portal, rich, monkeypatch):
    from apps.portal.api import project_aer_ai as api

    responses = {
        "analizar": {
            "ok": True,
            "analisis": {"resumen": ["Análisis nuevo"], "recomendaciones": []},
            "persistido": True,
            "guardadoEn": "2026-10-23 12:00",
            "uso": {"usd": 0.002},
        },
        "generar-resumen": {
            "ok": True,
            "texto": "**Estatus actual:**\nTexto completo del resumen",
            "resumen": {
                "contenido": "**Estatus actual:**\nTexto completo del resumen",
                "guardado": "23/10/2026",
            },
            "persistido": True,
        },
        "preguntar": {"ok": True, "texto": "Respuesta <segura>", "cache": True},
        "correo": {"ok": True, "texto": "Borrador del correo <editable>"},
        "minuta-borrador": {
            "ok": True,
            "texto": "Minuta <editable>",
            "uso": {"usd": 0.001},
        },
        "minuta-drive": {"ok": True, "texto": "Minuta de Drive", "cache": True},
        "minuta-guardar": {"ok": True},
        "config-guardar": {
            "ok": True,
            "config": copy.deepcopy(rich[1]["config"]["config"]),
        },
    }
    rich[1]["prompt"] = {"ok": True, "prompt": "Prompt predeterminado"}
    calls, urls = [], []

    def execute(operation, project, body):
        calls.append((operation, project, body))
        return copy.deepcopy(responses[operation])

    monkeypatch.setattr(api, "execute", execute)
    by_name = {name: op for op, name in api.OPERATIONS.items()}

    def rpc(route):
        name = route.request.url.rstrip("/").rsplit("/", 1)[-1]
        if name in by_name:
            route.fulfill(json={"ok": True, "result": responses[by_name[name]]})
        else:
            route.fallback()

    portal.route("**/api/rpc/**", rpc)
    portal.on("request", lambda r: urls.append(r.url))
    return responses, calls, urls


def click(page, identifier):
    page.locator("#" + identifier).click()


def test_analysis_summary_and_question_use_api(portal, actions, fixed_day):
    enter(portal)
    click(portal, "aeri-analyze")
    expect(portal.locator(".aeri-point").first).to_contain_text(
        "Análisis nuevo"
    )
    operation, project, body = actions[1][-1]
    assert (operation, project, body["forzar"]) == ("analizar", "AER.001", True)
    assert body["contexto"]["id"] == "AER.001"
    portal.locator("#aeri-question").fill("¿Cómo va el proyecto?")
    click(portal, "aeri-ask")
    expect(portal.locator("#aeri-response")).to_contain_text(
        "Respuesta <segura>"
    )
    assert actions[1][-1][2]["texto"] == "¿Cómo va el proyecto?"
    assert portal.locator("#aeri-response img").count() == 0
    portal.locator("#aeri-question").fill("Resume el proyecto para comité")
    click(portal, "aeri-ask")
    expect(portal.locator(".aeri-chat-summary-content")).to_contain_text(
        "Texto completo del resumen"
    )
    assert actions[1][-1][0] == "generar-resumen"
    assert (
        actions[1][-1][2]["datos"]["instrucciones"]
        == "Resume el proyecto para comité"
    )
    click(portal, "aeri-generate-summary")
    expect(portal.locator(".aer-toast").last).to_contain_text(
        "Resumen generado y guardado"
    )
    assert actions[1][-1][2]["datos"]["instrucciones"].startswith(
        "Estado actual,"
    )
    assert not any("/api/rpc/" in url for url in actions[2])


def test_validation_and_mail_retry_keep_draft(portal, actions, fixed_day):
    enter(portal)
    portal.locator("#aeri-question").fill("no")
    click(portal, "aeri-ask")
    expect(portal.locator("#aeri-response")).to_contain_text(
        "Escribe una pregunta"
    )
    assert not actions[1]
    portal.evaluate("aerIACorreo()")
    portal.locator("#aeri-mail-in").fill("no")
    click(portal, "aeri-mail-btn")
    assert not actions[1]
    portal.locator("#aeri-mail-in").fill("Enviar seguimiento al cliente")
    actions[0]["correo"] = {"ok": False, "error": "Error simulado"}
    click(portal, "aeri-mail-btn")
    expect(portal.locator("#aeri-mail-out")).to_contain_text("Error simulado")
    expect(portal.locator("#aeri-mail-in")).to_have_value(
        "Enviar seguimiento al cliente"
    )
    actions[0]["correo"] = {"ok": True, "texto": "Borrador recuperado"}
    click(portal, "aeri-mail-btn")
    expect(portal.locator("#aeri-mail-out")).to_have_text("Borrador recuperado")


def test_minute_notes_save_and_reload_preserve_editable_content(
    portal, actions, fixed_day
):
    enter(portal)
    portal.evaluate("aerIAAbrirMinuta()")
    click(portal, "aeri-minute-generate")
    expect(portal.locator(".aer-toast").last).to_contain_text(
        "al menos 15 caracteres"
    )
    assert not actions[1]
    portal.locator("#aeri-minute-topic").fill("Seguimiento")
    portal.locator("#aeri-minute-notes").fill(
        "Notas reales del seguimiento semanal"
    )
    click(portal, "aeri-minute-generate")
    expect(portal.locator("#aeri-minute-text")).to_have_value(
        "Minuta <editable>"
    )
    assert actions[1][-1][0] == "minuta-borrador"
    assert (
        actions[1][-1][2]["texto"] == "Tema: Seguimiento; Fecha: 2026-10-23; "
        "Notas: Notas reales del seguimiento semanal"
    )
    portal.locator("#aeri-minute-text").fill("Contenido revisado manualmente")
    actions[0]["minuta-guardar"] = {"ok": False, "error": "No guardado"}
    click(portal, "aeri-minute-save")
    expect(portal.locator("#aeri-minute-save")).to_have_text("Reintentar")
    expect(portal.locator("#aeri-minute-text")).to_have_value(
        "Contenido revisado manualmente"
    )
    actions[0]["minuta-guardar"] = {"ok": True}
    click(portal, "aeri-minute-save")
    expect(portal.locator("#aer-modal-back")).to_have_count(0)
    assert actions[1][-1][2] == {
        "datos": {
            "tema": "Seguimiento",
            "fecha": "2026-10-23",
            "contenido": "Contenido revisado manualmente",
        }
    }
    portal.wait_for_function("aerIAState.minutas !== null")


def test_drive_minute_uses_selection_and_exact_fields(
    portal, actions, fixed_day
):
    enter(portal)
    portal.locator(".aeri-driveitem input").nth(0).check()
    portal.locator(".aeri-driveitem input").nth(1).check()
    portal.evaluate("aerIAAbrirMinuta()")
    portal.locator("#aeri-minute-topic").fill("Desde Drive")
    click(portal, "aeri-minute-generate")
    expect(portal.locator("#aeri-minute-text")).to_have_value("Minuta de Drive")
    assert actions[1][-1][0] == "minuta-drive"
    assert actions[1][-1][2]["datos"] == {
        "ids": ["f0", "f1"],
        "tema": "Desde Drive",
        "fecha": "2026-10-23",
        "notas": "",
    }


def test_config_validation_prompt_retry_and_search(
    portal, actions, rich, fixed_day
):
    enter(portal)
    portal.evaluate("aerIAAbrirConfigMinutas()")
    portal.locator("#aeri-folder-url").fill("")
    click(portal, "aeri-folder-save")
    expect(portal.locator("#aeri-config-status")).to_contain_text(
        "Completa los tres campos"
    )
    assert not actions[1]
    portal.get_by_role(
        "button", name="↺ Restablecer prompt predeterminado", exact=True
    ).click()
    expect(portal.locator("#aeri-minute-prompt")).to_have_value(
        "Prompt predeterminado"
    )
    portal.locator("#aeri-folder-url").fill(
        " https://drive.google.com/drive/folders/demo "
    )
    portal.locator("#aeri-folder-name").fill(" ACME ")
    actions[0]["config-guardar"] = {"ok": False, "error": "Fallo al guardar"}
    click(portal, "aeri-folder-save")
    expect(portal.locator("#aeri-config-status")).to_contain_text(
        "Fallo al guardar"
    )
    expect(portal.locator("#aeri-minute-prompt")).to_have_value(
        "Prompt predeterminado"
    )
    actions[0]["config-guardar"] = {
        "ok": True,
        "config": rich[1]["config"]["config"],
    }
    click(portal, "aeri-folder-save-scan")
    expect(portal.locator("#aer-modal-back")).to_have_count(0)
    assert actions[1][-1][2]["datos"]["nombreBusqueda"] == "ACME"
    portal.wait_for_function("!aerIAState.buscando")
    assert portal.evaluate("aerIAState.seleccion") == []


def test_late_mail_does_not_replace_new_form(portal, actions, fixed_day):
    enter(portal)
    held = []
    portal.route("**/ia-aer/correo/", lambda route: held.append(route))
    portal.evaluate("aerIACorreo()")
    portal.locator("#aeri-mail-in").fill("Borrador del primer formulario")
    with portal.expect_request("**/ia-aer/correo/"):
        click(portal, "aeri-mail-btn")
    portal.evaluate("aerIACorreo()")
    portal.locator("#aeri-mail-in").fill("Nuevo formulario")
    held[0].fulfill(json={"data": {"ok": True, "texto": "Viejo"}, "meta": {}})
    portal.wait_for_timeout(150)
    expect(portal.locator("#aeri-mail-out")).to_be_empty()
    expect(portal.locator("#aeri-mail-in")).to_have_value("Nuevo formulario")


def test_late_analysis_ignores_replaced_state_and_duplicate_calls(
    portal, actions, fixed_day
):
    enter(portal)
    held = []
    portal.route("**/ia-aer/analizar/", lambda route: held.append(route))
    with portal.expect_request("**/ia-aer/analizar/"):
        click(portal, "aeri-analyze")
    portal.evaluate("aerIAAnalizar(true)")
    assert len(held) == 1
    portal.evaluate(
        "() => {aerIAState={...aerIAState,analisis:{sentinel:true}};}"
    )
    held[0].fulfill(json={"data": actions[0]["analizar"], "meta": {}})
    portal.wait_for_timeout(150)
    assert portal.evaluate("aerIAState.analisis") == {"sentinel": True}


def test_copy_uses_original_messages_without_sending_data(
    portal, actions, fixed_day
):
    enter(portal)
    portal.evaluate("document.execCommand=()=>true;aerIAVerMinuta(0)")
    portal.get_by_role("button", name="▣ Copiar contenido", exact=True).click()
    expect(portal.locator(".aer-toast").last).to_contain_text(
        "Contenido de la minuta copiado"
    )
    portal.evaluate("aerIAVerResumenEjecutivo()")
    portal.get_by_role("button", name="Copiar texto", exact=True).click()
    expect(portal.locator(".aer-toast").last).to_contain_text("Resumen copiado")
    assert not actions[1]


def test_question_response_keeps_newly_typed_question(
    portal, actions, fixed_day
):
    enter(portal)
    held = []
    portal.route("**/ia-aer/preguntar/", lambda route: held.append(route))
    portal.locator("#aeri-question").fill("Primera pregunta real")
    with portal.expect_request("**/ia-aer/preguntar/"):
        click(portal, "aeri-ask")
    portal.locator("#aeri-question").fill("Siguiente pregunta")
    held[0].fulfill(json={"data": actions[0]["preguntar"], "meta": {}})
    expect(portal.locator("#aeri-response")).to_contain_text(
        "Respuesta <segura>"
    )
    expect(portal.locator("#aeri-question")).to_have_value("Siguiente pregunta")


def test_mail_network_failure_can_retry_without_losing_notes(
    portal, actions, fixed_day
):
    enter(portal)

    def unavailable(route):
        route.abort()

    portal.route("**/ia-aer/correo/", unavailable)
    portal.evaluate("aerIACorreo()")
    portal.locator("#aeri-mail-in").fill("Seguimiento conservado")
    click(portal, "aeri-mail-btn")
    expect(portal.locator("#aeri-mail-btn")).to_have_text("Reintentar")
    expect(portal.locator("#aeri-mail-out")).not_to_be_empty()
    expect(portal.locator("#aeri-mail-in")).to_have_value(
        "Seguimiento conservado"
    )
    portal.unroute("**/ia-aer/correo/", unavailable)
    click(portal, "aeri-mail-btn")
    expect(portal.locator("#aeri-mail-out")).to_contain_text(
        "Borrador del correo"
    )


def test_late_default_prompt_does_not_overwrite_new_config(
    portal, actions, fixed_day
):
    enter(portal)
    held = []
    portal.route("**/ia-aer/prompt/", lambda route: held.append(route))
    portal.evaluate("aerIAAbrirConfigMinutas()")
    with portal.expect_request("**/ia-aer/prompt/"):
        portal.get_by_role(
            "button", name="↺ Restablecer prompt predeterminado", exact=True
        ).click()
    portal.evaluate("aerIAAbrirConfigMinutas()")
    portal.locator("#aeri-minute-prompt").fill("Nuevo borrador de prompt")
    held[0].fulfill(json={"data": {"ok": True, "prompt": "Viejo"}, "meta": {}})
    portal.wait_for_timeout(150)
    expect(portal.locator("#aeri-minute-prompt")).to_have_value(
        "Nuevo borrador de prompt"
    )
    assert portal.evaluate("aerIAState.cargandoPromptDefecto") is False
