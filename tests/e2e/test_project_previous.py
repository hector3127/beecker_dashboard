"""Enlace IXS al genérico y regreso sin entradas anteriores."""

from pathlib import Path

import pytest
from playwright.sync_api import expect

from tests.e2e.test_aer_executive import fixed_day as fixed_day
from tests.e2e.test_ixs_effort import state as capture_state
from tests.e2e.test_ixs_executive import ixs as ixs
from tests.e2e.test_project_detail_entry import project_detail as project_detail

pytestmark = pytest.mark.django_db(transaction=True)


def open_project(portal, previous=False):
    portal.goto(
        portal.base
        + "/proyectos/AMK.008/"
        + ("?vista=anterior" if previous else "")
    )
    expect(portal.locator(".ixs-head")).to_be_visible()
    portal.wait_for_load_state("networkidle")


@pytest.mark.parametrize("width", [1450, 900, 390])
def test_previous_link_matches_and_returns(portal, ixs, fixed_day, width):
    portal.set_viewport_size({"width": width, "height": 1000})
    directory = Path("tmp/migration/project_detail/project_previous") / str(
        width
    )
    directory.mkdir(parents=True, exist_ok=True)
    states = []
    for previous in [True, False]:
        open_project(portal, previous)
        portal.evaluate("ixsCambiarTab('unknown')")
        portal.get_by_role(
            "button", name="Consultar vista anterior →", exact=True
        ).click()
        expect(
            portal.locator(
                ".gh-header" if not previous else "#grid-riesgos-raid"
            )
        ).to_be_visible()
        portal.wait_for_load_state("networkidle")
        root = portal.locator("#dashboard-proyecto-detalle")
        if previous:
            reference_width = root.evaluate(
                "n=>n.getBoundingClientRect().width"
            )
        root.evaluate(
            """(node,width)=>{
          const host=document.createElement('div');host.style.width=width+'px';
          document.body.append(host);host.append(node);
        }""",
            reference_width,
        )
        portal.mouse.move(0, 0)
        state = capture_state(
            portal, "#dashboard-proyecto-detalle, #dashboard-proyecto-detalle *"
        )
        x, y = state[0]["box"][:2]
        for item in state:
            box = item["box"]
            item["box"] = [round(box[0] - x, 1), round(box[1] - y, 1), *box[2:]]
        states.append(state)
        root.screenshot(
            path=str(directory / ("old.png" if previous else "new.png"))
        )
        portal.get_by_role(
            "button", name="← Volver al nuevo ejecutivo", exact=True
        ).click()
        expect(portal.locator(".ixs-nav .active")).to_have_text("Ejecutivo")
        expect(portal.locator(".ixs-head")).to_be_visible()
    diffs = [
        (i, {key: (a[key], b[key]) for key in a if a[key] != b[key]})
        for i, (a, b) in enumerate(zip(*states, strict=True))
        if a != b
    ]
    assert not diffs, diffs[:5]
    assert not portal.locator(".project-previous-return").count()


def test_link_uses_only_modular_controllers(portal, ixs):
    errors = []
    portal.on("pageerror", lambda error: errors.append(str(error)))
    open_project(portal)
    portal.evaluate("""() => {
      for(const name of ['ixsAbrirVistaAnterior','ixsVolverEjecutivoNuevo',
        'renderDashboardEjecutivoProyecto','_ixsRenderShell','ixsCambiarTab'])
        window[name]=()=>{throw Error('old previous '+name);};
      beeIxsRuntime.select('unknown');
    }""")
    portal.get_by_role(
        "button", name="Consultar vista anterior →", exact=True
    ).click()
    expect(portal.locator(".project-previous-return")).to_be_visible()
    assert not portal.locator(
        ".project-previous-return [style], .project-previous-return [onclick]"
    ).count()
    portal.get_by_role(
        "button", name="← Volver al nuevo ejecutivo", exact=True
    ).click()
    expect(portal.locator(".ixs-nav .active")).to_have_text("Ejecutivo")
    assert not errors, errors


def test_project_seed_keeps_path_id_with_account_query(portal, ixs):
    requests = []
    portal.on("request", lambda request: requests.append(request.url))
    portal.goto(portal.base + "/proyectos/AMK.008/?cuenta=ACME&proyecto=OTHER")
    expect(portal.locator(".ixs-head")).to_be_visible()
    portal.wait_for_load_state("networkidle")
    assert portal.evaluate("beeProjectState.ixs.proyecto.id") == "AMK.008"
    assert any("/AMK.008/ejecutivo/" in url for url in requests)
    assert not any(
        "/OTHER/" in url or "/api/rpc/obtenerVistaCuentaBeecker/" in url
        for url in requests
    )
