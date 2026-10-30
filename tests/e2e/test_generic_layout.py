"""Tarjetas y controles genéricos: estructura original y acciones modulares."""

import pytest
from playwright.sync_api import expect

from tests.e2e.test_aer_executive import fixed_day as fixed_day
from tests.e2e.test_generic_sources import open_generic
from tests.e2e.test_ixs_executive import ixs as ixs
from tests.e2e.test_project_detail_entry import project_detail as project_detail

pytestmark = pytest.mark.django_db(transaction=True)


def test_actions_open_migrated_forms_without_legacy_helpers(portal, ixs):
    data, _ = ixs
    open_generic(portal, data)
    portal.evaluate("""() => {
      abrirModalHito=()=>{throw Error('old milestone form');};
      abrirModalRiesgo=()=>{throw Error('old risk form');};
    }""")
    portal.get_by_role("button", name="+ Agregar Riesgo", exact=True).click()
    expect(portal.locator("#modal-riesgo-overlay")).to_be_visible()
    portal.get_by_role("button", name="Cancelar", exact=True).click()
    portal.get_by_role("button", name="+ Agregar Hito", exact=True).click()
    expect(portal.locator("#modal-hito-overlay")).to_be_visible()


def test_layout_uses_dom_without_inline_html(portal, ixs):
    data, _ = ixs
    open_generic(portal, data)
    result = portal.evaluate("""async () => {
      const path='/static/app/scripts/pages/project_detail/sections/';
      const {mountGenericLayout}=await import(path+'generic_layout_view.js');
      const descriptor=Object.getOwnPropertyDescriptor(
        Element.prototype,'innerHTML');
      Object.defineProperty(Element.prototype,'innerHTML',{...descriptor,
        set(){throw Error('layout HTML');}});
      const target=document.createElement('div');let risk=0,milestone=0;
      mountGenericLayout(target,{risk:()=>risk++,milestone:()=>milestone++});
      const buttons=target.querySelectorAll('button');
      buttons[0].click();buttons[1].click();
      return {risk,milestone,
        inline:target.querySelectorAll('[style],[onclick]').length,
        grids:target.querySelectorAll('.grid-3').length};
    }""")
    assert result == {"risk": 1, "milestone": 1, "inline": 0, "grids": 4}


@pytest.mark.parametrize("retry", [False, True])
def test_generic_milestone_save_reloads_without_legacy(
    portal, ixs, monkeypatch, retry
):
    from apps.portal.api import project_detail as api

    data, _ = ixs
    calls, reloads = [], []
    monkeypatch.setattr(api.milestones, "get_milestone_types", lambda: ["Demo"])

    def save(project, items):
        calls.append((project, items))
        return {"ok": True, "hitos": []}

    monkeypatch.setattr(api.milestones, "save_milestone_batch", save)
    open_generic(portal, data)
    portal.evaluate("""() => {
      loadDashboard=()=>{throw Error('legacy reload');};
      abrirModalHito=()=>{throw Error('legacy milestone');};
    }""")

    def reload(route):
        reloads.append(route.request.method)
        if retry and len(reloads) == 1:
            route.fulfill(status=503, json={"error": {"message": "Reintenta"}})
        else:
            route.fallback()

    portal.route("**/screens/proyectos/AMK.008/ejecutivo/", reload)
    portal.get_by_role("button", name="+ Agregar Hito", exact=True).click()
    expect(portal.locator("#modal-hito-overlay")).to_be_visible()
    portal.locator(".mh-fecha").fill("2026-11-10")
    portal.locator(".mh-obs").fill("Nota")
    portal.locator("#mh-btn-guardar").click()
    expect(portal.locator("#modal-hito-overlay")).to_have_count(0)
    if retry:
        expect(portal.locator("#dashboard-proyecto-detalle")).to_contain_text(
            "Error cargando proyecto"
        )
        portal.get_by_role("button", name="Reintentar", exact=True).click()
    expect(portal.locator(".ixs-head")).to_be_visible()
    assert reloads == ["GET"] * (2 if retry else 1)
    assert calls == [
        (
            "AMK.008",
            [{"tipo": "Demo", "fechaISO": "2026-11-10", "observacion": "Nota"}],
        )
    ]
