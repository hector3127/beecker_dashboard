"""Editor de hitos: API v1, diseño previo y mismos mensajes."""

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
TYPES = ["🚀 Pase a producción", "🎥 Demo 1"]
SAVED = [
    {
        "tipo": TYPES[1],
        "fecha": "05/11/2026",
        "observacion": "Con 'comillas'",
        "indice": 1,
    },
    {"tipo": TYPES[1], "fecha": "12/11/2026", "observacion": "", "indice": 2},
]


@pytest.fixture
def milestones(portal, planning, monkeypatch):
    from apps.portal.api import project_detail as api

    calls, answers = [], {"result": {"ok": True, "hitos": []}}

    def types():
        return list(TYPES)

    def save(project, items):
        calls.append(("save", project, copy.deepcopy(items)))
        return copy.deepcopy(answers["result"])

    def edit(project, tipo, index, date, note):
        calls.append(("edit", project, tipo, index, date, note))
        return copy.deepcopy(answers["result"])

    def delete(project, tipo, index):
        calls.append(("delete", project, tipo, index))
        return copy.deepcopy(answers["result"])

    monkeypatch.setattr(api.milestones, "get_milestone_types", types)
    monkeypatch.setattr(api.milestones, "save_milestone_batch", save)
    monkeypatch.setattr(api.milestones, "edit_milestone_entry", edit)
    monkeypatch.setattr(api.milestones, "delete_milestone_entry", delete)

    def rpc(route):
        name = route.request.url.rstrip("/").rsplit("/", 1)[-1]
        if name == "obtenerTiposHitosExistentes":
            route.fulfill(json={"ok": True, "result": types()})
        else:
            route.fallback()

    portal.route("**/api/rpc/**", rpc)
    return calls, answers


def open_editor(portal, previous=False):
    open_planning(portal, previous)
    portal.evaluate(
        "hitos => { hitosAdicionalesActuales = hitos;"
        " idProyectoActualGlobal = 'AMK.008'; abrirModalHito('AMK.008'); }",
        SAVED,
    )
    expect(portal.locator("#modal-hito-overlay")).to_have_count(1)
    expect(portal.locator(".mh-tipo-select")).to_have_value(TYPES[0])


@pytest.mark.parametrize("width", [1450, 900, 390])
@pytest.mark.parametrize("variant", ["empty", "existing", "new-type"])
def test_editor_matches_previous(portal, milestones, fixed_day, width, variant):
    portal.set_viewport_size({"width": width, "height": 900})
    states = []
    directory = (
        Path("tmp/migration/project_detail/ixs_milestones")
        / variant
        / str(width)
    )
    directory.mkdir(parents=True, exist_ok=True)
    for previous in [True, False]:
        open_editor(portal, previous)
        if variant != "empty":
            portal.locator(".mh-tipo-select").select_option(
                TYPES[1] if variant == "existing" else "__nuevo__"
            )
        selector = "#modal-hito-overlay, #modal-hito-overlay *"
        states.append(capture_state(portal, selector))
        portal.screenshot(
            path=str(directory / ("old.png" if previous else "new.png")),
        )
    diffs = [
        (i, a["tag"], {k: (a[k], b[k]) for k in a if a[k] != b[k]})
        for i, (a, b) in enumerate(zip(*states, strict=True))
        if a != b
    ]
    assert len(states[0]) == len(states[1]) and not diffs


def fill_new(portal, name="Cierre", date="2026-12-01", note="Nota"):
    portal.locator(".mh-tipo-select").select_option("__nuevo__")
    portal.locator(".mh-tipo-nuevo").fill(name)
    portal.locator('.mh-icono-opcion[data-icono="🏁"]').click()
    portal.locator(".mh-fecha").fill(date)
    portal.locator(".mh-obs").fill(note)


def test_save_uses_api_and_reloads(portal, milestones, fixed_day):
    calls, _ = milestones
    requests = []
    portal.on("request", lambda request: requests.append(request))
    open_editor(portal)
    fill_new(portal)
    portal.locator("#mh-btn-guardar").click()
    expect(portal.locator("#modal-hito-overlay")).to_have_count(0)
    assert calls == [
        (
            "save",
            "AMK.008",
            [
                {
                    "tipo": "🏁 Cierre",
                    "fechaISO": "2026-12-01",
                    "observacion": "Nota",
                }
            ],
        )
    ]
    assert not any(
        "obtenerTiposHito" in r.url or "guardarHitos" in r.url for r in requests
    )
    token = next(
        c["value"] for c in portal.context.cookies() if c["name"] == "csrftoken"
    )
    posts = [r for r in requests if r.method == "POST" and "/hitos/" in r.url]
    assert posts and all(r.headers.get("x-csrftoken") == token for r in posts)


def test_edit_then_add_in_one_save(portal, milestones, fixed_day):
    calls, answers = milestones
    answers["result"] = {"ok": True, "hitos": SAVED}
    open_editor(portal)
    portal.locator(".mh-tipo-select").select_option(TYPES[1])
    expect(portal.locator(".mh-existente")).to_have_count(2)
    portal.locator(".mh-existente").first.locator(".mh-accion").first.click()
    expect(portal.locator(".mh-editando-aviso")).to_be_visible()
    expect(portal.locator(".mh-obs")).to_have_value("Con 'comillas'")
    portal.locator(".mh-fecha").fill("2026-11-06")
    portal.locator(".mh-agregar").click()
    row = portal.locator(".mh-fila").nth(1)
    row.locator(".mh-tipo-select").select_option("__nuevo__")
    row.locator(".mh-tipo-nuevo").fill("Extra")
    row.locator(".mh-fecha").fill("2026-12-02")
    portal.locator("#mh-btn-guardar").click()
    expect(portal.locator("#modal-hito-overlay")).to_have_count(0)
    assert [c[0] for c in calls] == ["edit", "save"]
    assert calls[0] == (
        "edit",
        "AMK.008",
        TYPES[1],
        1,
        "2026-11-06",
        "Con 'comillas'",
    )
    assert calls[1][2] == [
        {"tipo": "🎥 Extra", "fechaISO": "2026-12-02", "observacion": ""}
    ]


@pytest.mark.parametrize(
    "setup, message",
    [
        ("nothing-name", "Falta el nombre de un tipo de hito nuevo."),
        ("nothing-date", "Falta la fecha en uno de los hitos."),
        ("none", "Agrega al menos un hito."),
    ],
)
def test_validation_messages(portal, milestones, fixed_day, setup, message):
    calls, _ = milestones
    open_editor(portal)
    if setup == "nothing-name":
        portal.locator(".mh-tipo-select").select_option("__nuevo__")
        portal.locator(".mh-fecha").fill("2026-12-01")
    elif setup == "nothing-date":
        pass
    else:
        portal.locator(".mh-quitar").click()
    portal.locator("#mh-btn-guardar").click()
    expect(portal.locator("#mh-error")).to_have_text(message)
    assert calls == []
    expect(portal.locator("#mh-btn-guardar")).to_be_enabled()


def test_server_error_keeps_dialog_and_allows_retry(
    portal, milestones, fixed_day
):
    calls, answers = milestones
    answers["result"] = {"ok": False, "error": "Sin hoja"}
    open_editor(portal)
    fill_new(portal)
    portal.locator("#mh-btn-guardar").click()
    expect(portal.locator("#mh-error")).to_contain_text(
        "Error al guardar: Sin hoja"
    )
    expect(portal.locator("#modal-hito-overlay")).to_have_count(1)
    expect(portal.locator(".mh-obs")).to_have_value("Nota")
    answers["result"] = {"ok": True, "hitos": []}
    portal.locator("#mh-btn-guardar").click()
    expect(portal.locator("#modal-hito-overlay")).to_have_count(0)
    assert len(calls) == 2


def test_delete_from_dialog_confirms_and_refreshes(
    portal, milestones, fixed_day
):
    calls, answers = milestones
    answers["result"] = {"ok": True, "hitos": SAVED[1:]}
    open_editor(portal)
    portal.locator(".mh-tipo-select").select_option(TYPES[1])
    messages = []
    portal.once("dialog", lambda d: (messages.append(d.message), d.accept()))
    portal.locator(".mh-existente").first.locator(".mh-accion").nth(1).click()
    expect(portal.locator(".mh-existente")).to_have_count(1)
    assert messages == [
        f'¿Eliminar esta entrada de "{TYPES[1]}"? '
        "Esta acción no se puede deshacer."
    ]
    assert calls == [("delete", "AMK.008", TYPES[1], 1)]


def test_overlay_click_and_escape_hatch_close(portal, milestones, fixed_day):
    open_editor(portal)
    portal.locator("#modal-hito-overlay").click(position={"x": 2, "y": 2})
    expect(portal.locator("#modal-hito-overlay")).to_have_count(0)
