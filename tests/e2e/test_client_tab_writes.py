"""Pestaña Cliente (AER e IXS): guardado, borrado y avisos por API v1."""

import copy
from pathlib import Path

import pytest
from playwright.sync_api import expect

from tests.e2e.test_aer_executive import fixed_day as fixed_day
from tests.e2e.test_client_tab import (
    CLIENT,
    CONTACTS,
    edit_contact,
    edit_document,
    governance,
    info,
    new_contact,
    new_document,
    open_tab,
)
from tests.e2e.test_client_tab import (
    board as board,
)
from tests.e2e.test_client_tab import (
    family as family,
)
from tests.e2e.test_ixs_client_actions_transport import (
    client_actions as client_actions,
)
from tests.e2e.test_ixs_executive import ixs as ixs
from tests.e2e.test_project_detail_entry import project_detail as project_detail

pytestmark = pytest.mark.django_db(transaction=True)
PROJECT = {"ixs": "AMK.008", "aer": "AER.001"}
NAMES = {
    "contacto-guardar": ("guardarContactoAER", "ixsGuardarContacto"),
    "contacto-eliminar": ("eliminarContactoAER", "ixsEliminarContacto"),
    "info-guardar": ("guardarClienteInfoAER", "ixsGuardarClienteInfo"),
    "gobierno-guardar": (
        "guardarGobiernoClienteAER",
        "ixsGuardarGobiernoCliente",
    ),
    "documento-guardar": (
        "guardarDocumentoClienteAER",
        "ixsGuardarDocumentoCliente",
    ),
    "documento-eliminar": (
        "eliminarDocumentoClienteAER",
        "ixsEliminarDocumentoCliente",
    ),
}


@pytest.fixture
def writes(board, monkeypatch):
    """Servicios de escritura simulados; guarda lo que reciben."""
    from apps.portal.api import project_client

    calls = []
    answers = {}

    def run(service, aer_name, ixs_name, args):
        calls.append((service, aer_name, ixs_name, copy.deepcopy(args)))
        found = [k for k, v in NAMES.items() if v == (aer_name, ixs_name)]
        return copy.deepcopy(answers.get(found[0], {"ok": True}))

    monkeypatch.setattr(project_client, "run_operation", run)
    return calls, answers


def test_save_contact_goes_through_the_api_with_the_right_service(
    portal, board, writes
):
    family, _ = board
    calls, answers = writes
    requests = []
    portal.on("request", lambda request: requests.append(request))
    answers["contacto-guardar"] = {
        "ok": True,
        "cliente": {"contactos": [*CONTACTS, {"uid": "n1", "nombre": "Nuevo"}]},
    }
    open_tab(portal, family)
    new_contact(portal)
    portal.locator("#acc-nom").fill("Nuevo")
    portal.locator("#acc-req").check()
    portal.locator("#acc-nivel").select_option("Bajo")
    portal.get_by_role("button", name="Guardar contacto").click()

    expect(portal.locator("#aer-modal-back")).to_have_count(0)
    expect(portal.locator(".aer-client-directory")).to_contain_text("Nuevo")
    expect(portal.locator(".aer-toast")).to_contain_text("Contacto guardado")
    service, aer, ixs, args = calls[-1]
    assert (service, aer, ixs) == (family, *NAMES["contacto-guardar"])
    payload = args[0]
    assert payload["ID_Proyecto"] == PROJECT[family]
    assert payload["Nombre"] == "Nuevo" and payload["Requerimientos"] is True
    assert payload["Nivel_Decision"] == "Bajo" and payload["Aprueba"] is False
    assert not any("/api/rpc/" in r.url for r in requests)
    token = next(
        c["value"] for c in portal.context.cookies() if c["name"] == "csrftoken"
    )
    posts = [r for r in requests if r.method == "POST" and "/cliente/" in r.url]
    assert posts and all(r.headers.get("x-csrftoken") == token for r in posts)


def test_info_governance_and_document_updates_refresh_the_tab(
    portal, board, writes
):
    family, _ = board
    calls, answers = writes
    open_tab(portal, family)

    answers["info-guardar"] = {"ok": True, "uid": "i9"}
    info(portal)
    portal.locator("#aci-sponsor").fill("Marta Ruiz")
    portal.get_by_role("button", name="Guardar información").click()
    expect(portal.locator(".aer-client-side-table")).to_contain_text(
        "Marta Ruiz"
    )
    assert calls[-1][3][0]["Sponsor"] == "Marta Ruiz"

    answers["gobierno-guardar"] = {
        "ok": True,
        "gobierno": [
            {
                "reunion": "Comité",
                "frecuencia": "Mensual",
                "participantes": "Todos",
                "canal": "Teams",
            }
        ],
    }
    governance(portal)
    portal.get_by_role("button", name="＋ Agregar reunión").click()
    portal.locator('.aer-gov-edit-row [data-gov="reunion"]').last.fill("Comité")
    portal.get_by_role("button", name="Guardar cambios").click()
    expect(portal.locator(".aer-client-government")).to_contain_text("Comité")
    project, rows = calls[-1][3]
    assert project == PROJECT[family]
    assert [r["Reunion"] for r in rows] == ["Seguimiento", "Comité"]

    answers["documento-guardar"] = {
        "ok": True,
        "documentos": [
            {
                "uid": "d9",
                "nombre": "Guía",
                "tipo": "Documento",
                "url": "https://g",
                "accion": "Abrir",
            }
        ],
    }
    new_document(portal)
    portal.locator("#acd-nom").fill("Guía")
    portal.locator("#acd-tipo").select_option("Documento")
    portal.get_by_role("button", name="Guardar link").click()
    expect(portal.locator(".aer-client-docs-table")).to_contain_text("Guía")
    assert calls[-1][3][0]["Tipo"] == "Documento"


def test_deleting_asks_first_and_updates_the_list(portal, board, writes):
    family, _ = board
    calls, answers = writes
    answers["contacto-eliminar"] = {
        "ok": True,
        "cliente": {"contactos": CONTACTS[1:]},
    }
    answers["documento-eliminar"] = {
        "ok": True,
        "documentos": CLIENT["documentos"][1:],
    }
    open_tab(portal, family)
    edit_contact(portal)
    portal.once("dialog", lambda d: d.dismiss())
    portal.get_by_role("button", name="Eliminar").click()
    assert calls == []
    portal.once("dialog", lambda d: d.accept())
    portal.get_by_role("button", name="Eliminar").click()
    expect(portal.locator(".aer-client-directory")).not_to_contain_text(
        "Ana Pérez"
    )
    assert calls[-1][3] == ("c1", PROJECT[family])
    edit_document(portal)
    portal.once("dialog", lambda d: d.accept())
    portal.get_by_role("button", name="Eliminar").click()
    expect(portal.locator(".aer-client-docs-table")).not_to_contain_text(
        "Repositorio"
    )
    expect(portal.locator(".aer-toast").last).to_contain_text("Link eliminado")


def test_service_errors_keep_the_window_and_buttons_work_again(
    portal, board, writes
):
    family, _ = board
    _, answers = writes
    answers["contacto-guardar"] = {"ok": False, "error": "Nombre obligatorio."}
    open_tab(portal, family)
    new_contact(portal)
    portal.get_by_role("button", name="Guardar contacto").click()
    expect(portal.locator(".aer-toast.error")).to_contain_text(
        "Nombre obligatorio."
    )
    expect(portal.locator("#aer-modal-back")).to_be_visible()
    expect(
        portal.get_by_role("button", name="Guardar contacto")
    ).to_be_enabled()
    expect(
        portal.locator("#aer-modal-back .aer-btn:not(.primary)").first
    ).to_be_enabled()


def test_links_open_with_https(portal, board, writes):
    family, _ = board
    open_tab(portal, family)
    portal.evaluate(
        "window.__opened=[];"
        "window.open=(u,t,f)=>{window.__opened.push([u,t,f])};0"
    )
    links = portal.locator(".aer-client-docs-table .aer-client-doc-link")
    links.nth(0).click()
    links.nth(1).click()
    assert portal.evaluate("window.__opened") == [
        ["https://drive.google.com/r", "_blank", "noopener"],
        ["https://drive.google.com/mco", "_blank", "noopener"],
    ]


def test_export_downloads_the_contacts_csv(portal, board, writes):
    family, _ = board
    open_tab(portal, family)
    with portal.expect_download() as download:
        portal.get_by_role("button", name="⇩ Exportar").click()
    text = Path(download.value.path()).read_text(encoding="utf-8")
    assert (
        download.value.suggested_filename
        == f"{PROJECT[family]}_contactos_cliente.csv"
    )
    assert text.startswith('﻿"Nombre","Cargo"')
    assert '"Ana Pérez","Dirección <b>TI</b>","Sponsor"' in text


def test_text_is_never_html(portal, board):
    family, _ = board
    open_tab(portal, family)
    expect(portal.locator(".aer-client-directory")).to_contain_text(
        "Dirección <b>TI</b>"
    )
    expect(portal.locator(".aer-client-directory b")).to_have_count(0)
