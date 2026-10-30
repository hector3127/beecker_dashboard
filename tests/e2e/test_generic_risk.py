"""Alta de riesgos genéricos: paridad, POST, reintento y guardias de sesión."""

import copy

import pytest
from playwright.sync_api import expect

from tests.e2e.test_aer_executive import fixed_day as fixed_day
from tests.e2e.test_generic_sources import open_generic
from tests.e2e.test_ixs_executive import ixs as ixs
from tests.e2e.test_project_detail_entry import project_detail as project_detail

pytestmark = pytest.mark.django_db(transaction=True)


@pytest.fixture
def risk(portal, ixs, monkeypatch):
    from apps.portal.api import project_detail as api

    result, calls = {"ok": True}, []

    def save(*args):
        calls.append(args)
        return copy.deepcopy(result)

    monkeypatch.setattr(api.milestones, "add_risk", save)

    def rpc(route):
        save(*route.request.post_data_json["args"])
        route.fulfill(json={"ok": True, "result": result})

    portal.route("**/api/rpc/agregarRiesgoManual/", rpc)
    return ixs[0], result, calls


def open_risk(portal, data):
    open_generic(portal, data)
    portal.get_by_role("button", name="+ Agregar Riesgo", exact=True).click()
    expect(portal.locator("#modal-riesgo-overlay")).to_be_visible()


def fill_risk(portal):
    portal.locator("#mr-descripcion").fill("  Accesos pendientes  ")
    portal.locator("#mr-impacto").select_option("Alto")
    portal.locator("#mr-probabilidad").select_option("Alta")
    portal.locator("#mr-responsable").fill(" Ana ")


def test_save_uses_api_exact_values_and_direct_reload(portal, risk):
    data, _, calls = risk
    urls = []
    portal.on("request", lambda request: urls.append(request.url))
    open_risk(portal, data)
    portal.evaluate("""() => {
      loadDashboard=()=>{throw Error('legacy reload');};
    }""")
    fill_risk(portal)
    portal.locator("#mr-btn-guardar").click()
    expect(portal.locator("#modal-riesgo-overlay")).to_have_count(0)
    expect(portal.locator(".ixs-head")).to_be_visible()
    assert calls == [("AMK.008", "Accesos pendientes", "Alto", "Alta", " Ana ")]
    assert any("/AMK.008/riesgos-manuales/" in url for url in urls)
    assert not any("rpc/agregarRiesgoManual/" in url for url in urls)


def test_validation_error_retry_and_close(portal, risk):
    data, result, calls = risk
    open_risk(portal, data)
    portal.locator("#mr-btn-guardar").click()
    expect(portal.locator("#mr-error")).to_have_text(
        "Falta la descripción del riesgo."
    )
    assert calls == []
    fill_risk(portal)
    result.update({"ok": False, "error": "Validación del servicio"})
    portal.locator("#mr-btn-guardar").click()
    expect(portal.locator("#mr-error")).to_have_text(
        "Error al guardar: Validación del servicio"
    )
    expect(portal.locator("#mr-btn-guardar")).to_be_enabled()
    result.update({"ok": True})
    portal.locator("#mr-btn-guardar").click()
    expect(portal.locator("#modal-riesgo-overlay")).to_have_count(0)
    assert len(calls) == 2


@pytest.mark.parametrize("kind", ["cancel", "cross", "outside"])
def test_close_does_not_write(portal, risk, kind):
    data, _, calls = risk
    open_risk(portal, data)
    if kind == "cancel":
        portal.get_by_role("button", name="Cancelar", exact=True).click()
    elif kind == "cross":
        portal.locator(".gr-close").click()
    else:
        portal.locator("#modal-riesgo-overlay").click(position={"x": 2, "y": 2})
    expect(portal.locator("#modal-riesgo-overlay")).to_have_count(0)
    assert not calls


def test_transport_failure_and_retry(portal, risk):
    data, _, calls = risk
    open_risk(portal, data)
    portal.route(
        "**/riesgos-manuales/",
        lambda route: route.fulfill(
            status=503, json={"error": {"message": "Fuente no disponible"}}
        ),
    )
    fill_risk(portal)
    portal.locator("#mr-btn-guardar").click()
    expect(portal.locator("#mr-error")).to_contain_text("Error del servidor:")
    expect(portal.locator("#mr-btn-guardar")).to_be_enabled()
    assert not calls
    portal.unroute("**/riesgos-manuales/")
    portal.locator("#mr-btn-guardar").click()
    expect(portal.locator("#modal-riesgo-overlay")).to_have_count(0)


def test_busy_and_late_success_do_not_close_reopened_form(portal, risk):
    data, _, calls = risk
    open_risk(portal, data)
    portal.evaluate("""() => {
      window.testRiskCalls=0;
      beeProjectData.saveManualRisk=()=>{
        window.testRiskCalls++;
        return new Promise(resolve=>window.finishRiskSave=resolve);
      };
    }""")
    fill_risk(portal)
    portal.locator("#mr-btn-guardar").click()
    expect(portal.locator("#mr-btn-guardar")).to_have_text("Guardando...")
    expect(portal.locator("#mr-btn-guardar")).to_be_disabled()
    portal.get_by_role("button", name="Cancelar", exact=True).click()
    portal.get_by_role("button", name="+ Agregar Riesgo", exact=True).click()
    portal.locator("#mr-descripcion").fill("Otro borrador")
    portal.evaluate("""async () => {
      finishRiskSave({ok:true});await Promise.resolve();
    }""")
    expect(portal.locator("#modal-riesgo-overlay")).to_be_visible()
    expect(portal.locator("#mr-descripcion")).to_have_value("Otro borrador")
    assert portal.evaluate("testRiskCalls") == 1
    assert not calls


def test_server_error_is_plain_text_without_html(portal, risk):
    data, result, _ = risk
    attack = '<img src=x onerror="window.riskInjected=true">'
    result.update({"ok": False, "error": attack})
    open_risk(portal, data)
    fill_risk(portal)
    portal.evaluate("""() => {
      const descriptor=Object.getOwnPropertyDescriptor(
        Element.prototype,'innerHTML');
      Object.defineProperty(Element.prototype,'innerHTML',{...descriptor,
        set(){throw Error('legacy form interpolation');}});
    }""")
    portal.locator("#mr-btn-guardar").click()
    expect(portal.locator("#mr-error")).to_have_text(
        "Error al guardar: " + attack
    )
    assert not portal.locator("#modal-riesgo-overlay img").count()
    assert not portal.evaluate("!!window.riskInjected")
