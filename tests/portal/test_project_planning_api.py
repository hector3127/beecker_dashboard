"""Planeación: transporte nuevo, mismas fuentes, permisos y CSRF."""

import json
from unittest.mock import Mock

import pytest
from django.test import Client

from apps.access.scope import AccessScope
from apps.portal.api import project_detail as api
from core.exceptions import SheetsError

pytestmark = pytest.mark.django_db
BASE = "/api/v1/screens/proyectos/CCO.001%20%7C%20CR/planeacion/"


@pytest.mark.parametrize("action", ["guardar", "eliminar"])
@pytest.mark.parametrize("kind", ["vacacion", "compromiso"])
@pytest.mark.parametrize("ok", [True, False])
def test_exact_payload_response_and_post_only(
    client, monkeypatch, action, kind, ok
):
    result = {"ok": ok, "vacaciones": [], "error": "Registro no encontrado."}
    source = Mock(return_value=result)
    name = (
        "save_plan_dashboard"
        if action == "guardar"
        else "delete_plan_dashboard"
    )
    monkeypatch.setattr(api, name, source)
    payload = {"idProyecto": "Other", "uid": "uid/'a", "fecha": "2026-10-23"}
    url = BASE + kind + "/" + action + "/"
    response = client.post(
        url, json.dumps(payload), content_type="application/json"
    )
    assert response.status_code == 200
    assert response.json() == {"data": result, "meta": {}}
    if action == "guardar":
        source.assert_called_once_with(
            kind, {**payload, "idProyecto": "CCO.001 | CR"}
        )
    else:
        source.assert_called_once_with(kind, "CCO.001 | CR", payload["uid"])
    assert client.get(url).status_code == 405
    assert client.delete(url).status_code == 405


@pytest.mark.parametrize("action", ["guardar", "eliminar"])
@pytest.mark.parametrize(
    "grant", ["anonymous", "read_only", "wrong", "limited"]
)
def test_edit_permission_precedes_source(
    client, enforced, monkeypatch, action, grant
):
    source = Mock(side_effect=AssertionError("Unauthorized source access"))
    name = (
        "save_plan_dashboard"
        if action == "guardar"
        else "delete_plan_dashboard"
    )
    monkeypatch.setattr(api, name, source)
    caps = (
        {"view_operations"}
        if grant == "read_only"
        else ({"edit_agreements"} if grant == "wrong" else {"edit_operations"})
    )
    enforced(
        "Ana",
        caps=frozenset(caps),
        scope=(
            AccessScope.limited(accounts=["ACME"])
            if grant == "limited"
            else AccessScope.everything()
        ),
    )
    if grant == "anonymous":
        client.logout()
    assert client.post(
        BASE + "vacacion/" + action + "/", {}, content_type="application/json"
    ).status_code in {401, 403}
    source.assert_not_called()


@pytest.mark.parametrize("action", ["guardar", "eliminar"])
def test_full_edit_scope_and_public_failure(
    client, enforced, monkeypatch, action
):
    enforced("Ana", caps=frozenset({"edit_operations"}))
    source = Mock(return_value={"ok": True})
    name = (
        "save_plan_dashboard"
        if action == "guardar"
        else "delete_plan_dashboard"
    )
    monkeypatch.setattr(api, name, source)
    url = BASE + "compromiso/" + action + "/"
    assert (
        client.post(url, {}, content_type="application/json").status_code == 200
    )
    source.side_effect = SheetsError("secret")
    response = client.post(url, {}, content_type="application/json")
    assert response.status_code == 502
    assert "secret" not in response.content.decode()


@pytest.mark.parametrize("action", ["guardar", "eliminar"])
def test_csrf_inherited_even_without_access_enforcement(monkeypatch, action):
    source = Mock(return_value={"ok": True})
    name = (
        "save_plan_dashboard"
        if action == "guardar"
        else "delete_plan_dashboard"
    )
    monkeypatch.setattr(api, name, source)
    client = Client(enforce_csrf_checks=True)
    url = BASE + "vacacion/" + action + "/"
    assert (
        client.post(url, {}, content_type="application/json").status_code == 403
    )
    source.assert_not_called()
    token = client.get("/proyectos/CCO.001/").cookies["csrftoken"].value
    assert (
        client.post(
            url, {}, content_type="application/json", HTTP_X_CSRFTOKEN=token
        ).status_code
        == 200
    )


@pytest.mark.parametrize("action", ["guardar", "eliminar"])
@pytest.mark.parametrize("payload", [None, [], "text"])
def test_nonobject_body_never_calls_source(
    client, monkeypatch, action, payload
):
    source = Mock(side_effect=AssertionError("Invalid JSON reached source"))
    name = (
        "save_plan_dashboard"
        if action == "guardar"
        else "delete_plan_dashboard"
    )
    monkeypatch.setattr(api, name, source)
    response = client.post(
        BASE + "vacacion/" + action + "/",
        json.dumps(payload),
        content_type="application/json",
    )
    assert response.status_code == 400
    source.assert_not_called()


def test_wrappers_keep_original_store_services_and_exact_identifiers(
    monkeypatch,
):
    store = object()
    monkeypatch.setattr(api, "build_store_sheets", lambda: store)
    read = Mock(return_value={"ok": True})
    save = Mock(return_value={"ok": True})
    delete = Mock(return_value={"ok": True})
    monkeypatch.setattr(api, "read_plan", read)
    monkeypatch.setattr(api, "save_plan", save)
    monkeypatch.setattr(api, "delete_plan", delete)
    payload = {"idProyecto": "CCO.001 | CR", "uid": "uid/'a"}
    assert api.planning_dashboard(payload["idProyecto"]) == read.return_value
    assert api.save_plan_dashboard("vacacion", payload) == save.return_value
    assert (
        api.delete_plan_dashboard(
            "compromiso", payload["idProyecto"], payload["uid"]
        )
        == delete.return_value
    )
    read.assert_called_once_with(store, payload["idProyecto"])
    save.assert_called_once_with(store, "vacacion", payload)
    delete.assert_called_once_with(
        store, "compromiso", payload["idProyecto"], payload["uid"]
    )
