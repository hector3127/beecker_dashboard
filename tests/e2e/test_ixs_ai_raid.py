"""Recomendación IA → formulario RAID modular, sin publicar automáticamente."""

import pytest
from playwright.sync_api import expect

from tests.e2e.test_aer_executive import fixed_day as fixed_day
from tests.e2e.test_ixs_ai_actions import actions as actions
from tests.e2e.test_ixs_ai_actions import ia as ia
from tests.e2e.test_ixs_ai_actions import planning as planning
from tests.e2e.test_ixs_ai_sources import enter
from tests.e2e.test_ixs_executive import ixs as ixs
from tests.e2e.test_ixs_raid_create import alta as alta
from tests.e2e.test_project_detail_entry import project_detail as project_detail

pytestmark = pytest.mark.django_db(transaction=True)
LABELS = {"Risk": "Riesgo", "Issue": "Issue", "Opportunity": "Oportunidad"}


def open_recommendation(portal, tipo):
    portal.locator(".ixai-rec").first.get_by_role(
        "button", name=LABELS[tipo], exact=True
    ).click()
    expect(portal.locator("#ixs-raid-form-wrap")).to_be_visible()
    expect(portal.locator("#ixs-raid-api-state")).to_contain_text(
        "Claude configurado"
    )
    portal.wait_for_load_state("networkidle")
    portal.wait_for_timeout(400)
    portal.evaluate(
        "() => new Promise(resolve => requestAnimationFrame(() => "
        "requestAnimationFrame(resolve)))"
    )


@pytest.mark.parametrize("tipo", LABELS)
def test_recommendation_uses_modular_creator_without_old_functions(
    portal, actions, alta, fixed_day, tipo
):
    errors, requests = [], []
    portal.on("pageerror", lambda error: errors.append(str(error)))
    portal.on("request", lambda request: requests.append(request.url))
    enter(portal)
    portal.evaluate("""() => {
      for(const name of ['ixsRaidAbrirCrear','ixsRaidAbrirManual',
        'ixsRaidFormulario','ixsRaidCargar','ixsIARAID'])
        window[name]=()=>{throw Error('previous RAID '+name);};
    }""")
    open_recommendation(portal, tipo)
    expect(portal.locator('[data-raid-key="descripcion"]')).to_have_value(
        "Revisar entrega — Validar fecha y responsable"
    )
    assert not portal.locator("#ixs-raid-modal [onclick]").count()
    assert not any("/api/rpc/" in url for url in requests)
    assert not any(c[0] in {"create", "suggest"} for c in alta[0])
    if tipo == "Issue":
        portal.locator('[data-raid-key="titulo"]').fill("Entrega pendiente")
        portal.locator("#ixs-raid-create").click()
        expect(portal.locator("#ixs-raid-modal")).to_have_count(0)
        created = [call for call in alta[0] if call[0] == "create"]
        assert len(created) == 1
        assert created[0][1:3] == ("AMK.008", "Issue")
        assert created[0][3]["descripcion"] == (
            "Revisar entrega — Validar fecha y responsable"
        )
    assert not errors, errors
