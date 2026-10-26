"""Alta manual: mismo servicio, ID de ruta y protección de escritura."""

from unittest.mock import Mock

import pytest
from django.test import Client

from apps.access.scope import AccessScope
from apps.portal.api import project_detail as api
from core.exceptions import SheetsError

pytestmark = pytest.mark.django_db
URL = "/api/v1/screens/proyectos/CCO.001%20%7C%20CR/riesgos-manuales/"
BODY = {
    "idProyecto": "OTRO",
    "descripcion": " Riesgo ",
    "impacto": "Medio",
    "probabilidad": "Media",
    "responsable": " Ana ",
}


@pytest.fixture
def source(monkeypatch):
    load = Mock(return_value={"ok": True})
    monkeypatch.setattr(api.milestones, "add_risk", load)
    return load


@pytest.mark.parametrize("payload", [BODY, {}, {"impacto": "Inválido"}])
def test_original_service_arguments_and_route_id(client, source, payload):
    response = client.post(URL, payload, content_type="application/json")
    assert response.status_code == 200
    assert response.json() == {"data": {"ok": True}, "meta": {}}
    source.assert_called_once_with(
        "CCO.001 | CR",
        *(
            payload.get(key, "")
            for key in ("descripcion", "impacto", "probabilidad", "responsable")
        ),
    )


@pytest.mark.parametrize("grant", ["anonymous", "wrong", "limited", "full"])
def test_permissions_before_service(client, enforced, source, grant):
    enforced(
        "Ana",
        caps=frozenset(
            {"view_operations" if grant == "wrong" else "edit_operations"}
        ),
        scope=AccessScope.limited(accounts=["ACME"])
        if grant == "limited"
        else AccessScope.everything(),
    )
    if grant == "anonymous":
        client.logout()
    response = client.post(URL, BODY, content_type="application/json")
    assert response.status_code == (200 if grant == "full" else 403)
    if grant != "full":
        source.assert_not_called()


def test_csrf_and_body_before_service(client, source):
    strict = Client(enforce_csrf_checks=True)
    assert (
        strict.post(URL, BODY, content_type="application/json").status_code
        == 403
    )
    assert (
        client.post(URL, [], content_type="application/json").status_code == 400
    )
    assert client.get(URL).status_code == 405
    source.assert_not_called()
    token = "a" * 32
    strict.cookies["csrftoken"] = token
    assert (
        strict.post(
            URL, BODY, content_type="application/json", HTTP_X_CSRFTOKEN=token
        ).status_code
        == 200
    )


def test_original_validation_result_and_public_transport_error(client, source):
    source.return_value = {"ok": False, "error": "Impacto inválido."}
    assert (
        client.post(URL, BODY, content_type="application/json").json()["data"]
        == source.return_value
    )
    source.side_effect = SheetsError("secret")
    response = client.post(URL, BODY, content_type="application/json")
    assert response.status_code == 502
    assert "secret" not in response.content.decode()
