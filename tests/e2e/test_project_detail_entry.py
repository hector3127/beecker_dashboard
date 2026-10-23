"""Entrada transitoria del detalle, con datos y acciones anteriores."""

import copy
import json
from pathlib import Path

import pytest
from playwright.sync_api import expect

pytestmark = pytest.mark.django_db(transaction=True)


@pytest.fixture
def project_detail(portal, monkeypatch, datos):
    from apps.portal.api import project_detail as api

    executive = json.loads(
        Path("tests/ejecutivo/project_integrated_expected.json").read_text(
            encoding="utf-8"
        )
    )[0]
    aer = json.loads(
        Path("tests/aer/aer_expected.json").read_text(encoding="utf-8")
    )["results"][3]
    filters = {
        "proyectos": [
            {
                "id": executive["proyecto"]["id"],
                "nombre": "IXB",
                "servicio": "IXB",
            },
            {"id": aer["proyecto"]["id"], "nombre": "AER", "servicio": "AER"},
        ],
        "clientes": ["Todos los clientes", "ACME"],
    }
    monkeypatch.setattr(
        api, "get_available_filters", lambda: copy.deepcopy(filters)
    )
    monkeypatch.setattr(
        api, "get_executive_dashboard", lambda project: copy.deepcopy(executive)
    )
    monkeypatch.setattr(
        api, "aer_dashboard", lambda project: copy.deepcopy(aer)
    )
    for source in (
        "get_project_raid",
        "tasks_dashboard",
        "stages_dashboard",
        "resources_dashboard",
    ):
        monkeypatch.setattr(api, source, lambda project: {"ok": True})
    monkeypatch.setattr("apps.portal.pages.anterior_disponible", lambda: True)

    def rpc(route):
        name = route.request.url.rstrip("/").rsplit("/", 1)[-1]
        payload = {
            "getFiltrosDisponibles": filters,
            "getDashboardEjecutivoProyecto": executive,
            "getDashboardAERTYMProyecto": aer,
        }.get(name, {"ok": True})
        route.fulfill(json={"ok": True, "result": payload})

    portal.route("**/api/rpc/**", rpc)
    return executive, aer


@pytest.mark.parametrize("kind", ["ixb", "aer"])
def test_initial_read_and_refresh_use_api(portal, project_detail, kind):
    executive, aer = project_detail
    data = aer if kind == "aer" else executive
    id = data["proyecto"]["id"]
    requests = []
    portal.on("request", lambda r: requests.append(r.url))
    portal.goto(f"{portal.base}/proyectos/{id}/?volver=%2Foperativa%2F")
    title = ".aer-title" if kind == "aer" else ".ixs-title"
    expect(portal.locator(title)).to_contain_text(id)
    button = portal.locator(
        ".aer-head button" if kind == "aer" else ".ixs-head button"
    )
    button.click()
    expect(portal.locator(title)).to_contain_text(id)
    target = (
        f"/screens/proyectos/{id}/{'aer' if kind == 'aer' else 'ejecutivo'}/"
    )
    assert sum(target in url for url in requests) == 2
    assert not any(
        name in url
        for url in requests
        for name in [
            "rpc/getFiltrosDisponibles/",
            "rpc/getDashboardEjecutivoProyecto/",
            "rpc/getDashboardAERTYMProyecto/",
        ]
    )
    expect(portal.locator(".project-return a")).to_have_attribute(
        "href", "/operativa/"
    )


@pytest.mark.parametrize("kind", ["ixb", "aer"])
@pytest.mark.parametrize("width", [1450, 390])
def test_entry_matches_previous(portal, project_detail, kind, width):
    executive, aer = project_detail
    data = aer if kind == "aer" else executive
    id = data["proyecto"]["id"]
    portal.set_viewport_size({"width": width, "height": 1000})
    title = ".aer-title" if kind == "aer" else ".ixs-title"
    selectors = [
        ".top",
        ".project-return",
        "#view-container",
        ".aer-shell",
        ".aer-head",
        ".aer-tabs",
        ".aer-kpi",
        ".ixs-shell",
        ".ixs-head",
        ".ixs-tabs",
        ".ixs-kpi",
        "table",
        "th",
        "td",
    ]

    def state():
        expect(portal.locator(title)).to_contain_text(id)
        portal.wait_for_load_state("networkidle")
        return portal.evaluate(
            """sels => sels.map(s =>
          [...document.querySelectorAll(s)].map(el => {
            const r=el.getBoundingClientRect(), c=getComputedStyle(el);
            return {box:['x','y','width','height'].map(k=>
                Math.round(r[k]*10)/10),
              css:['color','backgroundColor','fontSize','paddingTop',
                'paddingBottom','marginBottom','boxSizing'].map(k=>c[k]),
              text:el.textContent.replace(/\\s+/g,'')};
          }))""",
            selectors,
        )

    out = Path(f"tmp/migration/project_detail/entry/{kind}/{width}")
    out.mkdir(parents=True, exist_ok=True)
    portal.goto(f"{portal.base}/proyectos/{id}/?vista=anterior")
    before = state()
    portal.screenshot(path=str(out / "previous.png"), full_page=True)
    portal.goto(f"{portal.base}/proyectos/{id}/")
    after = state()
    portal.screenshot(path=str(out / "current.png"), full_page=True)
    differences = {
        s: (a, b)
        for s, a, b in zip(selectors, before, after, strict=True)
        if a != b
    }
    (out / "differences.json").write_text(
        json.dumps(differences, indent=2), encoding="utf-8"
    )
    assert not differences, differences


def test_network_error_can_retry(portal, project_detail):
    count = 0

    def unavailable_once(route):
        nonlocal count
        count += 1
        if count == 1:
            route.fulfill(
                status=502,
                json={
                    "error": {
                        "code": "source",
                        "message": "Fuente no disponible.",
                    }
                },
            )
        else:
            route.continue_()

    portal.route("**/api/v1/screens/proyectos/AER.001/aer/", unavailable_once)
    portal.goto(f"{portal.base}/proyectos/AER.001/")
    expect(portal.locator("#dashboard-proyecto-detalle")).to_contain_text(
        "Fuente no disponible."
    )
    portal.get_by_role("button", name="Reintentar", exact=True).click()
    expect(portal.locator(".aer-title")).to_contain_text("AER.001")
    assert count == 2


def test_failed_filters_still_load_exact_project(portal, project_detail):
    portal.route("**/api/v1/screens/proyectos/filtros/", lambda r: r.abort())
    portal.goto(f"{portal.base}/proyectos/AER.001/")
    expect(portal.locator(".aer-title")).to_contain_text("AER.001")


def test_failed_legacy_download_can_retry(portal, project_detail):
    count = 0

    def unavailable_once(route):
        nonlocal count
        count += 1
        if count == 1:
            route.abort()
        else:
            route.continue_()

    portal.route("**/portal/js/proyecto_detalle.js?*", unavailable_once)
    portal.goto(f"{portal.base}/proyectos/AER.001/")
    expect(portal.locator("#view-container")).to_contain_text(
        "No se pudo cargar la interfaz del proyecto."
    )
    portal.get_by_role("button", name="Reintentar", exact=True).click()
    expect(portal.locator(".aer-title")).to_contain_text("AER.001")
    assert count == 2


def test_aer_refresh_preserves_selected_tab(portal, project_detail):
    portal.goto(f"{portal.base}/proyectos/AER.001/")
    expect(portal.locator(".aer-title")).to_contain_text("AER.001")
    portal.locator(".aer-tabs").get_by_role("button", name="Planeación").click()
    expect(portal.locator(".aer-tabs .active")).to_have_text("Planeación")
    portal.locator(".aer-head button").click()
    expect(portal.locator(".aer-tabs .active")).to_have_text("Planeación")
