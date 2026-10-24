"""Fuentes IA AER: firmas originales, permisos y lectura sin generación."""

import json
from unittest.mock import Mock

import pytest

from apps.access.scope import AccessScope
from apps.portal.api import project_aer_ai as api
from core.exceptions import SheetsError

pytestmark = pytest.mark.django_db
BASE = "/api/v1/screens/proyectos/AER.001%20%7C%20CR/ia-aer/"
CONTEXT = {"id": "context-id", "k": {"horas": 80}, "p": [{"a": "Tarea"}]}


@pytest.fixture
def provider(monkeypatch):
    context = object()
    builder = Mock(return_value=context)
    monkeypatch.setattr(api.ai_rpc, "build_context", builder)
    actions = {}
    for source, name in api.SOURCES.items():
        count, _, drive = api.ai_functions.FUNCTIONS[name]
        actions[source] = Mock(return_value={"ok": True, "source": source})
        monkeypatch.setitem(
            api.ai_functions.FUNCTIONS, name, (count, actions[source], drive)
        )
    return context, builder, actions


def get(client, source):
    return client.get(BASE + source + "/", {"contexto": json.dumps(CONTEXT)})


@pytest.mark.parametrize("source", api.SOURCES)
def test_exact_source_arguments(client, provider, source):
    response = get(client, source)
    assert response.status_code == 200
    assert response.json()["data"] == {"ok": True, "source": source}
    expected = (
        ("AER.001 | CR", CONTEXT) if source == "analisis" else ("AER.001 | CR",)
    )
    provider[2][source].assert_called_once_with(provider[0], expected)
    provider[1].assert_called_once_with(source == "archivos")


@pytest.mark.parametrize("source", api.SOURCES)
@pytest.mark.parametrize("grant", ["none", "wrong", "limited", "full"])
def test_authorization_before_context(
    client, enforced, provider, source, grant
):
    capability = (
        "manage_integrations" if source == "config" else "view_operations"
    )
    enforced(
        "Ana",
        caps=frozenset()
        if grant == "none"
        else frozenset({"edit_operations"})
        if grant == "wrong"
        else frozenset({capability}),
        scope=AccessScope.limited(accounts=["ACME"])
        if grant == "limited"
        else AccessScope.everything(),
    )
    response = get(client, source)
    if grant == "full":
        assert response.status_code == 200
    else:
        assert response.status_code in {401, 403}
        provider[1].assert_not_called()


@pytest.mark.parametrize("value", ["bad", "[]", "null"])
def test_invalid_comparison_context(client, provider, value):
    assert (
        client.get(BASE + "analisis/", {"contexto": value}).status_code == 400
    )
    provider[1].assert_not_called()


@pytest.mark.parametrize("source", api.SOURCES)
def test_read_only(client, provider, source):
    assert (
        client.post(
            BASE + source + "/", {}, content_type="application/json"
        ).status_code
        == 405
    )
    provider[1].assert_not_called()


@pytest.mark.parametrize("source", api.SOURCES)
def test_source_failure_keeps_public_response(client, provider, source):
    provider[2][source].side_effect = SheetsError("Source secret")
    response = get(client, source)
    assert response.status_code == 200
    assert response.json()["data"]["ok"] is False
    assert "Source secret" not in response.content.decode()
