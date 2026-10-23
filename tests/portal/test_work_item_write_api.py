"""Work Items: mismos servicios globales, alcance total, edición y CSRF."""

import json
from unittest.mock import Mock

import pytest
from django.test import Client

from apps.access.scope import AccessScope
from apps.portal.api import project_detail as api
from core.exceptions import SheetsError

pytestmark = pytest.mark.django_db
BASE = "/api/v1/screens/work-items/101/"
SOURCES = [
    ("avance", "save_work_item_progress"),
    ("comentarios", "add_comment"),
]


@pytest.mark.parametrize("action,source", SOURCES)
@pytest.mark.parametrize(
    "result",
    [
        {"ok": True, "textoPublicado": "23/10/2026 - Texto"},
        {"ok": False, "error": "Sin conexión."},
    ],
)
def test_original_service_exact_values_and_response(
    client, monkeypatch, action, source, result
):
    load = Mock(return_value=result)
    monkeypatch.setattr(api.daily, source, load)
    payload = {
        "id": 202,
        "campo": "qa",
        "valor": False,
        "comentario": "  Texto á ' \n",
    }
    response = client.post(
        BASE + action + "/",
        json.dumps(payload),
        content_type="application/json",
    )
    assert response.status_code == 200
    assert response.json() == {"data": result, "meta": {}}
    load.assert_called_once_with(
        *(
            (101, "qa", False)
            if action == "avance"
            else (101, payload["comentario"])
        )
    )
    assert client.get(BASE + action + "/").status_code == 405
    assert client.delete(BASE + action + "/").status_code == 405


@pytest.mark.parametrize("value", [0, "0", 150, "invalid", None])
def test_field_validation_is_left_to_original_service(
    client, monkeypatch, value
):
    load = Mock(return_value={"ok": False, "error": "Campo inválido."})
    monkeypatch.setattr(api.daily, "save_work_item_progress", load)
    response = client.post(
        BASE + "avance/",
        json.dumps({"campo": "otro", "valor": value}),
        content_type="application/json",
    )
    assert response.status_code == 200
    load.assert_called_once_with(101, "otro", value)


@pytest.mark.parametrize("action,source", SOURCES)
@pytest.mark.parametrize(
    "grant", ["anonymous", "none", "read_only", "wrong", "limited"]
)
def test_access_denied_before_any_source(
    client, enforced, monkeypatch, action, source, grant
):
    load = Mock(side_effect=AssertionError("Source without edit access"))
    monkeypatch.setattr(api.daily, source, load)
    caps = {
        "none": set(),
        "read_only": {"view_operations"},
        "wrong": {"edit_agreements"},
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
        BASE + action + "/", {}, content_type="application/json"
    ).status_code in {401, 403}
    load.assert_not_called()


@pytest.mark.parametrize("action,source", SOURCES)
def test_full_edit_scope_and_public_failure(
    client, enforced, monkeypatch, action, source
):
    enforced("Ana", caps=frozenset({"edit_operations"}))
    load = Mock(return_value={"ok": True})
    monkeypatch.setattr(api.daily, source, load)
    assert (
        client.post(
            BASE + action + "/", {}, content_type="application/json"
        ).status_code
        == 200
    )
    load.side_effect = SheetsError("secret")
    response = client.post(
        BASE + action + "/", {}, content_type="application/json"
    )
    assert response.status_code == 502
    assert "secret" not in response.content.decode()


@pytest.mark.parametrize("action,source", SOURCES)
def test_csrf_even_with_access_disabled(monkeypatch, action, source):
    load = Mock(return_value={"ok": True})
    monkeypatch.setattr(api.daily, source, load)
    client = Client(enforce_csrf_checks=True)
    assert (
        client.post(
            BASE + action + "/", {}, content_type="application/json"
        ).status_code
        == 403
    )
    load.assert_not_called()
    token = client.get("/proyectos/AMK.008/").cookies["csrftoken"].value
    assert (
        client.post(
            BASE + action + "/",
            {},
            content_type="application/json",
            HTTP_X_CSRFTOKEN=token,
        ).status_code
        == 200
    )


@pytest.mark.parametrize("action,source", SOURCES)
@pytest.mark.parametrize("payload", [None, [], "text"])
def test_nonobject_body_never_reaches_source(
    client, monkeypatch, action, source, payload
):
    load = Mock(side_effect=AssertionError("Malformed JSON reached source"))
    monkeypatch.setattr(api.daily, source, load)
    response = client.post(
        BASE + action + "/",
        json.dumps(payload),
        content_type="application/json",
    )
    assert response.status_code == 400
    load.assert_not_called()
