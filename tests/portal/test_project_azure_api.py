"""Panel Azure: mismo servicio, refresco explícito y alcance del RPC."""

from unittest.mock import Mock

import pytest

from apps.access.scope import AccessScope
from apps.portal.api import project_detail as api
from core.exceptions import SheetsError

pytestmark = pytest.mark.django_db
URL = "/api/v1/screens/proyectos/CCO.001%20%7C%20CR/azure/"


@pytest.mark.parametrize(
    "query,force", [("", False), ("?forzar=1", True), ("?forzar=0", False)]
)
@pytest.mark.parametrize("ok", [True, False])
def test_service_response_and_force(client, monkeypatch, query, force, ok):
    result = {
        "ok": ok,
        "items": [],
        "allItems": [],
        "stale": [],
        "aviso": "Corte",
        "error": "Sin PAT",
    }
    source = Mock(return_value=result)
    monkeypatch.setattr(api, "get_ixs_panel", source)
    response = client.get(URL + query)
    assert response.status_code == 200
    assert response.json() == {"data": result, "meta": {}}
    source.assert_called_once_with("CCO.001 | CR", force)


@pytest.mark.parametrize("grant", ["none", "limited", "anonymous"])
def test_permission_checked_before_source(client, enforced, monkeypatch, grant):
    source = Mock(side_effect=AssertionError("Unauthorized source access"))
    monkeypatch.setattr(api, "get_ixs_panel", source)
    enforced(
        "Ana",
        caps=frozenset() if grant == "none" else frozenset({"view_operations"}),
        scope=AccessScope.limited(accounts=["ACME"])
        if grant == "limited"
        else AccessScope.everything(),
    )
    if grant == "anonymous":
        client.logout()
    assert client.get(URL).status_code in {401, 403}
    source.assert_not_called()


def test_full_scope_can_read(client, enforced, monkeypatch):
    enforced(
        "Ana",
        caps=frozenset({"view_operations"}),
        scope=AccessScope.everything(),
    )
    source = Mock(return_value={"ok": True})
    monkeypatch.setattr(api, "get_ixs_panel", source)
    assert client.get(URL).status_code == 200
    source.assert_called_once()


def test_public_error_and_read_only(client, monkeypatch):
    source = Mock(side_effect=SheetsError("secret"))
    monkeypatch.setattr(api, "get_ixs_panel", source)
    response = client.get(URL)
    assert response.status_code == 502
    assert "secret" not in response.content.decode()
    assert client.post(URL, {}).status_code == 405


def test_planning_keeps_cached_read_even_with_force_parameter(
    client, monkeypatch
):
    source = Mock(return_value={"ok": True})
    monkeypatch.setattr(api, "get_ixs_panel", source)
    client.get(URL.replace("/azure/", "/planeacion/azure/") + "?forzar=1")
    source.assert_called_once_with("CCO.001 | CR", False)
