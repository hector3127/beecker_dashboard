"""Planeación AER: firmas originales, permiso total, CSRF y errores seguros."""

from unittest.mock import Mock

import pytest
from django.test import Client

from apps.access.scope import AccessScope
from apps.portal.api import project_aer_planning as api
from core.exceptions import SheetsError

pytestmark = pytest.mark.django_db
PROJECT = "AER.001 | CR"
BASE = "/api/v1/screens/proyectos/AER.001%20%7C%20CR/planeacion-aer/"
BODY = {
    "ID_Proyecto": "OTRO",
    "UID": "p1",
    "uid": "p1",
    "Actividad": "Prueba",
    "estado": "Completado",
    "cierre": "2026-10-23",
    "cerrado": True,
    "uids": ["p1", "p2"],
    "items": [{"Actividad": "Prueba"}],
}
EXPECTED = {
    "guardar": ({**BODY, "ID_Proyecto": PROJECT},),
    "vacacion-guardar": ({**BODY, "ID_Proyecto": PROJECT},),
    "importar": (PROJECT, BODY["items"]),
    "estado": (PROJECT, "p1", "Completado", "2026-10-23"),
    "cerrar": (PROJECT, "p1", True),
    "eliminar": ("p1",),
    "eliminar-lote": (PROJECT, ["p1", "p2"]),
    "vacacion-eliminar": ("p1", PROJECT),
}


def send(client, operation):
    return client.post(
        BASE + operation + "/", BODY, content_type="application/json"
    )


@pytest.fixture
def provider(monkeypatch):
    store = object()
    monkeypatch.setattr(api.rpc, "build_store", lambda: store)
    calls = {}
    for operation, name in api.OPERATIONS.items():
        count, _ = api.rpc.FUNCTIONS[name]
        fn = Mock(return_value={"ok": True, "plan": {"filas": []}})
        calls[operation] = fn
        monkeypatch.setitem(api.rpc.FUNCTIONS, name, (count, fn))
    return store, calls


@pytest.mark.parametrize("operation", EXPECTED)
def test_exact_service_arguments(client, provider, operation):
    store, calls = provider
    response = send(client, operation)
    assert response.status_code == 200
    assert response.json()["data"] == {"ok": True, "plan": {"filas": []}}
    calls[operation].assert_called_once_with(store, EXPECTED[operation])


@pytest.mark.parametrize("operation", EXPECTED)
@pytest.mark.parametrize("grant", ["none", "read", "limited", "full"])
def test_permissions_before_provider(
    client, enforced, provider, operation, grant
):
    enforced(
        "Ana",
        caps=frozenset({"edit_operations"})
        if grant in {"limited", "full"}
        else frozenset({"view_operations"})
        if grant == "read"
        else frozenset(),
        scope=AccessScope.limited(accounts=["ACME"])
        if grant == "limited"
        else AccessScope.everything(),
    )
    response = send(client, operation)
    if grant == "full":
        assert response.status_code == 200
    else:
        assert response.status_code in {401, 403}
        for call in provider[1].values():
            call.assert_not_called()


@pytest.mark.parametrize("operation", EXPECTED)
def test_csrf_body_and_method(client, provider, operation):
    assert send(Client(enforce_csrf_checks=True), operation).status_code == 403
    assert (
        client.post(
            BASE + operation + "/", [], content_type="application/json"
        ).status_code
        == 400
    )
    assert client.get(BASE + operation + "/").status_code == 405
    for call in provider[1].values():
        call.assert_not_called()


def test_unknown_operation_and_source_errors(client, provider):
    assert send(client, "arbitraria").status_code == 400
    for call in provider[1].values():
        call.assert_not_called()
    provider[1]["guardar"].side_effect = SheetsError("Fuente no disponible")
    response = send(client, "guardar")
    assert response.status_code == 200
    assert response.json()["data"]["ok"] is False
