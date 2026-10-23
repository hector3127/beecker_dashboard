"""Hitos del proyecto por API v1: mismo servicio, permiso de edición y CSRF."""

import json
from unittest.mock import Mock

import pytest
from django.test import Client

from apps.access.scope import AccessScope
from apps.portal.api import project_detail as api

pytestmark = pytest.mark.django_db
BASE = "/api/v1/screens/proyectos/"
PROJECT = "CCO.001%20%7C%20CR"
ACTIONS = {
    "guardar": ("save_milestone_batch", {"hitos": [{"tipo": "Go live"}]}),
    "editar": (
        "edit_milestone_entry",
        {
            "tipo": "Go live",
            "indice": 1,
            "fechaISO": "2026-01-02",
            "observacion": "n",
        },
    ),
    "eliminar": ("delete_milestone_entry", {"tipo": "Go live", "indice": 1}),
}
CALLS = {
    "guardar": ("CCO.001 | CR", [{"tipo": "Go live"}]),
    "editar": ("CCO.001 | CR", "Go live", 1, "2026-01-02", "n"),
    "eliminar": ("CCO.001 | CR", "Go live", 1),
}


def url(action):
    return f"{BASE}{PROJECT}/hitos/{action}/"


def test_types_are_read_with_view_access(client, enforced, monkeypatch):
    source = Mock(return_value=["🚀 Go live"])
    monkeypatch.setattr(api.milestones, "get_milestone_types", source)
    enforced("Ana")
    response = client.get(f"{BASE}hitos/tipos/")
    assert response.json() == {"data": {"tipos": ["🚀 Go live"]}, "meta": {}}


@pytest.mark.parametrize("action", ACTIONS)
def test_same_service_and_response(client, monkeypatch, action):
    name, body = ACTIONS[action]
    result = {"ok": True, "hitos": []}
    source = Mock(return_value=result)
    monkeypatch.setattr(api.milestones, name, source)
    response = client.post(
        url(action), json.dumps(body), content_type="application/json"
    )
    assert response.json() == {"data": result, "meta": {}}
    source.assert_called_once_with(*CALLS[action])
    assert client.get(url(action)).status_code == 405


@pytest.mark.parametrize("action", ACTIONS)
@pytest.mark.parametrize("grant", ["none", "read_only", "limited"])
def test_write_permission_before_source(
    client, enforced, monkeypatch, action, grant
):
    source = Mock(
        side_effect=AssertionError("Source called without edit access")
    )
    monkeypatch.setattr(api.milestones, ACTIONS[action][0], source)
    caps = {"read_only": {"view_operations"}, "none": set()}.get(
        grant, {"edit_operations"}
    )
    enforced(
        "Ana",
        caps=frozenset(caps),
        scope=AccessScope.limited(accounts=["ACME"])
        if grant == "limited"
        else AccessScope.everything(),
    )
    assert client.post(
        url(action), {}, content_type="application/json"
    ).status_code in {
        401,
        403,
    }
    source.assert_not_called()


def test_csrf_even_when_access_is_disabled(monkeypatch):
    source = Mock(return_value={"ok": True, "hitos": []})
    monkeypatch.setattr(api.milestones, "delete_milestone_entry", source)
    client = Client(enforce_csrf_checks=True)
    assert (
        client.post(
            url("eliminar"), {}, content_type="application/json"
        ).status_code
        == 403
    )
    source.assert_not_called()


def test_nonobject_body_is_rejected(client, monkeypatch):
    source = Mock(side_effect=AssertionError("Invalid request reached source"))
    monkeypatch.setattr(api.milestones, "save_milestone_batch", source)
    response = client.post(
        url("guardar"), "[]", content_type="application/json"
    )
    assert response.status_code == 400
    source.assert_not_called()
