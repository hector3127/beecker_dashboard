"""Registro RAID por API v1: mismo servicio, permisos de lectura y errores."""

from unittest.mock import Mock

import pytest

from apps.portal.api import project_detail as api
from core.exceptions import SheetsError

pytestmark = pytest.mark.django_db
URL = "/api/v1/screens/proyectos/AMK.008/raid-registro/"


def test_same_service_and_response(client, monkeypatch):
    result = {"ok": True, "registros": [{"id": 1}], "aviso": ""}
    source = Mock(return_value=result)
    monkeypatch.setattr(api.ixs_rpc, "list_raid", source)

    response = client.get(URL)

    assert response.json() == {"data": result, "meta": {}}
    source.assert_called_once_with("AMK.008", False)


def test_force_refresh_is_passed_only_when_asked(client, monkeypatch):
    source = Mock(return_value={"ok": True, "registros": []})
    monkeypatch.setattr(api.ixs_rpc, "list_raid", source)

    client.get(URL + "?forzar=1")
    client.get(URL + "?forzar=0")

    assert [c.args for c in source.call_args_list] == [
        ("AMK.008", True),
        ("AMK.008", False),
    ]


@pytest.mark.parametrize("grant", ["none", "limited"])
def test_read_needs_operations_with_full_scope(
    client, enforced, monkeypatch, grant
):
    from apps.access.scope import AccessScope

    source = Mock(side_effect=AssertionError("Source called without access"))
    monkeypatch.setattr(api.ixs_rpc, "list_raid", source)
    enforced(
        "Ana",
        caps=frozenset() if grant == "none" else frozenset({"view_operations"}),
        scope=AccessScope.limited(accounts=["ACME"])
        if grant == "limited"
        else AccessScope.everything(),
    )

    assert client.get(URL).status_code in {401, 403}
    source.assert_not_called()


def test_public_source_error_hides_details(client, monkeypatch):
    monkeypatch.setattr(
        api.ixs_rpc, "list_raid", Mock(side_effect=SheetsError("secret"))
    )

    response = client.get(URL)

    assert response.status_code == 502
    assert "secret" not in response.content.decode()


def test_post_is_not_allowed(client):
    assert client.post(URL, {}).status_code == 405
