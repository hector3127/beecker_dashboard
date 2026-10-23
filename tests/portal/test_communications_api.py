"""Centro de Comunicación por API v1: mismos servicios, permisos y CSRF."""

import json
from unittest.mock import Mock

import pytest
from django.test import Client

from apps.access.scope import AccessScope
from apps.portal.api import project_detail as api

pytestmark = pytest.mark.django_db
LIST = "/api/v1/screens/proyectos/comunicados/"
SAVE = "/api/v1/screens/proyectos/comunicados/guardar/"


@pytest.fixture
def source(monkeypatch):
    monkeypatch.setattr(api, "build_store_sheets", lambda: "store")
    mocks = {
        "list": Mock(return_value={"ok": True, "comunicados": [{"uid": "1"}]}),
        "save": Mock(return_value={"ok": True, "comunicados": []}),
    }
    monkeypatch.setattr(api.bee_com, "list_communications", mocks["list"])
    monkeypatch.setattr(api.bee_com, "save_communication", mocks["save"])
    return mocks


def post(client, body):
    return client.post(SAVE, json.dumps(body), content_type="application/json")


def test_list_and_save_call_the_same_services(client, source):
    listed = client.get(LIST)
    saved = post(client, {"titulo": "Aviso", "contenido": "Texto"})

    assert listed.json()["data"] == {"ok": True, "comunicados": [{"uid": "1"}]}
    assert saved.json() == {"data": {"ok": True, "comunicados": []}, "meta": {}}
    source["list"].assert_called_once_with("store")
    source["save"].assert_called_once_with(
        "store", {"titulo": "Aviso", "contenido": "Texto"}
    )


def test_service_errors_come_back_as_the_original_dict(
    client, monkeypatch, source
):
    from apps.daily.services.ixs_store import IxsError

    source["save"].side_effect = IxsError(
        "Escribe un título y contenido válidos."
    )

    response = post(client, {"titulo": ""})

    assert response.status_code == 200
    assert response.json()["data"]["ok"] is False
    assert "título" in response.json()["data"]["error"]


@pytest.mark.parametrize("grant", ["none", "read_only", "limited"])
def test_save_needs_edit_with_full_scope(client, enforced, source, grant):
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

    assert post(client, {"titulo": "x"}).status_code in {401, 403}
    source["save"].assert_not_called()


def test_list_needs_operations_and_csrf_is_enforced(client, enforced, source):
    enforced("Ana", caps=frozenset())
    assert client.get(LIST).status_code in {401, 403}
    source["list"].assert_not_called()
    strict = Client(enforce_csrf_checks=True)
    assert (
        strict.post(SAVE, "{}", content_type="application/json").status_code
        == 403
    )
    assert post(client, []).status_code in {400, 401, 403}
