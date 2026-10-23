"""Guardado y comentarios de Planeación: API, diseño previo y ciclo de vida."""

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


@pytest.fixture
def writes(portal, planning, monkeypatch):
    from apps.portal.api import project_detail as api

    calls, results = [], {"progress": {"ok": True}, "comment": {"ok": True}}

    def save(id, field, value):
        calls.append(("progress", id, field, value))
        return copy.deepcopy(results["progress"])

    def comment(id, text):
        calls.append(("comment", id, text))
        return copy.deepcopy(results["comment"])

    monkeypatch.setattr(api.daily, "save_work_item_progress", save)
    monkeypatch.setattr(api.daily, "add_comment", comment)

    def rpc(route):
        name = route.request.url.rstrip("/").rsplit("/", 1)[-1]
        if name in {"guardarCampoAvanceWorkItem", "agregarComentarioWorkItem"}:
            args = route.request.post_data_json["args"]
            result = (
                save(*args)
                if name == "guardarCampoAvanceWorkItem"
                else comment(*args)
            )
            route.fulfill(json={"ok": True, "result": result})
        else:
            route.fallback()

    portal.route("**/api/rpc/**", rpc)
    return calls, results


def update(portal, column, value):
    control = portal.locator(f"#wi-row-101 td:nth-child({column}) input")
    if isinstance(value, bool):
        control.set_checked(value)
    else:
        control.evaluate(
            "(input,value)=>{input.value=value;"
            "input.dispatchEvent(new Event('change',{bubbles:true}));}",
            value,
        )


def draft(portal, text):
    # Planeación intentionally hides this column in both versions.
    portal.locator("#wi-comentario-101").evaluate(
        "(input,text)=>input.value=text", text
    )


def send(portal):
    portal.locator("#wi-row-101 .ixs-azure-comment button").evaluate(
        "button=>button.click()"
    )


@pytest.mark.parametrize("width", [1450, 900, 390])
@pytest.mark.parametrize("action", ["dev", "qa", "date", "comment"])
def test_saved_result_matches_previous(
    portal, writes, fixed_day, width, action
):
    portal.set_viewport_size({"width": width, "height": 1000})
    states = []
    directory = (
        Path("tmp/migration/project_detail/ixs_work_items")
        / action
        / str(width)
    )
    directory.mkdir(parents=True, exist_ok=True)
    for previous in [True, False]:
        open_planning(portal, previous)
        if action == "dev":
            update(portal, 5, "62.5")
        elif action == "qa":
            update(portal, 6, True)
        elif action == "date":
            update(portal, 7, "2026-10-29")
        else:
            draft(portal, "  Validación cliente  ")
            send(portal)
        if action == "comment":
            expect(portal.locator("#wi-comentario-status-101")).to_have_text(
                "✓ Publicado en Azure DevOps"
            )
            selector = "#wi-row-101, #wi-row-101 *"
        elif action == "date":
            expect(portal.locator("#ixs-plan-attention")).to_contain_text(
                "0 trabajos vencidos"
            )
            selector = "#ixs-tab-contenido, #ixs-tab-contenido *"
        else:
            expect(portal.locator("#wi-avance-101")).to_contain_text(
                "50%" if action == "dev" else "20%"
            )
            selector = "#wi-row-101, #wi-row-101 *"
        states.append(capture_state(portal, selector))
        portal.screenshot(
            path=str(directory / ("old.png" if previous else "new.png")),
            full_page=True,
        )
    assert states[0] == states[1]


def test_all_fields_and_comment_use_api_with_csrf(portal, writes, fixed_day):
    calls, _ = writes
    requests = []
    portal.on("request", lambda request: requests.append(request))
    open_planning(portal)
    update(portal, 5, "60")
    expect(portal.locator("#wi-avance-101")).to_contain_text("48%")
    update(portal, 6, True)
    expect(portal.locator("#wi-avance-101")).to_contain_text("68%")
    with portal.expect_response("**/screens/work-items/101/avance/"):
        update(portal, 8, "Demo final")
    update(portal, 7, "2026-10-29")
    expect(portal.locator("#ixs-plan-attention")).to_contain_text(
        "0 trabajos vencidos"
    )
    draft(portal, "  Hola á ' cliente  ")
    send(portal)
    expect(portal.locator("#wi-comentario-status-101")).to_have_text(
        "✓ Publicado en Azure DevOps"
    )
    expect(portal.locator("#wi-comentario-101")).to_have_value("")
    assert calls == [
        ("progress", 101, "devConstruido", 60),
        ("progress", 101, "qa", True),
        ("progress", 101, "demo", "Demo final"),
        ("progress", 101, "fechaLimiteDev", "2026-10-29"),
        ("comment", 101, "Hola á ' cliente"),
    ]
    assert not any("/api/rpc/" in request.url for request in requests)
    token = next(
        cookie["value"]
        for cookie in portal.context.cookies()
        if cookie["name"] == "csrftoken"
    )
    posts = [request for request in requests if request.method == "POST"]
    assert len(posts) == 5
    assert all(request.headers.get("x-csrftoken") == token for request in posts)
    expect(portal.locator("#wi-comentario-status-101")).to_be_empty(
        timeout=4500
    )


def test_empty_comment_does_not_send(portal, writes, fixed_day):
    calls, _ = writes
    open_planning(portal)
    draft(portal, "   ")
    portal.once("dialog", lambda dialog: dialog.accept())
    with portal.expect_event("dialog") as pending:
        send(portal)
    assert pending.value.message == "Escribe un comentario antes de enviar."
    assert calls == []


@pytest.mark.parametrize("kind", ["progress", "comment"])
@pytest.mark.parametrize("mode", ["source", "permission", "transport"])
def test_error_keeps_input_and_allows_retry(
    portal, writes, fixed_day, kind, mode
):
    calls, results = writes
    open_planning(portal)
    path = "**/screens/work-items/101/" + (
        "avance/" if kind == "progress" else "comentarios/"
    )

    def fail(route):
        if mode == "transport":
            route.abort()
        else:
            route.fulfill(
                status=403,
                json={
                    "error": {"code": "forbidden", "message": "Sin permiso."}
                },
            )

    if mode == "source":
        results[kind] = {"ok": False, "error": "Error de fuente."}
    else:
        portal.route(path, fail)
    if kind == "comment":
        draft(portal, "Borrador")
    portal.once("dialog", lambda dialog: dialog.accept())
    with portal.expect_event("dialog") as pending:
        if kind == "progress":
            update(portal, 5, "75")
        else:
            send(portal)
    assert pending.value.message.startswith("Error")
    expect(
        portal.locator("#wi-comentario-101")
        if kind == "comment"
        else portal.locator("#wi-row-101 td:nth-child(5) input")
    ).to_have_value("Borrador" if kind == "comment" else "75")
    if mode == "source":
        results[kind] = {"ok": True}
    else:
        portal.unroute(path, fail)
    if kind == "progress":
        update(portal, 5, "75")
        expect(portal.locator("#wi-avance-101")).to_contain_text("60%")
    else:
        expect(portal.locator("#wi-row-101 button")).to_be_enabled()
        send(portal)
        expect(portal.locator("#wi-comentario-status-101")).to_have_text(
            "✓ Publicado en Azure DevOps"
        )


@pytest.mark.parametrize("kind", ["progress", "comment"])
@pytest.mark.parametrize("ok", [True, False])
def test_late_response_does_not_modify_reentered_view(
    portal, writes, fixed_day, kind, ok
):
    open_planning(portal)
    held = []
    path = "**/screens/work-items/101/" + (
        "avance/" if kind == "progress" else "comentarios/"
    )
    portal.route(path, lambda route: held.append(route))
    alerts = []
    portal.on(
        "dialog",
        lambda dialog: (alerts.append(dialog.message), dialog.accept()),
    )
    if kind == "comment":
        draft(portal, "Anterior")
    with portal.expect_request(path):
        if kind == "progress":
            update(portal, 5, "75")
        else:
            send(portal)
    if kind == "comment":
        expect(portal.locator("#wi-row-101 button")).to_be_disabled()
        portal.locator("#wi-row-101 button").dispatch_event("click")
        assert len(held) == 1
    portal.locator(".ixs-nav").get_by_role(
        "button", name="Ejecutivo", exact=True
    ).click()
    portal.locator(".ixs-nav").get_by_role(
        "button", name="Planeación", exact=True
    ).click()
    expect(portal.locator("#wi-row-101")).to_be_visible()
    draft(portal, "Nuevo borrador")
    held[0].fulfill(
        json={"data": {"ok": ok, "error": "Respuesta anterior"}, "meta": {}}
    )
    portal.wait_for_load_state("networkidle")
    expect(portal.locator("#wi-avance-101")).to_contain_text("40%")
    expect(portal.locator("#wi-comentario-101")).to_have_value("Nuevo borrador")
    expect(portal.locator("#wi-comentario-status-101")).to_be_empty()
    assert alerts == []


def test_visible_azure_tab_writes_use_api(portal, writes, fixed_day):
    calls, _ = writes
    requests = []
    portal.on("request", lambda request: requests.append(request.url))
    open_planning(portal)
    portal.locator(".ixs-nav").get_by_role(
        "button", name="Azure DevOps", exact=True
    ).click()
    portal.locator("#ixs-azure-wi-collapse > summary").click()
    control = portal.locator("#wi-comentario-101")
    control.scroll_into_view_if_needed()
    control.fill("  Comentario visible  ")
    portal.locator("#wi-row-101 .ixs-azure-comment button").click()
    expect(portal.locator("#wi-comentario-status-101")).to_have_text(
        "✓ Publicado en Azure DevOps"
    )
    assert calls[-1] == ("comment", 101, "Comentario visible")
    expect(control).to_have_value("")
    update(portal, 5, "45")
    expect(portal.locator("#wi-avance-101")).to_contain_text("36%")
    assert calls[-1] == ("progress", 101, "devConstruido", 45)
    assert not any(
        url.endswith(
            ("/guardarCampoAvanceWorkItem/", "/agregarComentarioWorkItem/")
        )
        for url in requests
    )
