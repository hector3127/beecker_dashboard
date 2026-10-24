"""Cliente por API v1: misma función de AER o IXS, permisos y CSRF."""

import json
from unittest.mock import Mock

import pytest
from django.test import Client

from apps.access.scope import AccessScope
from apps.portal.api import project_client as api

pytestmark = pytest.mark.django_db
PROJECT = "AMK.008"


def url(operation):
    return f"/api/v1/screens/proyectos/{PROJECT}/cliente/{operation}/"


def post(client, operation, body):
    return client.post(
        url(operation), json.dumps(body), content_type="application/json"
    )


@pytest.fixture
def run(monkeypatch):
    mock = Mock(return_value={"ok": True, "cliente": {"contactos": []}})
    monkeypatch.setattr(api, "run_operation", mock)
    return mock


@pytest.mark.parametrize(
    ("operation", "body", "aer", "ixs", "args"),
    [
        (
            "contacto-guardar",
            {"UID": "u", "ID_Proyecto": "Otro", "Nombre": "Ana"},
            "guardarContactoAER",
            "ixsGuardarContacto",
            ({"UID": "u", "ID_Proyecto": PROJECT, "Nombre": "Ana"},),
        ),
        (
            "contacto-eliminar",
            {"uid": "u"},
            "eliminarContactoAER",
            "ixsEliminarContacto",
            ("u", PROJECT),
        ),
        (
            "info-guardar",
            {"Sponsor": "Eva"},
            "guardarClienteInfoAER",
            "ixsGuardarClienteInfo",
            ({"Sponsor": "Eva", "ID_Proyecto": PROJECT},),
        ),
        (
            "gobierno-guardar",
            {"filas": [{"Reunion": "Semanal"}]},
            "guardarGobiernoClienteAER",
            "ixsGuardarGobiernoCliente",
            (PROJECT, [{"Reunion": "Semanal"}]),
        ),
        (
            "documento-guardar",
            {"Nombre": "Repo", "URL": "https://x"},
            "guardarDocumentoClienteAER",
            "ixsGuardarDocumentoCliente",
            ({"Nombre": "Repo", "URL": "https://x", "ID_Proyecto": PROJECT},),
        ),
        (
            "documento-eliminar",
            {"uid": "d"},
            "eliminarDocumentoClienteAER",
            "ixsEliminarDocumentoCliente",
            ("d", PROJECT),
        ),
    ],
)
@pytest.mark.parametrize("service", ["aer", "ixs"])
def test_each_operation_calls_the_function_of_its_service(
    client, run, operation, body, aer, ixs, args, service
):
    response = post(client, operation, {**body, "servicio": service})

    assert response.status_code == 200
    assert response.json()["data"] == {
        "ok": True,
        "cliente": {"contactos": []},
    }
    run.assert_called_once_with(service, aer, ixs, args)


def test_run_operation_uses_the_real_function_tables(monkeypatch):
    aer = Mock(return_value={"ok": True, "from": "aer"})
    ixs = Mock(return_value={"ok": True, "from": "ixs"})
    monkeypatch.setitem(
        api.aer_rpc.FUNCTIONS, "guardarContactoAER", (1, lambda s, a: aer(s, a))
    )
    monkeypatch.setitem(
        api.ixs_functions.SHEET_FUNCTIONS,
        "ixsGuardarContacto",
        lambda store, payload: ixs(store, payload),
    )
    monkeypatch.setattr(api.aer_rpc, "build_store", lambda: "aer-store")
    monkeypatch.setattr(api.ixs_rpc, "build_store_sheets", lambda: "ixs-store")

    assert (
        api.run_operation(
            "aer", "guardarContactoAER", "ixsGuardarContacto", ({"a": 1},)
        )["from"]
        == "aer"
    )
    assert (
        api.run_operation(
            "ixs", "guardarContactoAER", "ixsGuardarContacto", ({"a": 1},)
        )["from"]
        == "ixs"
    )
    aer.assert_called_once_with("aer-store", ({"a": 1},))
    ixs.assert_called_once_with("ixs-store", {"a": 1})


@pytest.mark.parametrize(
    ("operation", "service"),
    [("nada", "aer"), ("contacto-guardar", ""), ("contacto-guardar", "otro")],
)
def test_unknown_operation_or_service_is_rejected(
    client, run, operation, service
):
    response = post(client, operation, {"servicio": service})

    assert response.status_code == 400
    run.assert_not_called()


@pytest.mark.parametrize("grant", ["none", "read_only", "limited"])
def test_needs_edit_with_full_scope(client, enforced, run, grant):
    caps = {"none": set(), "read_only": {"view_operations"}}.get(
        grant, {"edit_operations"}
    )
    enforced(
        "Ana",
        caps=frozenset(caps),
        scope=AccessScope.limited(accounts=["ACME"])
        if grant == "limited"
        else AccessScope.everything(),
    )

    assert post(
        client, "contacto-guardar", {"servicio": "aer"}
    ).status_code in {401, 403}
    run.assert_not_called()


def test_csrf_and_nonobject_bodies(client, run):
    strict = Client(enforce_csrf_checks=True)
    assert (
        strict.post(
            url("contacto-guardar"), "{}", content_type="application/json"
        ).status_code
        == 403
    )
    assert post(client, "contacto-guardar", []).status_code == 400
    run.assert_not_called()
