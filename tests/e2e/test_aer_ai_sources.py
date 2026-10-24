"""IA AER parcial: cargas por API, modelo separado y CSS externo idéntico."""

import copy
from pathlib import Path

import pytest
from playwright.sync_api import expect

from tests.e2e.test_aer_executive import fixed_day as fixed_day
from tests.e2e.test_ixs_effort import state
from tests.e2e.test_project_detail_entry import project_detail as project_detail

pytestmark = pytest.mark.django_db(transaction=True)
READS = {
    "obtenerUltimoAnalisisProyectoAER": "analisis",
    "obtenerUltimoResumenEjecutivoAER": "resumen",
    "listarMinutasIAProyectoAER": "minutas",
    "obtenerConfigCarpetaMinutasAER": "config",
    "buscarMinutasCarpetaAER": "archivos",
}


@pytest.fixture
def ia(portal, project_detail, monkeypatch):
    from apps.portal.api import project_aer_ai as api

    responses = {
        "analisis": {"ok": True, "resultado": None},
        "resumen": {"ok": True, "resumen": None},
        "minutas": {
            "ok": True,
            "filas": [
                {
                    "fecha": "2026-10-21",
                    "tema": "Comité",
                    "contenido": "Acuerdos de seguimiento",
                }
            ],
        },
        "config": {"ok": True, "config": {}},
        "archivos": {"ok": True, "totalEncontradas": 0, "archivos": []},
    }
    calls = []

    def read(source, project, context):
        calls.append((source, project, context))
        return copy.deepcopy(responses[source])

    monkeypatch.setattr(api, "read", read)

    def rpc(route):
        name = route.request.url.rstrip("/").rsplit("/", 1)[-1]
        if name in READS:
            route.fulfill(json={"ok": True, "result": responses[READS[name]]})
        else:
            route.fallback()

    portal.route("**/api/rpc/**", rpc)
    return project_detail[1], responses, calls


def enter(page, previous=False):
    page.goto(
        page.base
        + "/proyectos/AER.001/"
        + ("?vista=anterior" if previous else "")
    )
    page.locator(".aer-tabs").get_by_role(
        "button", name="✦ IA", exact=True
    ).click()
    page.wait_for_function(
        "!aerIAState.cargandoAnalisis && !aerIAState.cargandoResumen && "
        "!aerIAState.cargandoConfig && !aerIAState.cargandoMinutas && "
        "!aerIAState.buscando"
    )
    expect(page.locator(".aeri")).to_be_visible()


@pytest.mark.parametrize("width", [1450, 900, 390])
@pytest.mark.parametrize("variant", ["empty", "saved", "drive"])
def test_sources_and_styles_match_previous(
    portal, ia, fixed_day, width, variant
):
    _, responses, calls = ia
    if variant == "empty":
        responses["minutas"]["filas"] = []
    if variant == "saved":
        responses["analisis"]["resultado"] = {
            "analisis": {
                "resumen": ["Proyecto bajo seguimiento"],
                "recomendaciones": [],
                "riesgos": [],
                "preguntas": [],
            },
            "guardadoEn": "2026-10-22 14:30",
            "zonaHoraria": "America/Mexico_City",
        }
    if variant == "drive":
        responses["config"]["config"] = {
            "folderUrl": "https://drive.google.com/drive/folders/demo",
            "nombreFrecuente": "Reunión",
            "nombreBusqueda": "ACME",
        }
    portal.set_viewport_size({"width": width, "height": 1000})
    directory = (
        Path("tmp/migration/project_detail/aer_ai_sources")
        / variant
        / str(width)
    )
    directory.mkdir(parents=True, exist_ok=True)
    snapshots = []
    for previous in [True, False]:
        enter(portal, previous)
        portal.mouse.move(0, 0)
        snapshots.append(state(portal, ".aeri, .aeri *"))
        portal.screenshot(
            path=str(directory / ("old.png" if previous else "new.png")),
            full_page=True,
        )
    assert snapshots[0] == snapshots[1]
    assert {x[0] for x in calls} == {
        "analisis",
        "resumen",
        "minutas",
        "config",
    } | ({"archivos"} if variant == "drive" else set())
    assert portal.locator("link#aer-ia-styles-v55").count() == 1
    assert portal.locator("style#aer-ia-styles-v55").count() == 0


def test_sources_use_api_without_generation_and_reuse_cache(
    portal, ia, fixed_day
):
    urls = []
    portal.on("request", lambda r: urls.append(r.url))
    enter(portal)
    assert len(ia[2]) == 4
    portal.locator(".aer-tabs").get_by_role(
        "button", name="Ejecutivo", exact=True
    ).click()
    portal.locator(".aer-tabs").get_by_role(
        "button", name="✦ IA", exact=True
    ).click()
    expect(portal.locator(".aeri")).to_be_visible()
    assert len(ia[2]) == 4
    assert not any(any(name in url for name in READS) for url in urls)
    assert not any("Claude" in url or "generar" in url for url in urls)


def test_source_failure_retry_and_late_response(portal, ia, fixed_day):
    ia[1]["config"] = {"ok": False, "error": "Fallo de configuración"}
    enter(portal)
    expect(portal.locator(".aer-toast")).to_contain_text(
        "Fallo de configuración"
    )
    ia[1]["config"] = {"ok": True, "config": {"nombreFrecuente": "Nueva"}}
    portal.evaluate("aerIACargarConfigMinutas()")
    portal.wait_for_function("aerIAState.config?.nombreFrecuente === 'Nueva'")
    held = []
    portal.route("**/ia-aer/minutas/", lambda r: held.append(r))
    portal.evaluate("() => {aerIAState.minutas=null;aerIACargarMinutas();}")
    portal.wait_for_timeout(100)
    portal.evaluate(
        "() => {aerIAState={...aerIAState,minutas:[{tema:'Nuevo estado'}]};}"
    )
    held[0].fulfill(
        json={"data": {"ok": True, "filas": [{"tema": "Vieja"}]}, "meta": {}}
    )
    portal.wait_for_timeout(150)
    assert portal.evaluate("aerIAState.minutas") == [{"tema": "Nuevo estado"}]


def test_same_project_refresh_does_not_leave_loading_stuck(
    portal, ia, fixed_day
):
    enter(portal)
    held = []
    portal.route("**/ia-aer/minutas/", lambda route: held.append(route))
    with portal.expect_request("**/ia-aer/minutas/"):
        portal.evaluate("() => {aerIAState.minutas=null;aerIACargarMinutas();}")
    portal.evaluate("() => {aerDashboardData={...aerDashboardData};}")
    held[0].fulfill(
        json={
            "data": {"ok": True, "filas": [{"tema": "Misma cuenta"}]},
            "meta": {},
        }
    )
    portal.wait_for_function("!aerIAState.cargandoMinutas")
    assert portal.evaluate("aerIAState.minutas") == [{"tema": "Misma cuenta"}]
