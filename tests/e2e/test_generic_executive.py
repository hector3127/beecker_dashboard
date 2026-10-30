"""Ejecutivo genérico modular: ruta directa, error, reintento y DOM seguro."""

import copy

import pytest
from playwright.sync_api import expect

from tests.e2e.test_aer_executive import fixed_day as fixed_day
from tests.e2e.test_generic_sources import open_generic
from tests.e2e.test_ixs_executive import ixs as ixs
from tests.e2e.test_project_detail_entry import project_detail as project_detail

pytestmark = pytest.mark.django_db(transaction=True)


@pytest.fixture
def generic(portal, ixs, monkeypatch):
    from apps.portal.api import project_detail as api

    data, _ = ixs
    data["proyecto"].update(id="GEN.001", servicio="CUSTOM")
    monkeypatch.setattr(
        api,
        "get_available_filters",
        lambda: {
            "proyectos": [
                {"id": "GEN.001", "nombre": "Genérico", "servicio": "CUSTOM"}
            ],
            "clientes": ["Todos los clientes", "ACME"],
        },
    )
    monkeypatch.setattr(
        api, "get_executive_dashboard", lambda project: copy.deepcopy(data)
    )
    return data


@pytest.mark.parametrize("retry", [False, True])
def test_direct_generic_entry_and_refresh_without_old_renderer(
    portal, generic, retry
):
    urls, errors = [], []
    portal.on("request", lambda request: urls.append(request.url))
    portal.on("pageerror", lambda error: errors.append(str(error)))
    portal.goto(portal.base + "/proyectos/GEN.001/?volver=%2Foperativa%2F")
    expect(portal.locator(".gh-header")).to_contain_text("GEN.001")
    portal.wait_for_load_state("networkidle")
    portal.evaluate("""() => {
      for(const name of ['renderDashboardEjecutivoProyecto','loadDashboard',
        '_pintarRangoClockifyProyecto','cargarRaidProyectoEjecutivoAzure',
        'cargarHorasTasksProyectoClockify','_ixsFechaSalidaPRD'])
        window[name]=()=>{throw Error('old generic '+name);};
    }""")
    reloads = []

    def reload(route):
        reloads.append(route.request.method)
        if retry and len(reloads) == 1:
            route.fulfill(status=503, json={"error": {"message": "Reintenta"}})
        else:
            route.fallback()

    portal.route("**/GEN.001/ejecutivo/", reload)
    portal.evaluate("document.getElementById('btn-refresh').click()")
    if retry:
        expect(portal.locator("#dashboard-proyecto-detalle")).to_contain_text(
            "Error cargando proyecto"
        )
        portal.get_by_role("button", name="Reintentar", exact=True).click()
    expect(portal.locator(".gh-header")).to_contain_text("GEN.001")
    portal.wait_for_load_state("networkidle")
    assert reloads == ["GET"] * (2 if retry else 1)
    assert portal.evaluate("beeProjectState.projectId") == "GEN.001"
    expect(portal.locator(".project-return a")).to_have_attribute(
        "href", "/operativa/"
    )
    for suffix in ["clockify-rango", "raid", "tasks"]:
        assert any(f"/GEN.001/{suffix}/" in url for url in urls)
    assert not any("/api/rpc/" in url for url in urls)
    assert not errors, errors


def test_full_mount_and_error_without_html_or_legacy_helpers(portal, ixs):
    data, _ = ixs
    open_generic(portal, data)
    result = portal.evaluate(
        """data => {
      const attack='<img src=x onerror="window.genericAttack=true">';
      data.proyecto.nombre=attack;
      const descriptor=Object.getOwnPropertyDescriptor(
        Element.prototype,'innerHTML');
      Object.defineProperty(Element.prototype,'innerHTML',{...descriptor,
        set(){throw Error('generic HTML interpolation');}});
      beeGenericExecutive.mount(data);
      const root=document.getElementById('dashboard-proyecto-detalle');
      const text=root.textContent.includes(attack);
      const images=root.querySelectorAll('img').length;
      beeGenericExecutive.mount({errorServidor:attack});
      return {text,images,error:root.textContent==='Error: '+attack,
        attack:!!window.genericAttack};
    }""",
        data,
    )
    assert result == {"text": True, "images": 0, "error": True, "attack": False}
