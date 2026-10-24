"""Acciones AER/IXS: argumentos exactos, proveedores, permisos y CSRF."""

from unittest.mock import Mock

import pytest
from django.test import Client

from apps.access.scope import AccessScope
from apps.portal.api import project_actions as api
from apps.portal.api import project_client
from core.exceptions import SheetsError

pytestmark = pytest.mark.django_db
PROJECT = "AMK.008 | CR"
BASE = "/api/v1/screens/proyectos/AMK.008%20%7C%20CR/acciones/"
BODY = {
    "UID": "a1",
    "ID_Proyecto": "OTRO",
    "Accion": "Revisar",
    "uid": "a1",
    "campo": "estado",
    "valor": "Completado",
    "datos": {"accion": "Pendiente"},
}
EXPECTED = {
    "leer": (PROJECT,),
    "partes-leer": (PROJECT,),
    "guardar": ({**BODY, "ID_Proyecto": PROJECT},),
    "actualizar": (PROJECT, "a1", "estado", "Completado"),
    "eliminar": ("a1",),
    "limpiar-duplicados": (PROJECT,),
    "parte-guardar": (PROJECT, BODY["datos"]),
    "parte-actualizar": (PROJECT, "a1", "estado", "Completado"),
    "parte-eliminar": (PROJECT, "a1"),
}


def send(client, operation, service, body=None):
    if operation in {"leer", "partes-leer"}:
        path = "" if operation == "leer" else "partes/"
        return client.get(BASE + path, {"servicio": service})
    return client.post(
        BASE + operation + "/",
        {**(BODY if body is None else body), "servicio": service},
        content_type="application/json",
    )


@pytest.fixture
def calls(monkeypatch):
    regular = Mock(return_value={"ok": True, "acciones": {"filas": []}})
    monkeypatch.setattr(api, "run_operation", regular)
    ai = {}
    monkeypatch.setattr(api.ai_rpc, "build_context", lambda drive: "ai-context")
    for operation in [
        "partes-leer",
        "parte-guardar",
        "parte-actualizar",
        "parte-eliminar",
    ]:
        name = api.OPERATIONS[operation][0]
        count = len(EXPECTED[operation])
        ai[operation] = Mock(return_value={"ok": True, "filas": []})
        fn = ai[operation]
        monkeypatch.setitem(
            api.ai_rpc.FUNCTIONS,
            name,
            (count, lambda ctx, args, fn=fn: fn(ctx, args), False),
        )
    return regular, ai


@pytest.mark.parametrize("service", ["aer", "ixs"])
@pytest.mark.parametrize("operation", EXPECTED)
def test_exact_provider_arguments_and_response(
    client, calls, service, operation
):
    regular, ai = calls
    response = send(client, operation, service)
    assert response.status_code == 200
    if service == "aer" and operation.startswith("parte"):
        ai[operation].assert_called_once_with("ai-context", EXPECTED[operation])
        regular.assert_not_called()
        assert response.json()["data"] == {"ok": True, "filas": []}
    else:
        regular.assert_called_once_with(
            service, *api.OPERATIONS[operation], EXPECTED[operation]
        )
        assert response.json()["data"]["ok"] is True


@pytest.mark.parametrize("service", ["aer", "ixs"])
@pytest.mark.parametrize("operation", EXPECTED)
@pytest.mark.parametrize("grant", ["none", "limited", "full"])
def test_permissions_before_providers(
    client, calls, enforced, service, operation, grant
):
    capability = (
        "view_operations"
        if operation in {"leer", "partes-leer"}
        else "edit_operations"
    )
    enforced(
        "Ana",
        caps=frozenset() if grant == "none" else frozenset({capability}),
        scope=AccessScope.limited(accounts=["ACME"])
        if grant == "limited"
        else AccessScope.everything(),
    )
    response = send(client, operation, service)
    assert (
        response.status_code == 200
        if grant == "full"
        else response.status_code in {401, 403}
    )
    if grant != "full":
        calls[0].assert_not_called()
        for fn in calls[1].values():
            fn.assert_not_called()


@pytest.mark.parametrize(
    "operation", [key for key in EXPECTED if key not in {"leer", "partes-leer"}]
)
def test_mutations_require_csrf_and_object_body(client, calls, operation):
    strict = Client(enforce_csrf_checks=True)
    assert send(strict, operation, "ixs").status_code == 403
    assert (
        client.post(
            BASE + operation + "/", [], content_type="application/json"
        ).status_code
        == 400
    )
    calls[0].assert_not_called()


def test_invalid_service_and_operation_rejected(client, calls):
    assert send(client, "guardar", "otro").status_code == 400
    assert send(client, "nada", "aer").status_code == 400
    assert send(client, "leer", "").status_code == 400
    calls[0].assert_not_called()


def test_ai_parts_keep_safe_errors(client, calls):
    calls[1]["parte-guardar"].side_effect = SheetsError("Fuente no disponible")
    response = send(client, "parte-guardar", "aer")
    assert response.status_code == 200
    assert response.json()["data"]["ok"] is False


@pytest.mark.parametrize("service", ["aer", "ixs"])
@pytest.mark.parametrize("operation", EXPECTED)
def test_actual_service_tables_exist_and_are_invoked(
    monkeypatch, service, operation
):
    aer, ixs = api.OPERATIONS[operation]
    source = Mock(return_value={"ok": True})
    args = EXPECTED[operation]
    if service == "aer" and operation.startswith("parte"):
        count, _, drive = api.ai_functions.FUNCTIONS[aer]
        monkeypatch.setitem(
            api.ai_functions.FUNCTIONS,
            aer,
            (count, lambda ctx, values: source(ctx, values), drive),
        )
        monkeypatch.setattr(api.ai_rpc, "build_context", lambda flag: "ai")
        expected = ("ai", args)
    elif service == "aer":
        count, _ = project_client.aer_rpc.FUNCTIONS[aer]
        monkeypatch.setitem(
            project_client.aer_rpc.FUNCTIONS,
            aer,
            (count, lambda store, values: source(store, values)),
        )
        monkeypatch.setattr(
            project_client.aer_rpc, "build_store", lambda: "aer"
        )
        expected = ("aer", args)
    else:
        assert ixs in project_client.ixs_functions.SHEET_FUNCTIONS
        monkeypatch.setitem(
            project_client.ixs_functions.SHEET_FUNCTIONS,
            ixs,
            lambda store, *values: source(store, *values),
        )
        monkeypatch.setattr(
            project_client.ixs_rpc, "build_store_sheets", lambda: "ixs"
        )
        expected = ("ixs", *args)
    assert api.execute(service, operation, PROJECT, BODY) == {"ok": True}
    source.assert_called_once_with(*expected)
