"""Las familias reales recorren sus pestañas sin descargar compatibilidad."""

import copy

import pytest
from playwright.sync_api import expect

from tests.e2e.test_aer_executive import fixed_day as fixed_day
from tests.e2e.test_project_detail_entry import project_detail as project_detail

pytestmark = pytest.mark.django_db(transaction=True)


@pytest.mark.parametrize("service", ["AER", "T&M", "IXB", "SaaS", "RaaS"])
def test_all_tabs_are_independent(portal, project_detail, monkeypatch, service):
    from apps.portal.api import project_detail as api

    aer = service in {"AER", "T&M"}
    data = project_detail[1 if aer else 0]
    project = data["proyecto"]
    identifier = project["id"]
    project["servicio"] = service
    monkeypatch.setattr(
        api,
        "get_available_filters",
        lambda: {
            "proyectos": [
                {"id": identifier, "nombre": "Nombre", "servicio": service}
            ],
            "clientes": ["Todos los clientes", "ACME"],
        },
    )
    monkeypatch.setattr(
        api,
        "aer_dashboard" if aer else "get_executive_dashboard",
        lambda project: copy.deepcopy(data),
    )
    urls, errors = [], []
    portal.on("request", lambda request: urls.append(request.url))
    portal.on("pageerror", lambda error: errors.append(str(error)))

    def no_legacy(route):
        route.abort()

    portal.route("**/portal/js/proyecto_detalle.js?*", no_legacy)
    portal.route("**/core/js/gas_shim.js", no_legacy)
    portal.route("**/api/rpc/**", no_legacy)
    portal.goto(portal.base + f"/proyectos/{identifier}/")
    expect(portal.locator(".aer-head" if aer else ".ixs-head")).to_be_visible()
    names = (
        [
            "Planeación",
            "Esfuerzo",
            "Riesgos",
            "Recursos",
            "Acciones",
            "Cliente",
            "✦ IA",
            "Ejecutivo",
        ]
        if aer
        else [
            "Planeación",
            "Esfuerzo",
            "Recursos",
            "Gestión RAID",
            "Acciones",
            "Cliente",
            "Comunicación",
            "Azure DevOps",
            "IA",
            "Ejecutivo",
        ]
    )
    navigation = portal.locator(".aer-tabs" if aer else ".ixs-nav")
    for name in names:
        navigation.get_by_role("button", name=name, exact=True).click()
        expect(navigation.locator(".active")).to_have_text(name)
    portal.wait_for_load_state("networkidle")
    assert not errors, errors
    assert not any(
        token in url
        for url in urls
        for token in ("proyecto_detalle.js", "gas_shim.js", "/api/rpc/")
    ), urls
    assert portal.evaluate("typeof google") == "undefined"


def test_route_id_survives_hidden_sentinel_and_detached_controls(
    portal, project_detail
):
    urls = []
    portal.on("request", lambda request: urls.append(request.url))
    portal.goto(portal.base + "/proyectos/AER.001/?cuenta=ACME")
    expect(portal.locator(".aer-head")).to_be_visible()
    portal.evaluate("""async () => {
      document.getElementById('f-proyecto').value='Todos los proyectos';
      await beeProjectEntryRuntime.load();
    }""")
    expect(portal.locator(".aer-title")).to_contain_text("AER.001")
    portal.evaluate("""async () => {
      document.getElementById('f-proyecto').remove();
      await beeProjectEntryRuntime.load();
    }""")
    assert not any(
        token in url
        for url in urls
        for token in ("proyecto_detalle.js", "gas_shim.js", "/api/rpc/")
    )
