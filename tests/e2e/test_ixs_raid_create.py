"""Alta RAID: API v1, mismo diseño que el anterior y reglas de publicación."""

import copy

import pytest
from playwright.sync_api import expect

from tests.e2e.test_aer_executive import fixed_day as fixed_day
from tests.e2e.test_ixs_effort import state as capture_state
from tests.e2e.test_ixs_executive import PAGE
from tests.e2e.test_ixs_executive import ixs as ixs
from tests.e2e.test_ixs_raid import ROWS
from tests.e2e.test_project_detail_entry import project_detail as project_detail

pytestmark = pytest.mark.django_db(transaction=True)
OPTIONS = {
    "ok": True,
    "proyectoAzure": "AMK",
    "iteracionDefault": "AMK",
    "iteraciones": ["AMK", "AMK\\Development", "AMK\\Deployment"],
    "usuarios": [
        {
            "nombre": "Ana Pérez",
            "email": "ana@x.com",
            "valor": "Ana Pérez <ana@x.com>",
        },
        {
            "nombre": "Luis Soto",
            "email": "luis@x.com",
            "valor": "Luis Soto <luis@x.com>",
        },
    ],
    "relacionados": [
        {"id": 132790, "titulo": "Épica principal", "tipo": "Epic"}
    ],
    "campos": {
        "state": {"opciones": ["New", "Active"]},
        "reason": {"opciones": ["New"]},
        "escalate": {"opciones": ["No", "Yes"]},
        "relatedSoftware": {"opciones": ["UiPath", "SAP"]},
        "managementStrategy": {"opciones": ["Mitigar", "Aceptar"]},
        "stakeholders": {"opciones": ["Cliente", "Equipo"]},
        "opportunitySource": {"opciones": ["Interna"]},
        "category": {"opciones": ["Técnico", "Legal"]},
    },
}
FIELD_TYPES = {
    "ok": True,
    "campos": {
        "severidad": {"opciones": ["1 - Crítico", "2 - Alto", "3 - Medio"]},
        "prioridad": {"opciones": ["1", "2", "3"]},
        "probabilidad": {"opciones": ["Alto", "Medio", "Bajo"]},
        "categoria": {"opciones": ["Técnico", "Legal"]},
        "fuenteRiesgo": {"opciones": ["Cliente"]},
        "estrategiaGestion": {"opciones": ["Mitigar"]},
        "partesInteresadas": {"opciones": ["Cliente"]},
        "escalate": {"opciones": ["No", "Sí"]},
    },
}
SUGGESTION = {
    "titulo": "Servidor sin respaldo",
    "descripcion": "El servidor productivo no tiene respaldo",
    "planMitigacion": (
        "Crear respaldo diario\n* Probar restauración\n- Documentar"
    ),
    "triggers": "Falla de disco",
    "contingencyPlan": "Usar el servidor secundario",
    "planAprovechamiento": "Reutilizar el script",
    "senalAlerta": "Aumento de tickets",
    "planAccion": "Automatizar",
    "followUp": "Revisión mensual",
    "severidad": "2 - Alto",
    "prioridad": "2",
    "probabilidad": "Alto",
    "categoria": "Técnico",
    "responsable": "Ana Pérez <ana@x.com>",
    "escalate": "No",
    "estrategiaGestion": "Mitigar",
    "originalEstimate": 4,
    "state": "Extraño",
}
FREE = "El servidor productivo no tiene respaldo diario"


@pytest.fixture
def alta(portal, ixs, monkeypatch):
    from apps.portal.api import project_detail as api

    calls = []
    answers = {
        "create": {"ok": True, "id": 901},
        "prompt": {
            "ok": True,
            "configurado": True,
            "prompt": "Prompt estándar",
        },
        "save": {"ok": True, "prompt": "Guardado"},
    }

    def listed(project, force=False):
        return {"ok": True, "registros": copy.deepcopy(ROWS), "aviso": ""}

    def prompt(settings, tipo):
        calls.append(("prompt", tipo))
        return copy.deepcopy(answers["prompt"])

    def save(settings, tipo, text):
        calls.append(("save", tipo, text))
        return copy.deepcopy(answers["save"])

    def suggest(settings, tipo, description):
        calls.append(("suggest", tipo, description))
        return {"ok": True, "sugerencia": copy.deepcopy(SUGGESTION)}

    def fields(project, tipo):
        calls.append(("fields", project, tipo))
        return copy.deepcopy(FIELD_TYPES)

    def options(project, tipo):
        calls.append(("options", project, tipo))
        return copy.deepcopy(OPTIONS)

    def create(project, tipo, data):
        calls.append(("create", project, tipo, copy.deepcopy(data)))
        return copy.deepcopy(answers["create"])

    monkeypatch.setattr(api.ixs_rpc, "list_raid", listed)
    monkeypatch.setattr(api.ai_rpc, "build_claude", lambda: "claude")
    monkeypatch.setattr(api.claude_assist, "read_raid_prompt", prompt)
    monkeypatch.setattr(api.claude_assist, "save_raid_prompt", save)
    monkeypatch.setattr(api.claude_assist, "suggest_raid", suggest)
    monkeypatch.setattr(api.ixs_rpc, "raid_field_types", fields)
    monkeypatch.setattr(api.ixs_rpc, "raid_creation_options", options)
    monkeypatch.setattr(api.ixs_rpc, "create_raid_record", create)

    def rpc(route):
        name = route.request.url.rstrip("/").rsplit("/", 1)[-1]
        args = (route.request.post_data_json or {}).get("args", [])
        table = {
            "ixsRaidListarProyecto": lambda: listed(*args),
            "ixsRaidObtenerPrompt": lambda: prompt("claude", *args),
            "ixsRaidGuardarPrompt": lambda: save("claude", *args),
            "ixsRaidSugerirClaude": lambda: suggest("claude", *args),
            "ixsRaidCamposTipo": lambda: fields(*args),
            "ixsRaidAltaOpciones": lambda: options(*args),
            "ixsRaidCrearRegistro": lambda: create(*args),
        }
        if name in table:
            route.fulfill(json={"ok": True, "result": table[name]()})
        else:
            route.fallback()

    portal.route("**/api/rpc/**", rpc)
    return calls, answers


def open_modal(portal, tipo, previous=False):
    portal.goto(portal.base + PAGE + ("?vista=anterior" if previous else ""))
    portal.locator(".ixs-nav").get_by_role(
        "button", name="Gestión RAID", exact=True
    ).click()
    expect(portal.locator("#ixs-raid-tabla tbody tr")).to_have_count(5)
    label = {
        "Risk": "+ Riesgo",
        "Issue": "+ Issue",
        "Opportunity": "+ Oportunidad",
    }
    portal.get_by_role("button", name=label[tipo], exact=True).click()
    expect(portal.locator("#ixs-raid-modal")).to_be_visible()
    expect(portal.locator("#ixs-raid-api-state")).to_contain_text(
        "Claude configurado"
    )
    portal.wait_for_load_state("networkidle")


def manual(portal):
    portal.locator("#ixs-raid-free").fill(FREE)
    portal.locator("#ixs-raid-manual").click()
    expect(portal.locator("#ixs-raid-form-wrap")).to_be_visible()


def suggested(portal):
    portal.locator("#ixs-raid-free").fill(FREE)
    portal.locator("#ixs-raid-suggest").click()
    expect(portal.locator("#ixs-raid-form-wrap")).to_be_visible()
    expect(portal.locator("#ixs-raid-modal-msg")).to_contain_text(
        "Sugerencia generada"
    )


def initial(portal):
    portal.locator("#ixs-raid-free").fill(FREE)


def snapshot(portal):
    selector = "#ixs-raid-modal, #ixs-raid-modal *"
    classes = portal.evaluate(
        "s=>[...document.querySelectorAll(s)]"
        ".map(e=>String(e.getAttribute('class')||'').trim())",
        selector,
    )
    return [
        {**s, "cls": c}
        for s, c in zip(capture_state(portal, selector), classes, strict=True)
    ]


def form_value(portal, key):
    return portal.locator(f'#ixs-raid-form-wrap [data-raid-key="{key}"]')


def test_modal_reads_and_creates_by_api(portal, alta, fixed_day):
    calls, _ = alta
    requests = []
    portal.on("request", lambda request: requests.append(request))
    open_modal(portal, "Issue")
    suggested(portal)
    assert ("prompt", "Issue") in calls
    assert ("fields", "AMK.008", "Issue") in calls
    assert ("options", "AMK.008", "Issue") in calls
    assert ("suggest", "Issue", FREE) in calls
    form_value(portal, "iterationPath").fill("amk\\development")
    form_value(portal, "relatedWorkItemId").fill("#132790")
    portal.locator("#ixs-raid-create").click()
    expect(portal.locator("#ixs-raid-modal-msg")).to_contain_text(
        "Registro #901 creado correctamente."
    )
    expect(portal.locator("#ixs-raid-modal")).to_have_count(0)
    create = next(c for c in calls if c[0] == "create")
    data = create[3]
    assert create[:3] == ("create", "AMK.008", "Issue")
    assert data["iterationPath"] == "AMK\\Development"
    assert data["relatedWorkItemId"] == "#132790"
    assert data["severidad"] == "2 - Alto"
    assert data["impactoNivel"] == "2" and data["probabilidad"] == "2"
    assert data["planMitigacion"] == (
        "• Crear respaldo diario\n• Probar restauración\n• Documentar"
    )
    assert not any("/api/rpc/" in r.url for r in requests)
    token = next(
        c["value"] for c in portal.context.cookies() if c["name"] == "csrftoken"
    )
    posts = [r for r in requests if r.method == "POST"]
    assert posts and all(r.headers.get("x-csrftoken") == token for r in posts)
    expect(portal.locator("#ixs-raid-tabla tbody tr")).to_have_count(5)


@pytest.mark.parametrize(
    ("edit", "message"),
    [
        (
            lambda p: form_value(p, "titulo").fill(""),
            "Completa título y descripción antes de crear.",
        ),
        (
            lambda p: form_value(p, "iterationPath").fill("Otra\\Ruta"),
            "Iteration Path no válido: selecciona una ruta de la lista "
            "real de Azure para AMK.",
        ),
        (
            lambda p: form_value(p, "relatedWorkItemId").fill("abc"),
            "Selecciona un Work Item sugerido o escribe su ID numérico.",
        ),
    ],
)
def test_publishing_rules_block_before_azure(
    portal, alta, fixed_day, edit, message
):
    calls, _ = alta
    open_modal(portal, "Opportunity")
    suggested(portal)
    edit(portal)
    portal.locator("#ixs-raid-create").click()
    expect(portal.locator("#ixs-raid-modal-msg")).to_have_text(message)
    assert not any(c[0] == "create" for c in calls)


def test_short_description_is_rejected_and_suggestion_keeps_choices(
    portal, alta, fixed_day
):
    calls, _ = alta
    open_modal(portal, "Risk")
    portal.locator("#ixs-raid-free").fill("corto")
    portal.locator("#ixs-raid-suggest").click()
    expect(portal.locator("#ixs-raid-modal-msg")).to_have_text(
        "Describe la situación con al menos 12 caracteres."
    )
    assert not any(c[0] == "suggest" for c in calls)
    suggested(portal)
    form_value(portal, "iterationPath").fill("deploy")
    portal.locator(
        "#ixs-raid-alta-list-iterationPath button", has_text="Deployment"
    ).dispatch_event("mousedown")
    expect(form_value(portal, "iterationPath")).to_have_value("AMK\\Deployment")
    portal.locator("#ixs-raid-suggest").click()
    expect(portal.locator("#ixs-raid-modal-msg")).to_contain_text(
        "Sugerencia generada"
    )
    expect(form_value(portal, "iterationPath")).to_have_value("AMK\\Deployment")
    expect(form_value(portal, "responsable")).to_have_value(
        "Ana Pérez <ana@x.com>"
    )


def test_severity_derives_impact_and_probability_for_issues(
    portal, alta, fixed_day
):
    open_modal(portal, "Issue")
    manual(portal)
    form_value(portal, "severidad").select_option("1 - Crítico")
    expect(form_value(portal, "impactoNivel")).to_have_value("1")
    expect(form_value(portal, "iterationPath")).to_have_value("AMK")


def test_parent_status_line_follows_what_is_typed(portal, alta, fixed_day):
    open_modal(portal, "Opportunity")
    manual(portal)
    status = portal.locator("#ixs-raid-parent-status")
    form_value(portal, "relatedWorkItemId").fill("132790")
    expect(status).to_contain_text(
        "✓ Padre seleccionado #132790 · Épica principal"
    )
    form_value(portal, "relatedWorkItemId").fill("999")
    expect(status).to_contain_text("se verificará en Azure al guardar")
    form_value(portal, "relatedWorkItemId").fill("xx")
    expect(status).to_have_text(
        "Selecciona un Work Item sugerido o escribe un ID numérico."
    )


def test_prompt_is_saved_and_restored(portal, alta, fixed_day):
    calls, answers = alta
    open_modal(portal, "Issue")
    portal.locator("details.ixs-raid-prompt summary").click()
    portal.locator("#ixs-raid-prompt").fill("Mi prompt")
    portal.get_by_role("button", name="Guardar prompt").click()
    expect(portal.locator("#ixs-raid-modal-msg")).to_have_text(
        "✓ Prompt de Issue guardado."
    )
    assert ("save", "Issue", "Mi prompt") in calls
    answers["save"] = {"ok": True, "prompt": "Estándar"}
    portal.get_by_role("button", name="Restaurar estándar").click()
    expect(portal.locator("#ixs-raid-modal-msg")).to_have_text(
        "✓ Prompt estándar restaurado."
    )
    expect(portal.locator("#ixs-raid-prompt")).to_have_value("Estándar")
    assert ("save", "Issue", "") in calls


def test_text_never_becomes_html_and_overlay_closes(portal, alta, fixed_day):
    open_modal(portal, "Risk")
    portal.locator("#ixs-raid-free").fill(
        "<img src=x onerror=alert(1)> en el servidor"
    )
    portal.locator("#ixs-raid-manual").click()
    expect(portal.locator("#ixs-raid-modal img")).to_have_count(0)
    expect(form_value(portal, "descripcion")).to_have_value(
        "<img src=x onerror=alert(1)> en el servidor"
    )
    portal.locator("#ixs-raid-modal").click(position={"x": 3, "y": 3})
    expect(portal.locator("#ixs-raid-modal")).to_have_count(0)


def test_azure_errors_are_shown_without_closing(portal, alta, fixed_day):
    calls, answers = alta
    answers["create"] = {"ok": False, "error": "Azure rechazó el campo"}
    open_modal(portal, "Opportunity")
    suggested(portal)
    portal.locator("#ixs-raid-create").click()
    expect(portal.locator("#ixs-raid-modal-msg")).to_have_text(
        "Azure rechazó el campo"
    )
    expect(portal.locator("#ixs-raid-modal")).to_be_visible()
    expect(portal.locator("#ixs-raid-create")).to_be_enabled()
