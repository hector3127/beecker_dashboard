"""Guardado de recursos: servicio previo, permiso de edición, alcance y CSRF."""

import json
from unittest.mock import Mock

import pytest
from django.test import Client

from apps.access.scope import AccessScope
from apps.portal.api import project_detail as api
from core.exceptions import SheetsError

pytestmark = pytest.mark.django_db
URL = "/api/v1/screens/proyectos/CCO.001%20%7C%20CR/recursos/guardar/"


@pytest.mark.parametrize(
    "result",
    [
        {"ok": True, "proyectoId": "CCO.001 | CR", "filas": []},
        {"ok": False, "error": "Escribe el rol del recurso."},
    ],
)
def test_same_save_payload_and_response(client, monkeypatch, result):
    source = Mock(return_value=result)
    monkeypatch.setattr(api, "save_resource_dashboard", source)
    payload = {
        "idProyecto": "Other",
        "nombre": "Ana Pérez",
        "rol": "QA",
        "horasEstimadas": "0",
        "activo": False,
    }
    response = client.post(
        URL, json.dumps(payload), content_type="application/json"
    )
    assert response.status_code == 200
    assert response.json() == {"data": result, "meta": {}}
    source.assert_called_once_with({**payload, "idProyecto": "CCO.001 | CR"})
    assert client.get(URL).status_code == 405
    assert (
        client.put(URL, payload, content_type="application/json").status_code
        == 405
    )


@pytest.mark.parametrize(
    "grant", ["anonymous", "none", "read_only", "wrong", "limited"]
)
def test_write_permission_before_source(client, enforced, monkeypatch, grant):
    source = Mock(
        side_effect=AssertionError("Source called without edit access")
    )
    monkeypatch.setattr(api, "save_resource_dashboard", source)
    caps = {
        "read_only": {"view_operations"},
        "wrong": {"edit_agreements"},
        "none": set(),
    }.get(grant, {"edit_operations"})
    enforced(
        "Ana",
        caps=frozenset(caps),
        scope=AccessScope.limited(accounts=["ACME"])
        if grant == "limited"
        else AccessScope.everything(),
    )
    if grant == "anonymous":
        client.logout()
    assert client.post(
        URL, {}, content_type="application/json"
    ).status_code in {401, 403}
    source.assert_not_called()


def test_full_edit_scope_and_public_source_error(client, enforced, monkeypatch):
    enforced("Ana", caps=frozenset({"edit_operations"}))
    source = Mock(return_value={"ok": True})
    monkeypatch.setattr(api, "save_resource_dashboard", source)
    assert (
        client.post(URL, {}, content_type="application/json").status_code == 200
    )
    source.side_effect = SheetsError("secret")
    response = client.post(URL, {}, content_type="application/json")
    assert response.status_code == 502
    assert "secret" not in response.content.decode()


def test_csrf_even_when_access_is_disabled(monkeypatch):
    source = Mock(return_value={"ok": True})
    monkeypatch.setattr(api, "save_resource_dashboard", source)
    client = Client(enforce_csrf_checks=True)
    assert (
        client.post(URL, {}, content_type="application/json").status_code == 403
    )
    source.assert_not_called()
    page = client.get("/proyectos/CCO.001%20%7C%20CR/")
    token = page.cookies["csrftoken"].value
    assert (
        client.post(
            URL, {}, content_type="application/json", HTTP_X_CSRFTOKEN=token
        ).status_code
        == 200
    )
    source.assert_called_once_with({"idProyecto": "CCO.001 | CR"})


@pytest.mark.parametrize("payload", [[], None, "text"])
def test_nonobject_body_is_rejected(client, monkeypatch, payload):
    source = Mock(side_effect=AssertionError("Invalid request reached source"))
    monkeypatch.setattr(api, "save_resource_dashboard", source)
    response = client.post(
        URL, json.dumps(payload), content_type="application/json"
    )
    assert response.status_code == 400
    source.assert_not_called()


def test_save_uses_original_store_and_service(monkeypatch):
    store = object()
    monkeypatch.setattr(api, "build_store_sheets", lambda: store)
    source = Mock(return_value={"ok": True, "filas": []})
    monkeypatch.setattr(api, "save_resource", source)
    payload = {
        "idProyecto": "CCO.001 | CR",
        "horasEstimadas": "12.25",
        "activo": False,
    }
    assert api.save_resource_dashboard(payload) == source.return_value
    source.assert_called_once_with(store, payload)
