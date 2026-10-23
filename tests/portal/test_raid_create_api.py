"""Alta RAID por API v1: mismos servicios, permisos por operación y CSRF."""

import json
from unittest.mock import Mock

import pytest
from django.test import Client

from apps.access.scope import AccessScope
from apps.portal.api import project_detail as api

pytestmark = pytest.mark.django_db
BASE = "/api/v1/screens/proyectos/"
PROJECT = "AMK.008"


def post(client, path, body):
    return client.post(
        BASE + path, json.dumps(body), content_type="application/json"
    )


@pytest.fixture
def services(monkeypatch):
    mocks = {
        "fields": Mock(return_value={"ok": True, "campos": {}}),
        "options": Mock(return_value={"ok": True, "iteraciones": ["AMK"]}),
        "create": Mock(return_value={"ok": True, "id": 9}),
        "read": Mock(return_value={"ok": True, "prompt": "p"}),
        "save": Mock(return_value={"ok": True, "prompt": "q"}),
        "suggest": Mock(return_value={"ok": True, "sugerencia": {}}),
    }
    monkeypatch.setattr(api.ixs_rpc, "raid_field_types", mocks["fields"])
    monkeypatch.setattr(api.ixs_rpc, "raid_creation_options", mocks["options"])
    monkeypatch.setattr(api.ixs_rpc, "create_raid_record", mocks["create"])
    monkeypatch.setattr(api.ai_rpc, "build_claude", lambda: "claude")
    monkeypatch.setattr(api.claude_assist, "read_raid_prompt", mocks["read"])
    monkeypatch.setattr(api.claude_assist, "save_raid_prompt", mocks["save"])
    monkeypatch.setattr(api.claude_assist, "suggest_raid", mocks["suggest"])
    return mocks


def test_reads_call_the_same_services(client, services):
    fields = client.get(f"{BASE}{PROJECT}/raid/campos/?tipo=Issue")
    options = client.get(f"{BASE}{PROJECT}/raid/alta-opciones/?tipo=Risk")
    prompt = client.get(f"{BASE}raid/prompt/?tipo=Opportunity")

    assert fields.json()["data"] == {"ok": True, "campos": {}}
    assert options.json()["data"]["iteraciones"] == ["AMK"]
    assert prompt.json()["data"]["prompt"] == "p"
    services["fields"].assert_called_once_with(PROJECT, "Issue")
    services["options"].assert_called_once_with(PROJECT, "Risk")
    services["read"].assert_called_once_with("claude", "Opportunity")


def test_create_suggest_and_prompt_pass_the_body_and_route_project(
    client, services
):
    created = post(
        client,
        f"{PROJECT}/raid/crear/",
        {"tipo": "Risk", "datos": {"titulo": "x"}, "idProyecto": "Other"},
    )
    suggested = post(
        client,
        "raid/sugerir/",
        {"tipo": "Issue", "descripcion": "El servidor se cae seguido"},
    )
    saved = post(client, "raid/prompt/", {"tipo": "Issue", "prompt": ""})

    assert created.json() == {"data": {"ok": True, "id": 9}, "meta": {}}
    services["create"].assert_called_once_with(PROJECT, "Risk", {"titulo": "x"})
    assert suggested.status_code == 200
    services["suggest"].assert_called_once_with(
        "claude", "Issue", "El servidor se cae seguido"
    )
    assert saved.status_code == 200
    services["save"].assert_called_once_with("claude", "Issue", "")


@pytest.mark.parametrize(
    ("path", "grant"),
    [
        (f"{PROJECT}/raid/crear/", "read_only"),
        (f"{PROJECT}/raid/crear/", "limited"),
        ("raid/sugerir/", "read_only"),
        ("raid/prompt/", "read_only"),
        ("raid/prompt/", "edit_only"),
    ],
)
def test_writes_need_their_own_capability_before_the_service(
    client, enforced, services, path, grant
):
    caps = {
        "read_only": {"view_operations"},
        "limited": {"edit_operations"},
        "edit_only": {"view_operations", "edit_operations"},
    }[grant]
    enforced(
        "Ana",
        caps=frozenset(caps),
        scope=AccessScope.limited(accounts=["ACME"])
        if grant == "limited"
        else AccessScope.everything(),
    )

    assert post(client, path, {"tipo": "Risk"}).status_code in {401, 403}
    for name in ("create", "suggest", "save"):
        services[name].assert_not_called()


def test_prompt_save_with_integrations_and_read_with_operations(
    client, enforced, services
):
    enforced("Ana", caps=frozenset({"view_operations", "manage_integrations"}))

    assert client.get(f"{BASE}raid/prompt/?tipo=Risk").status_code == 200
    assert post(client, "raid/prompt/", {"tipo": "Risk"}).status_code == 200


def test_csrf_and_nonobject_bodies(client, services):
    strict = Client(enforce_csrf_checks=True)
    assert (
        strict.post(
            BASE + f"{PROJECT}/raid/crear/",
            "{}",
            content_type="application/json",
        ).status_code
        == 403
    )
    assert post(client, f"{PROJECT}/raid/crear/", []).status_code == 400
    assert post(client, "raid/prompt/", "x").status_code == 400
    services["create"].assert_not_called()
