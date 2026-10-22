"""Acuerdos en el navegador: lo que cada persona puede ver y cambiar."""

import pytest
from playwright.sync_api import expect

from apps.access.scope import AccessScope
from apps.portal.models import ExecutiveAgreement

pytestmark = pytest.mark.django_db(transaction=True)

CUENTA = "/cuenta/clinica-sur/?nombre=Clinica+Sur"
READ = frozenset({"view_agreements"})
BOTH = frozenset({"view_agreements", "edit_agreements"})


def browser_session(portal, client):
    """Pasa la sesion de la persona firmada al navegador."""
    portal.context.add_cookies(
        [
            {
                "name": "sessionid",
                "value": client.cookies["sessionid"].value,
                "url": portal.base,
            }
        ]
    )


@pytest.fixture
def records():
    return (
        ExecutiveAgreement.objects.create(
            account="Clinica Sur", title="Revisar fase 2"
        ),
        ExecutiveAgreement.objects.create(
            account="ACME", title="Cerrar renovacion"
        ),
    )


def test_view_only_person_reads_without_edit_controls(
    portal, datos, enforced, client, records
):
    enforced("lectora", caps=READ)
    browser_session(portal, client)
    portal.goto(portal.base + CUENTA)

    section = portal.locator("#executive-agreements")
    expect(section).to_contain_text("Revisar fase 2")
    expect(
        section.get_by_role("button", name="+ Agregar acuerdo o pendiente")
    ).to_be_hidden()
    expect(section.get_by_role("button", name="Editar")).to_have_count(0)
    expect(section.get_by_role("button", name="Cerrar")).to_have_count(0)
    expect(
        section.get_by_label("Cambiar estado de Revisar fase 2")
    ).to_be_disabled()


def test_person_with_edit_changes_a_status_and_it_is_saved(
    portal, datos, enforced, client, records
):
    enforced("editora", caps=BOTH)
    browser_session(portal, client)
    portal.goto(portal.base + CUENTA)

    section = portal.locator("#executive-agreements")
    section.get_by_label("Cambiar estado de Revisar fase 2").select_option(
        "progress"
    )
    expect(section).to_contain_text("Estado actualizado.")
    assert (
        ExecutiveAgreement.objects.get(title="Revisar fase 2").status
        == "progress"
    )


def test_limited_scope_does_not_see_another_accounts_agreements(
    portal, datos, enforced, client, records
):
    enforced("ana", caps=BOTH, scope=AccessScope.limited(accounts=["ACME"]))
    browser_session(portal, client)
    # La cuenta ajena ya no abre; tampoco se puede leer por el endpoint.
    assert portal.request.get(portal.base + CUENTA).status == 404
    # Ni siquiera pidiendo el endpoint con la cuenta ajena en la direccion.
    body = portal.request.get(
        portal.base + "/ejecutiva/acuerdos/?account=Clinica+Sur"
    ).json()
    assert body["items"] == []
