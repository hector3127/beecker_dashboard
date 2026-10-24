"""Riesgos AER: servicios exactos, permiso/alcance y CSRF."""

from unittest.mock import Mock

import pytest
from django.test import Client

from apps.access.scope import AccessScope
from apps.portal.api import project_aer_risks as api
from core.exceptions import SheetsError

pytestmark = pytest.mark.django_db
PROJECT = "AER.001 | CR"
BASE = "/api/v1/screens/proyectos/AER.001%20%7C%20CR/riesgos-aer/"
BODY = {"UID": "r1", "uid": "r1", "ID_Proyecto": "OTRO", "Riesgo": "Entrega"}
EXPECTED = {
    "leer": (PROJECT,),
    "guardar": ({**BODY, "ID_Proyecto": PROJECT},),
    "eliminar": ("r1",),
    "limpiar-duplicados": (PROJECT,),
}


def send(client, operation):
    return (
        client.get(BASE)
        if operation == "leer"
        else client.post(
            BASE + operation + "/", BODY, content_type="application/json"
        )
    )


@pytest.fixture
def provider(monkeypatch):
    store = object()
    monkeypatch.setattr(api.rpc, "build_store", lambda: store)
    calls = {}
    for operation, name in api.OPERATIONS.items():
        count, _ = api.rpc.FUNCTIONS[name]
        calls[operation] = Mock(
            return_value={"ok": True, "riesgos": {"filas": []}}
        )
        monkeypatch.setitem(api.rpc.FUNCTIONS, name, (count, calls[operation]))
    return store, calls


@pytest.mark.parametrize("operation", EXPECTED)
def test_exact_provider_arguments(client, provider, operation):
    store, calls = provider
    response = send(client, operation)
    assert response.status_code == 200
    assert response.json()["data"] == {"ok": True, "riesgos": {"filas": []}}
    calls[operation].assert_called_once_with(store, EXPECTED[operation])


@pytest.mark.parametrize("operation", EXPECTED)
@pytest.mark.parametrize("grant", ["none", "wrong", "limited", "full"])
def test_permission_and_scope_before_provider(
    client, enforced, provider, operation, grant
):
    capability = "view_operations" if operation == "leer" else "edit_operations"
    enforced(
        "Ana",
        caps=frozenset()
        if grant == "none"
        else frozenset({"view_costs"})
        if grant == "wrong"
        else frozenset({capability}),
        scope=AccessScope.limited(accounts=["ACME"])
        if grant == "limited"
        else AccessScope.everything(),
    )
    response = send(client, operation)
    if grant == "full":
        assert response.status_code == 200
    else:
        assert response.status_code in {401, 403}
        for fn in provider[1].values():
            fn.assert_not_called()


@pytest.mark.parametrize(
    "operation", ["guardar", "eliminar", "limpiar-duplicados"]
)
def test_csrf_body_and_method(client, provider, operation):
    assert send(Client(enforce_csrf_checks=True), operation).status_code == 403
    assert (
        client.post(
            BASE + operation + "/", [], content_type="application/json"
        ).status_code
        == 400
    )
    assert client.get(BASE + operation + "/").status_code == 405
    for fn in provider[1].values():
        fn.assert_not_called()


def test_read_not_exposed_as_write_and_unknown_operation(client, provider):
    assert (
        client.post(
            BASE + "leer/", BODY, content_type="application/json"
        ).status_code
        == 400
    )
    assert send(client, "arbitraria").status_code == 400
    assert (
        client.post(BASE, BODY, content_type="application/json").status_code
        == 405
    )
    for fn in provider[1].values():
        fn.assert_not_called()


@pytest.mark.parametrize("operation", EXPECTED)
def test_service_failure_keeps_public_response(client, provider, operation):
    provider[1][operation].side_effect = SheetsError("Source secret")
    response = send(client, operation)
    assert response.status_code == 200
    assert response.json()["data"]["ok"] is False
    assert "Source secret" not in response.content.decode()
