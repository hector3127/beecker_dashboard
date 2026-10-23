"""Lecturas IA: mismos servicios, alcance y permisos que el RPC."""

from unittest.mock import Mock

import pytest

from apps.access.scope import AccessScope
from apps.portal.api import project_ai as api
from core.exceptions import SheetsError

pytestmark = pytest.mark.django_db
BASE = "/api/v1/screens/proyectos/CCO.001%20%7C%20CR/"
READS = {
    "cliente/": ("client", "read_client_actions", "client-store"),
    "ia/analisis/": ("ai", "read_analysis", "ai-store"),
    "ia/memoria/": ("ai", "read_memory", "ai-store"),
    "ia/minutas/": ("ai", "read_minutes", "ai-store"),
    "ia/drive/carpetas/": ("drive", "read_config", "ai-store"),
    "ia/drive/archivos/": ("drive", "list_files", "drive-context"),
}


@pytest.fixture
def sources(monkeypatch):
    modules = {
        "client": api.ixs_client,
        "ai": api.ixs_ai,
        "drive": api.ixs_drive,
    }
    monkeypatch.setattr(
        api.ixs_rpc, "build_store_sheets", lambda: "client-store"
    )
    monkeypatch.setattr(api.ai_rpc, "build_ixs_store", lambda: "ai-store")
    monkeypatch.setattr(
        api.ai_rpc, "build_drive_context", lambda: "drive-context"
    )
    monkeypatch.setattr(
        api.ai_rpc,
        "build_claude",
        Mock(side_effect=AssertionError("Unexpected model access")),
    )
    result = {}
    for path, (module, name, _) in READS.items():
        source = Mock(return_value={"ok": True, "filas": [], "aviso": "Corte"})
        monkeypatch.setattr(modules[module], name, source)
        result[path] = source
    return result


@pytest.mark.parametrize("path", READS)
@pytest.mark.parametrize("ok", [True, False])
def test_exact_service_response_and_project_id(client, sources, path, ok):
    result = {"ok": ok, "filas": [], "error": "Fuente no disponible"}
    sources[path].return_value = result
    response = client.get(BASE + path)
    assert response.status_code == 200
    assert response.json() == {"data": result, "meta": {}}
    sources[path].assert_called_once_with(READS[path][2], "CCO.001 | CR")


@pytest.mark.parametrize("path", READS)
@pytest.mark.parametrize("grant", ["none", "limited", "anonymous"])
def test_permission_checked_before_source(
    client, sources, enforced, path, grant
):
    capability = (
        "manage_integrations"
        if path == "ia/drive/carpetas/"
        else "view_operations"
    )
    enforced(
        "Ana",
        caps=frozenset() if grant == "none" else frozenset({capability}),
        scope=AccessScope.limited(accounts=["ACME"])
        if grant == "limited"
        else AccessScope.everything(),
    )
    if grant == "anonymous":
        client.logout()
    assert client.get(BASE + path).status_code in {401, 403}
    sources[path].assert_not_called()


@pytest.mark.parametrize("path", READS)
def test_full_authorized_scope(client, sources, enforced, path):
    capability = (
        "manage_integrations"
        if path == "ia/drive/carpetas/"
        else "view_operations"
    )
    enforced(
        "Ana", caps=frozenset({capability}), scope=AccessScope.everything()
    )
    assert client.get(BASE + path).status_code == 200
    sources[path].assert_called_once()


def test_folder_configuration_keeps_manage_integrations_permission(
    client, sources, enforced
):
    enforced(
        "Ana",
        caps=frozenset({"view_operations", "edit_operations"}),
        scope=AccessScope.everything(),
    )
    assert client.get(BASE + "ia/drive/carpetas/").status_code == 403
    sources["ia/drive/carpetas/"].assert_not_called()


@pytest.mark.parametrize("path", READS)
def test_same_safe_error_wrapper_and_read_only(client, sources, path):
    sources[path].side_effect = SheetsError("Fallo simulado")
    response = client.get(BASE + path)
    assert response.status_code == 200
    assert response.json()["data"]["ok"] is False
    assert client.post(BASE + path, {}).status_code == 405
