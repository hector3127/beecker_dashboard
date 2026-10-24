"""Evaluaciones AER: argumentos originales, permisos y CSRF antes de fuentes."""

from unittest.mock import Mock

import pytest
from django.test import Client

from apps.access.scope import AccessScope
from apps.portal.api import project_aer_resources as api
from core.exceptions import SheetsError

pytestmark = pytest.mark.django_db
PROJECT = "AER.001 | CR"
BASE = "/api/v1/screens/proyectos/AER.001%20%7C%20CR/evaluaciones-aer/"
BODY = {"UID": "e1", "uid": "e1", "ID_Proyecto": "OTRO", "Calidad": "80"}


@pytest.fixture
def provider(monkeypatch):
    store = object()
    monkeypatch.setattr(api.rpc, "build_store", lambda: store)
    calls = {}
    for op, name in api.OPERATIONS.items():
        count, _ = api.rpc.FUNCTIONS[name]
        calls[op] = Mock(
            return_value={"ok": True, "evaluaciones": {"filas": []}}
        )
        monkeypatch.setitem(api.rpc.FUNCTIONS, name, (count, calls[op]))
    return store, calls


def send(client, operation, body=BODY):
    return client.post(
        BASE + operation + "/", body, content_type="application/json"
    )


@pytest.mark.parametrize("operation", api.OPERATIONS)
def test_exact_provider_arguments(client, provider, operation):
    response = send(client, operation)
    assert response.status_code == 200
    assert response.json()["data"] == {
        "ok": True,
        "evaluaciones": {"filas": []},
    }
    expected = (
        ({**BODY, "ID_Proyecto": PROJECT},)
        if operation == "guardar"
        else ("e1", PROJECT)
    )
    provider[1][operation].assert_called_once_with(provider[0], expected)


@pytest.mark.parametrize("operation", api.OPERATIONS)
@pytest.mark.parametrize("grant", ["none", "wrong", "limited", "full"])
def test_authorization_before_provider(
    client, enforced, provider, operation, grant
):
    enforced(
        "Ana",
        caps=frozenset()
        if grant == "none"
        else frozenset({"view_operations"})
        if grant == "wrong"
        else frozenset({"edit_operations"}),
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


@pytest.mark.parametrize("operation", api.OPERATIONS)
def test_csrf_body_and_method(client, provider, operation):
    assert send(Client(enforce_csrf_checks=True), operation).status_code == 403
    assert send(client, operation, []).status_code == 400
    assert client.get(BASE + operation + "/").status_code == 405
    for fn in provider[1].values():
        fn.assert_not_called()


def test_unknown_operation_rejected(client, provider):
    assert send(client, "arbitraria").status_code == 400
    for fn in provider[1].values():
        fn.assert_not_called()


@pytest.mark.parametrize("operation", api.OPERATIONS)
def test_source_failure_preserves_public_response(client, provider, operation):
    provider[1][operation].side_effect = SheetsError("Source secret")
    response = send(client, operation)
    assert response.status_code == 200
    assert response.json()["data"]["ok"] is False
    assert "Source secret" not in response.content.decode()
