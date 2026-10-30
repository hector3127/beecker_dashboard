"""Centro de Comunicación: API v1, mismo diseño y publicación."""

import copy

import pytest
from playwright.sync_api import expect

from tests.e2e.test_aer_executive import fixed_day as fixed_day
from tests.e2e.test_ixs_effort import state as capture_state
from tests.e2e.test_ixs_executive import PAGE
from tests.e2e.test_ixs_executive import ixs as ixs
from tests.e2e.test_project_detail_entry import project_detail as project_detail

pytestmark = pytest.mark.django_db(transaction=True)
ITEMS = [
    {
        "uid": "c1",
        "fecha": "2026-10-20",
        "titulo": "Nuevo lineamiento <b>x</b>",
        "resumen": "Resumen del lineamiento",
        "contenido": (
            "Todos deben usar la plantilla.\nSin excepciones & sin demoras."
        ),
        "categoria": "Lineamiento",
        "importante": True,
        "proyecto": "AMK.008",
        "autor": "Ana",
        "puntosClave": "• Usar plantilla\n2. Revisar\n- Publicar",
    },
    {
        "uid": "c2",
        "fecha": "2026-10-18",
        "titulo": "Aviso general",
        "resumen": "",
        "contenido": "x" * 200,
        "categoria": "Aviso",
        "importante": False,
        "proyecto": "",
        "autor": "",
        "puntosClave": "",
    },
    {
        "uid": "c3",
        "fecha": "2026-10-10",
        "titulo": "Cambio de proceso",
        "resumen": "Otro",
        "contenido": "Cambia el flujo",
        "categoria": "Cambio",
        "importante": False,
        "proyecto": "AMK.008",
        "autor": "Luis",
        "puntosClave": "",
    },
    {
        "uid": "c4",
        "fecha": "2026-10-19",
        "titulo": "De otro proyecto",
        "resumen": "No debe verse aquí",
        "contenido": "Ajeno",
        "categoria": "Aviso",
        "importante": False,
        "proyecto": "OTRO.001",
        "autor": "Eva",
        "puntosClave": "",
    },
]


@pytest.fixture
def board(portal, ixs, monkeypatch):
    from apps.portal.api import project_detail as api

    calls = []
    store = {"items": copy.deepcopy(ITEMS), "fail": None, "error": ""}

    def listed(*_):
        if store["fail"]:
            return {"ok": False, "error": store["fail"]}
        return {"ok": True, "comunicados": copy.deepcopy(store["items"])}

    def save(*args):
        payload = args[-1]
        calls.append(copy.deepcopy(payload))
        if store["error"]:
            return {"ok": False, "error": store["error"]}
        item = {
            "uid": payload["uid"] or f"n{len(calls)}",
            "fecha": "2026-10-23",
            "resumen": payload.get("resumen", ""),
            "importante": payload["importante"],
            "categoria": payload["categoria"],
            **{
                k: payload.get(k, "")
                for k in (
                    "titulo",
                    "contenido",
                    "proyecto",
                    "autor",
                    "puntosClave",
                )
            },
        }
        store["items"] = [x for x in store["items"] if x["uid"] != item["uid"]]
        store["items"].insert(0, item)
        return {"ok": True, "comunicados": copy.deepcopy(store["items"])}

    monkeypatch.setattr(api, "build_store_sheets", lambda: "store")
    monkeypatch.setattr(api.bee_com, "list_communications", listed)
    monkeypatch.setattr(api.bee_com, "save_communication", save)

    def rpc(route):
        name = route.request.url.rstrip("/").rsplit("/", 1)[-1]
        args = (route.request.post_data_json or {}).get("args", [])
        if name == "beeComListar":
            route.fulfill(json={"ok": True, "result": listed()})
        elif name == "beeComGuardar":
            route.fulfill(json={"ok": True, "result": save(*args)})
        else:
            route.fallback()

    portal.route("**/api/rpc/**", rpc)
    return calls, store


def open_tab(portal):
    portal.goto(portal.base + PAGE)
    portal.locator(".ixs-nav").get_by_role(
        "button", name="Comunicación", exact=True
    ).click()
    expect(portal.locator(".bee-com-kpis")).to_be_visible()
    portal.wait_for_load_state("networkidle")


def snapshot(portal):
    selector = (
        "#ixs-tab-contenido, #ixs-tab-contenido *, "
        "#bee-com-modal, #bee-com-modal *"
    )
    classes = portal.evaluate(
        "s=>[...document.querySelectorAll(s)]"
        ".map(e=>String(e.getAttribute('class')||'').trim())",
        selector,
    )
    return [
        {**s, "cls": c}
        for s, c in zip(capture_state(portal, selector), classes, strict=True)
    ]


def nothing(portal):
    pass


def search(portal):
    portal.locator(".bee-com-filters input").fill("plantilla")


def detail(portal):
    portal.locator(".bee-com-list .bee-com-row").first.click()
    expect(portal.locator("#bee-com-modal")).to_be_visible()


def new_form(portal):
    portal.get_by_role("button", name="＋ Nuevo comunicado").click()
    expect(portal.locator("#bee-com-modal")).to_be_visible()


def edit_form(portal):
    detail(portal)
    portal.get_by_role("button", name="Editar comunicado").click()
    expect(portal.locator("#bee-com-modal form")).to_be_visible()


def test_reads_by_api_and_hides_other_projects(portal, board, fixed_day):
    requests = []
    portal.on("request", lambda request: requests.append(request.url))
    open_tab(portal)
    expect(portal.locator(".bee-com-list .bee-com-row")).to_have_count(3)
    expect(portal.locator(".bee-com-list")).not_to_contain_text(
        "De otro proyecto"
    )
    expect(portal.locator(".bee-com-kpi b").first).to_have_text("3")
    assert not any("beeComListar" in url for url in requests)
    assert any("/screens/proyectos/comunicados/" in url for url in requests)


def test_text_is_never_html_and_detail_shows_key_points(
    portal, board, fixed_day
):
    open_tab(portal)
    expect(portal.locator(".bee-com-list")).to_contain_text(
        "Nuevo lineamiento <b>x</b>"
    )
    expect(portal.locator(".bee-com-row b b")).to_have_count(0)
    detail(portal)
    expect(portal.locator(".bee-com-detail-points li")).to_have_count(3)
    expect(portal.locator(".bee-com-detail-message")).to_contain_text(
        "sin demoras"
    )
    portal.locator("#bee-com-modal .bee-com-btn[aria-label='Cerrar']").click()
    expect(portal.locator("#bee-com-modal")).to_have_count(0)


def test_publishing_updates_the_list_with_csrf(portal, board, fixed_day):
    calls, _ = board
    requests = []
    portal.on("request", lambda request: requests.append(request))
    open_tab(portal)
    new_form(portal)
    form = portal.locator("#bee-com-modal form")
    form.locator('[name="titulo"]').fill("Comunicado nuevo")
    form.locator('[name="contenido"]').fill("Cuerpo del mensaje")
    form.locator('[name="categoria"]').select_option("Cambio")
    form.locator('[name="importante"]').check()
    form.get_by_role("button", name="Publicar comunicado").click()
    expect(portal.locator("#bee-com-modal")).to_have_count(0)
    expect(portal.locator(".bee-com-list")).to_contain_text("Comunicado nuevo")
    assert calls[0]["uid"] == "" and calls[0]["importante"] is True
    assert calls[0]["proyecto"] == "AMK.008"
    token = next(
        c["value"] for c in portal.context.cookies() if c["name"] == "csrftoken"
    )
    posts = [
        r for r in requests if r.method == "POST" and "comunicados" in r.url
    ]
    assert posts and all(r.headers.get("x-csrftoken") == token for r in posts)


def test_edit_keeps_the_uid_and_service_errors_stay_in_the_form(
    portal, board, fixed_day
):
    calls, store = board
    open_tab(portal)
    edit_form(portal)
    store["error"] = "Escribe un título y contenido válidos."
    portal.get_by_role("button", name="Publicar comunicado").click()
    expect(portal.locator("#bee-com-error")).to_have_text(
        "Escribe un título y contenido válidos."
    )
    expect(
        portal.get_by_role("button", name="Publicar comunicado")
    ).to_be_enabled()
    store["error"] = ""
    portal.get_by_role("button", name="Publicar comunicado").click()
    expect(portal.locator("#bee-com-modal")).to_have_count(0)
    assert [c["uid"] for c in calls] == ["c1", "c1"]


def test_load_errors_are_shown(portal, board, fixed_day):
    _, store = board
    store["fail"] = "Hoja no disponible"
    open_tab_error = portal.goto(portal.base + PAGE)
    assert open_tab_error is not None
    portal.locator(".ixs-nav").get_by_role(
        "button", name="Comunicación", exact=True
    ).click()
    expect(portal.locator(".bee-com-card").first).to_have_text(
        "Hoja no disponible"
    )
    expect(portal.locator(".bee-com-list")).to_contain_text(
        "No hay comunicados con estos filtros."
    )
