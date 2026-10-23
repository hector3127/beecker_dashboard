"""Ejecutivo IXB/SaaS/RaaS: diseño anterior y lecturas diferidas."""

import copy
import json
from pathlib import Path

import pytest
from playwright.sync_api import expect

from tests.e2e.test_aer_executive import fixed_day as fixed_day
from tests.e2e.test_project_detail_entry import project_detail as project_detail

pytestmark = pytest.mark.django_db(transaction=True)
PAGE = "/proyectos/AMK.008/"


@pytest.fixture
def ixs(portal, project_detail, monkeypatch):
    from apps.portal.api import project_detail as api

    data, _ = project_detail
    data.clear()
    data.update(
        json.loads(
            Path("tests/ejecutivo/project_integrated_expected.json").read_text(
                encoding="utf-8"
            )
        )[5]
    )
    responses = {
        "get_project_raid": {
            "ok": True,
            "totalRiesgos": 2,
            "totalPendientes": 0,
            "totalOportunidades": 3,
            "riesgos": [
                {
                    "id": 1,
                    "descripcion": "Accesos pendientes",
                    "impacto": "Alto",
                    "estado": "Active",
                },
                {"id": 1, "descripcion": "Duplicado"},
            ],
        },
        "tasks_dashboard": {
            "ok": True,
            "invOperativa": 2.5,
            "invComercial": 0,
            "totalHoras": 10.75,
            "nomenclatura": "AMK.008",
            "rango": {"fechaInicio": "2026-07-01", "fechaFin": "2026-10-23"},
            "tasks": [
                {"nombre": "Desarrollo", "horas": 8.25},
                {"nombre": "Inversión", "horas": 2.5},
                {"nombre": "Sin horas", "horas": 0},
            ],
        },
        "resources_dashboard": {
            "ok": True,
            "filas": [{"nombre": "  ANA PEREZ ", "activo": False}],
        },
        "stages_dashboard": {
            "ok": True,
            **{
                k: copy.deepcopy(data[k])
                for k in ("hitos", "historialCompleto", "suspensiones")
            },
        },
    }
    for source in responses:
        monkeypatch.setattr(
            api,
            source,
            lambda project, key=source: copy.deepcopy(responses[key]),
        )
    methods = dict(
        zip(
            [
                "obtenerRaidProyectoEjecutivoAzure",
                "obtenerResumenTasksTagsClockifyProyecto",
                "ixsRecursosLeer",
                "obtenerEtapasHistoricoAIProyecto",
            ],
            responses,
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
    return data, responses


@pytest.mark.parametrize("variant", ["full", "empty", "attention"])
@pytest.mark.parametrize("width", [1450, 900, 390])
def test_every_executive_element_matches(
    portal, ixs, fixed_day, variant, width
):
    data, responses = ixs
    if variant == "empty":
        data.clear()
        data.update({"proyecto": {"id": "AMK.008"}})
        for source in responses:
            responses[source] = {"ok": True}
    elif variant == "attention":
        data["kpisExtra"]["pctCumplimientoFinanciero"] = 130
        data["avance"].update(
            {
                "fuente": "Hitos y fechas de etapa",
                "pct": 0,
                "indiceRitmo": 0,
                "etapaActualPct": 0,
            }
        )
        data["presupuesto"]["consumoDisponible"] = False
        data["proyecto"].update(
            {"estadoGeneral": "EN RIESGO", "nivelRiesgoFecha": "Alto"}
        )
        data["suspensiones"] = [
            {"fechaInicio": "2026-10-01", "fechaFin": "2026-10-04"}
        ]
        data["hitosAdicionales"].extend(
            [
                {"tipo": "Demo", "fecha": "2026-10-05"},
                {"tipo": "UAT", "fecha": "2026-10-05"},
            ]
        )
    portal.set_viewport_size({"width": width, "height": 1000})

    def state():
        expect(portal.locator("#ixs-tab-contenido .ixs-kpis")).to_be_visible()
        portal.wait_for_load_state("networkidle")
        return portal.evaluate("""() => [...document.querySelectorAll(
            '#ixs-tab-contenido *')].map(el => {
            const r=el.getBoundingClientRect(),c=getComputedStyle(el);
            return {tag:el.tagName.toLowerCase(),
              box:['x','y','width','height'].map(k=>Math.round(r[k]*10)/10),
              css:['fontSize','fontWeight','lineHeight','color','backgroundColor','backgroundImage','paddingTop','paddingBottom','marginTop','marginBottom','display','gap'].map(k=>c[k]),
              text:el.textContent.replace(/\\s+/g,'')};
        })""")

    out = Path(f"tmp/migration/project_detail/ixs_executive/{variant}/{width}")
    out.mkdir(parents=True, exist_ok=True)
    portal.goto(portal.base + PAGE + "?vista=anterior")
    before = state()
    portal.screenshot(path=str(out / "previous.png"), full_page=True)
    portal.goto(portal.base + PAGE)
    after = state()
    portal.screenshot(path=str(out / "current.png"), full_page=True)
    (out / "differences.json").write_text(
        json.dumps(
            {
                "previous_count": len(before),
                "current_count": len(after),
                "differences": [
                    {"index": i, "previous": a, "current": b}
                    for i, (a, b) in enumerate(zip(before, after, strict=False))
                    if a != b
                ],
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    assert after == before
    expect(portal.locator("#ixs-tab-contenido")).to_have_attribute(
        "data-renderer", "modular"
    )
    assert portal.locator("#ixs-tab-contenido [onclick]").count() == 0
    assert portal.locator("style#ixs-v74-styles").count() == 0
    assert portal.locator("link#ixs-v74-styles").count() == 1


def test_reads_and_keyboard_expansion(portal, ixs):
    data, _ = ixs
    data["filasRecursosCompleto"].append(
        {"nombre": "Recurso seis", "horasReales": 1, "horasEstimadas": 0}
    )
    data["porRol"].append(
        {"rol": "Rol seis", "horasReales": 1, "horasEstimadas": 0}
    )
    data["historialCompleto"] = []
    requests = []
    portal.on("request", lambda r: requests.append(r.url))
    portal.goto(portal.base + PAGE)
    expect(
        portal.locator("#ixs-gantt-historico .ixs-time-bar.real")
    ).to_have_count(2)
    expect(portal.locator("#ixs-raid-issues")).to_have_text("0")
    expect(portal.locator("[data-resource-workload] td[title]")).to_have_text(
        "Ana Pérez"
    )
    expect(portal.locator("#ixs-tasks-content")).not_to_contain_text(
        "Sin horas"
    )
    buttons = portal.locator(".ixs-more-btn")
    expect(buttons).to_have_count(2)
    for button in buttons.all():
        button.focus()
        button.press("Enter")
        expect(button).to_have_text("Ver menos ↑")
        expect(button.locator("xpath=preceding-sibling::div")).to_be_visible()
        button.press("Enter")
        expect(button.locator("xpath=preceding-sibling::div")).to_be_hidden()
    for suffix in ("raid/", "tasks/", "recursos/", "etapas/"):
        assert any(
            f"/screens/proyectos/AMK.008/{suffix}" in url for url in requests
        )
    assert not any("/api/rpc/" in url for url in requests)


def test_source_errors_and_return_to_executive(portal, ixs):
    _, responses = ixs
    responses["get_project_raid"] = {
        "ok": False,
        "error": "Azure no disponible",
    }
    responses["tasks_dashboard"] = {
        "ok": False,
        "error": "Clockify no disponible",
    }
    portal.goto(portal.base + PAGE)
    expect(portal.locator("#ixs-risks-content")).to_have_text(
        "Azure: Azure no disponible"
    )
    expect(portal.locator("#ixs-tasks-content")).to_have_text(
        "No disponibles: Clockify no disponible"
    )
    expect(portal.locator(".ixs-kpis")).to_contain_text("42.8%")
    portal.locator(".ixs-nav").get_by_role(
        "button", name="Esfuerzo", exact=True
    ).click()
    responses["get_project_raid"] = {"ok": True, "riesgos": []}
    responses["tasks_dashboard"] = {"ok": True, "tasks": []}
    portal.locator(".ixs-nav").get_by_role(
        "button", name="Ejecutivo", exact=True
    ).click()
    expect(portal.locator("#ixs-risks-content")).to_contain_text(
        "Sin riesgos Active / Proposed"
    )
    expect(portal.locator("#ixs-tasks-content")).to_contain_text(
        "Sin tasks con horas"
    )


def test_source_text_is_safe(portal, ixs):
    data, responses = ixs
    text = '<img src=x onerror="window.ixsInjected=true">'
    data["filasRecursosCompleto"][0]["nombre"] = text
    data["hitosAdicionales"][0]["tipo"] = text
    responses["get_project_raid"]["riesgos"][0]["descripcion"] = text
    responses["tasks_dashboard"]["tasks"][0]["nombre"] = text
    portal.goto(portal.base + PAGE)
    expect(portal.locator("#ixs-risks-content")).to_contain_text(text)
    expect(portal.locator("#ixs-tasks-content")).to_contain_text(text)
    assert portal.locator("#ixs-tab-contenido img").count() == 0
    assert portal.evaluate("window.ixsInjected") is None


def test_transport_errors_recover_on_return(portal, ixs):
    def fail(route):
        route.abort("failed")

    for suffix in ("raid", "tasks"):
        portal.route(f"**/screens/proyectos/AMK.008/{suffix}/", fail)
    portal.goto(portal.base + PAGE)
    expect(portal.locator("#ixs-risks-content")).to_contain_text("Error Azure:")
    expect(portal.locator("#ixs-tasks-content")).to_contain_text(
        "Error Clockify:"
    )
    for suffix in ("raid", "tasks"):
        portal.unroute(f"**/screens/proyectos/AMK.008/{suffix}/", fail)
    portal.locator(".ixs-nav").get_by_role(
        "button", name="Esfuerzo", exact=True
    ).click()
    portal.locator(".ixs-nav").get_by_role(
        "button", name="Ejecutivo", exact=True
    ).click()
    expect(portal.locator("#ixs-risks-content")).to_contain_text(
        "Accesos pendientes"
    )
    expect(portal.locator("#ixs-tasks-content")).to_contain_text("Desarrollo")


def test_late_responses_do_not_replace_a_new_executive(portal, ixs):
    held = []

    def hold(route):
        # Hold only the first executive's reads. Effort also reads tasks now.
        if any(r.request.url == route.request.url for r in held):
            route.fallback()
        else:
            held.append(route)

    for suffix in ("raid", "tasks"):
        portal.route(f"**/screens/proyectos/AMK.008/{suffix}/", hold)
    with (
        portal.expect_request("**/screens/proyectos/AMK.008/raid/"),
        portal.expect_request("**/screens/proyectos/AMK.008/tasks/"),
    ):
        portal.goto(portal.base + PAGE)
    portal.locator(".ixs-nav").get_by_role(
        "button", name="Esfuerzo", exact=True
    ).click()
    for suffix in ("raid", "tasks"):
        portal.unroute(f"**/screens/proyectos/AMK.008/{suffix}/", hold)
    portal.locator(".ixs-nav").get_by_role(
        "button", name="Ejecutivo", exact=True
    ).click()
    expect(portal.locator("#ixs-risks-content")).to_contain_text(
        "Accesos pendientes"
    )
    expect(portal.locator("#ixs-tasks-content")).to_contain_text("Desarrollo")
    assert len(held) == 2
    for route in held:
        route.fulfill(
            json={
                "data": {"ok": False, "error": "Respuesta anterior"},
                "meta": {},
            }
        )
    portal.wait_for_load_state("networkidle")
    expect(portal.locator("#ixs-risks-content")).to_contain_text(
        "Accesos pendientes"
    )
    expect(portal.locator("#ixs-tasks-content")).to_contain_text("Desarrollo")
