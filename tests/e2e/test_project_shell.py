"""Encabezados/navegación AER e IXS: diseño, cargas y refrescos seguros."""

import copy
from pathlib import Path

import pytest
from playwright.sync_api import expect

from tests.e2e.test_aer_executive import fixed_day as fixed_day
from tests.e2e.test_ixs_effort import state
from tests.e2e.test_project_detail_entry import project_detail as project_detail

pytestmark = pytest.mark.django_db(transaction=True)


def family_data(project_detail, family):
    return project_detail[1 if family == "aer" else 0]


def enter(page, data, previous=False):
    page.goto(
        page.base
        + f"/proyectos/{data['proyecto']['id']}/"
        + ("?vista=anterior" if previous else "")
    )
    expect(page.locator(".aer-head, .ixs-head")).to_be_visible()
    page.wait_for_load_state("networkidle")


@pytest.mark.parametrize("family", ["aer", "ixs"])
@pytest.mark.parametrize("width", [1450, 900, 390])
@pytest.mark.parametrize("variant", ["full", "empty", "special", "closed"])
def test_header_and_navigation_match_previous(
    portal, project_detail, fixed_day, family, width, variant
):
    data = family_data(project_detail, family)
    p = data["proyecto"]
    if variant == "empty":
        data["proyecto"] = {"id": p["id"]}
    elif variant == "special":
        p.update(
            {
                "nombre": "Proyecto <img> & revisión",
                "cliente": "Cliente & socios",
                "deliveryManager": "Ana <gestión>",
                "sponsor": "Sponsor 'uno'",
                "pm": "PM & equipo",
            }
        )
        data["cerrado"] = False
        data["historialCompleto"] = [
            {
                "fase": "Etapa & <revisión>",
                "fechaInicio": "2026-10-01",
                "fechaFin": "2026-11-01",
                "enCurso": True,
            }
        ]
    elif variant == "closed":
        data["cerrado"] = True
        p["estado"] = "Cerrado"
    portal.set_viewport_size({"width": width, "height": 1000})
    selector = (
        ".aer-head, .aer-head *, .aer-tabs, .aer-tabs *"
        if family == "aer"
        else ".ixs-head, .ixs-head *, .ixs-nav, .ixs-nav *"
    )
    directory = (
        Path("tmp/migration/project_detail/shell")
        / family
        / variant
        / str(width)
    )
    directory.mkdir(parents=True, exist_ok=True)
    states = []
    for previous in [True, False]:
        enter(portal, data, previous)
        portal.mouse.move(0, 0)
        states.append(state(portal, selector))
        portal.screenshot(
            path=str(directory / ("old.png" if previous else "new.png")),
            full_page=True,
        )
    assert states[0] == states[1]
    assert portal.locator(selector).locator("[onclick]").count() == 0
    assert portal.locator(".aer-head img, .ixs-head img").count() == 0


def isolate_panes(page, family):
    page.evaluate(
        """family => {
      window.shellLoads=[];
      if(family==='aer'){
        _aerRenderTab=()=>{};
        if(window.beeAerRuntime){
          beeAerRuntime.dispatch=()=>{};
          beeAerRuntime.load=name=>shellLoads.push(name);
        }
        aerIACargarAnalisis=()=>shellLoads.push('analysis');
        aerIACargarMinutas=()=>shellLoads.push('minutes');
        aerIACargarConfigMinutas=()=>shellLoads.push('config');
        aerIACargarResumenEjecutivo=()=>shellLoads.push('summary');
        aerIACargarAccionesPartes=()=>shellLoads.push('parts');
        _aerEstadoClase=()=>{throw Error('old state helper')};
      }else{
        _ixsRenderTab=()=>{};
        _ixsEtapaActual=()=>{throw Error('old stage helper')};
      }
      const descriptor=Object.getOwnPropertyDescriptor(
        Element.prototype,'innerHTML');
      Object.defineProperty(Element.prototype,'innerHTML',{...descriptor,set(value){
        if(this.id==='dashboard-proyecto-detalle')
          throw Error('old shell renderer');
        descriptor.set.call(this,value);
      }});
    }""",
        family,
    )


@pytest.mark.parametrize("family", ["aer", "ixs"])
def test_each_tab_uses_external_events_and_original_load_order(
    portal, project_detail, fixed_day, family
):
    data = family_data(project_detail, family)
    enter(portal, data)
    isolate_panes(portal, family)
    nav = portal.locator(".aer-tabs" if family == "aer" else ".ixs-nav")
    names = (
        [
            "Ejecutivo",
            "Planeación",
            "Esfuerzo",
            "Riesgos",
            "Acciones",
            "Recursos",
            "Cliente",
            "✦ IA",
        ]
        if family == "aer"
        else [
            "Ejecutivo",
            "Planeación",
            "Esfuerzo",
            "Recursos",
            "Gestión RAID",
            "Acciones",
            "Cliente",
            "Comunicación",
            "Azure DevOps",
            "IA",
        ]
    )
    for name in names:
        nav.get_by_role("button", name=name, exact=True).click()
        expect(nav.locator("button.active")).to_have_text(name)
    if family == "aer":
        assert portal.evaluate("shellLoads") == [
            "parts",
            "analysis",
            "minutes",
            "config",
            "summary",
            "parts",
        ]
        portal.evaluate("aerCambiarTab('minutas')")
        assert portal.evaluate("aerTabActual") == "ia"
        expect(nav.locator("button.active")).to_have_text("✦ IA")
    assert nav.locator("[onclick]").count() == 0


@pytest.mark.parametrize("family", ["aer", "ixs"])
def test_refresh_preserves_family_tab_behavior_and_api(
    portal, project_detail, fixed_day, family
):
    data = family_data(project_detail, family)
    enter(portal, data)
    isolate_panes(portal, family)
    portal.locator(".aer-tabs, .ixs-nav").get_by_role(
        "button", name="Recursos", exact=True
    ).click()
    calls = []
    resource = "aer" if family == "aer" else "ejecutivo"
    updated = copy.deepcopy(data)
    updated["proyecto"]["nombre"] = "Proyecto actualizado"

    def reload(route):
        calls.append(route.request.method)
        route.fulfill(json={"data": updated, "meta": {}})

    portal.route(f"**/screens/proyectos/*/{resource}/", reload)
    portal.locator(".aer-head, .ixs-head").get_by_role(
        "button", name="Actualizar"
    ).click()
    expect(portal.locator(".aer-title, .ixs-title")).to_contain_text(
        "Proyecto actualizado"
    )
    expect(
        portal.locator(".aer-tabs, .ixs-nav").locator("button.active")
    ).to_have_text("Recursos" if family == "aer" else "Ejecutivo")
    assert calls == ["GET"]
    expect(portal.locator(".project-return a")).to_have_attribute(
        "href", "/operativa/"
    )


@pytest.mark.parametrize("family", ["aer", "ixs"])
def test_refresh_ignores_superseded_response_before_newer_one_arrives(
    portal, project_detail, fixed_day, family
):
    data = family_data(project_detail, family)
    enter(portal, data)
    isolate_panes(portal, family)
    held = []
    resource = "aer" if family == "aer" else "ejecutivo"
    pattern = f"**/screens/proyectos/*/{resource}/"
    portal.route(pattern, lambda route: held.append(route))
    refresh = portal.locator(".aer-head, .ixs-head").get_by_role(
        "button", name="Actualizar"
    )
    for _ in range(2):
        with portal.expect_request(pattern):
            refresh.click()
    old = copy.deepcopy(data)
    old["proyecto"]["nombre"] = "Respuesta anterior"
    held[0].fulfill(json={"data": old, "meta": {}})
    portal.wait_for_timeout(150)
    expect(portal.locator(".aer-title, .ixs-title")).not_to_contain_text(
        "Respuesta anterior"
    )
    latest = copy.deepcopy(data)
    latest["proyecto"]["nombre"] = "Respuesta reciente"
    held[1].fulfill(json={"data": latest, "meta": {}})
    expect(portal.locator(".aer-title, .ixs-title")).to_contain_text(
        "Respuesta reciente"
    )


@pytest.mark.parametrize("family", ["aer", "ixs"])
def test_invalid_refresh_retains_original_error_presentation(
    portal, project_detail, fixed_day, family
):
    enter(portal, family_data(project_detail, family))
    resource = "aer" if family == "aer" else "ejecutivo"
    portal.route(
        f"**/screens/proyectos/*/{resource}/",
        lambda r: r.fulfill(
            json={"data": {"ok": False, "error": "Fallo simulado"}, "meta": {}}
        ),
    )
    portal.locator(".aer-head, .ixs-head").get_by_role(
        "button", name="Actualizar"
    ).click()
    expect(portal.locator("#view-container")).to_contain_text(
        "Error cargando datos"
        if family == "aer"
        else "No se pudo actualizar el proyecto."
    )


@pytest.mark.parametrize("family", ["aer", "ixs"])
def test_refresh_does_not_replace_another_family(
    portal, project_detail, fixed_day, family
):
    data = family_data(project_detail, family)
    enter(portal, data)
    held = []
    resource = "aer" if family == "aer" else "ejecutivo"
    pattern = f"**/screens/proyectos/*/{resource}/"
    portal.route(pattern, lambda route: held.append(route))
    with portal.expect_request(pattern):
        portal.locator(".aer-head, .ixs-head").get_by_role(
            "button", name="Actualizar"
        ).click()
    other = "ixs" if family == "aer" else "aer"
    portal.evaluate(
        """family => {
      const root=document.getElementById('dashboard-proyecto-detalle');
      const shell=document.createElement('div');shell.className=family+'-shell';
      shell.textContent='Otro proyecto';root.replaceChildren(shell);
    }""",
        other,
    )
    held[0].fulfill(json={"data": data, "meta": {}})
    portal.wait_for_timeout(150)
    expect(portal.locator("#dashboard-proyecto-detalle")).to_have_text(
        "Otro proyecto"
    )
