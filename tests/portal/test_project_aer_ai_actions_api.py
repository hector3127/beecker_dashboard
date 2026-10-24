"""Acciones IA AER: servicios exactos, permisos originales y CSRF."""

from unittest.mock import Mock

import pytest
from django.test import Client

from apps.access import rpc_policy
from apps.access.scope import AccessScope
from apps.portal.api import project_aer_ai as api
from core.exceptions import SheetsError

pytestmark = pytest.mark.django_db
BASE = "/api/v1/screens/proyectos/AER.001%20%7C%20CR/ia-aer/"
BODY = {
    "ID_Proyecto": "OTRO",
    "contexto": {"k": {"horas": 80}},
    "datos": {"tema": "Comité", "contenido": "Editable", "ids": ["f1"]},
    "texto": "Texto exacto",
    "forzar": False,
}


@pytest.fixture
def provider(monkeypatch):
    context = object()
    builder = Mock(return_value=context)
    monkeypatch.setattr(api.ai_rpc, "build_context", builder)
    calls = {}
    for operation, name in api.OPERATIONS.items():
        count, _, drive = api.ai_functions.FUNCTIONS[name]
        calls[operation] = Mock(return_value={"ok": True, "texto": "Resultado"})
        monkeypatch.setitem(
            api.ai_functions.FUNCTIONS, name, (count, calls[operation], drive)
        )
    return context, builder, calls


def send(client, operation, body=BODY):
    return client.post(
        BASE + operation + "/", body, content_type="application/json"
    )


@pytest.mark.parametrize("operation", api.OPERATIONS)
def test_exact_original_service_arguments(client, provider, operation):
    response = send(client, operation)
    assert response.status_code == 200
    assert response.json()["data"] == {"ok": True, "texto": "Resultado"}
    if operation in {"config-guardar", "minuta-guardar"}:
        expected = ("AER.001 | CR", BODY["datos"])
    else:
        last = (
            BODY["forzar"]
            if operation == "analizar"
            else BODY["datos"]
            if operation in {"generar-resumen", "minuta-drive"}
            else BODY["texto"]
        )
        expected = ("AER.001 | CR", BODY["contexto"], last)
    provider[2][operation].assert_called_once_with(provider[0], expected)
    provider[1].assert_called_once_with(
        operation in {"generar-resumen", "minuta-drive"}
    )


@pytest.mark.parametrize("operation", api.OPERATIONS)
@pytest.mark.parametrize("grant", ["none", "wrong", "limited", "full"])
def test_original_permission_before_context(
    client, provider, enforced, operation, grant
):
    capability = (
        "manage_integrations"
        if operation == "config-guardar"
        else "edit_operations"
    )
    assert rpc_policy.POLICY[api.OPERATIONS[operation]] == (capability,)
    enforced(
        "Ana",
        caps=frozenset()
        if grant == "none"
        else frozenset({"view_operations"})
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
        provider[1].assert_not_called()


@pytest.mark.parametrize("operation", api.OPERATIONS)
def test_csrf_object_and_method_before_provider(client, provider, operation):
    assert send(Client(enforce_csrf_checks=True), operation).status_code == 403
    assert send(client, operation, []).status_code == 400
    assert client.get(BASE + operation + "/").status_code == 405
    provider[1].assert_not_called()


@pytest.mark.parametrize("operation", api.OPERATIONS)
def test_source_failure_keeps_public_contract(client, provider, operation):
    provider[2][operation].side_effect = SheetsError("Source secret")
    response = send(client, operation)
    assert response.status_code == 200
    assert response.json()["data"]["ok"] is False
    assert "Source secret" not in response.content.decode()


def test_unknown_action_is_not_routable(client, provider):
    assert send(client, "arbitraria").status_code == 404
    provider[1].assert_not_called()
