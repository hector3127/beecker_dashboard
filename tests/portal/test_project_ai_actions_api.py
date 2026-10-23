"""Acciones IA: servicios originales, permisos, alcance y CSRF."""

from unittest.mock import Mock

import pytest
from django.test import Client

from apps.access.scope import AccessScope
from apps.portal.api import project_ai as api
from core.exceptions import SheetsError

pytestmark = pytest.mark.django_db
BASE = "/api/v1/screens/proyectos/CCO.001%20%7C%20CR/ia/"
PROJECT = "CCO.001 | CR"
PAYLOAD = {
    "contexto": {"fuentes": ["azure"]},
    "forzar": True,
    "pregunta": "Pregunta exacta",
    "snapshot": {"horas": 8},
    "analisis": {"resumen": []},
    "tema": "Tema",
    "fecha": "2026-10-23",
    "contenido": "Contenido",
    "url": "https://drive.google.com/drive/folders/a",
    "tipo": "transcripciones",
    "carpeta": "folder",
    "archivo": "file",
    "archivos": ["file"],
    "notas": "Apuntes",
    "ID_Proyecto": "AJENO",
}
CASES = {
    "analizar/": (
        "ai",
        "analyze_project",
        "edit_operations",
        ("claude", "store", (PROJECT, PAYLOAD["contexto"], True)),
    ),
    "preguntar/": (
        "ai",
        "ask_question",
        "edit_operations",
        ("claude", (PROJECT, PAYLOAD["contexto"], "Pregunta exacta")),
    ),
    "memoria/guardar/": (
        "ai",
        "save_memory",
        "edit_operations",
        ("store", PROJECT, PAYLOAD["snapshot"], PAYLOAD["analisis"]),
    ),
    "minutas/guardar/": (
        "ai",
        "save_minute",
        "edit_operations",
        ("store", (PROJECT, "Tema", "2026-10-23", "Contenido")),
    ),
    "drive/carpetas/guardar/": (
        "drive",
        "save_folder",
        "manage_integrations",
        ("drive", PROJECT, PAYLOAD["url"], "transcripciones"),
    ),
    "drive/carpetas/quitar/": (
        "drive",
        "remove_folder",
        "manage_integrations",
        ("store", PROJECT, "folder", "transcripciones"),
    ),
    "drive/documento/leer/": (
        "drive",
        "read_document",
        "view_operations",
        ("drive", PROJECT, "file"),
    ),
    "drive/minuta/generar/": (
        "drive",
        "generate_minute",
        "edit_operations",
        (
            "claude",
            "drive",
            (PROJECT, ["file"], "Tema", "2026-10-23", "Apuntes"),
        ),
    ),
    "accion/guardar/": (
        "client",
        "save_record",
        "edit_operations",
        ("client-store", "accion", {**PAYLOAD, "ID_Proyecto": PROJECT}),
    ),
}


@pytest.fixture
def services(monkeypatch):
    for name, value in [
        ("build_claude", "claude"),
        ("build_ixs_store", "store"),
        ("build_drive_context", "drive"),
    ]:
        monkeypatch.setattr(api.ai_rpc, name, lambda value=value: value)
    monkeypatch.setattr(
        api.ixs_rpc, "build_store_sheets", lambda: "client-store"
    )
    modules = {
        "ai": api.ixs_ai,
        "drive": api.ixs_drive,
        "client": api.ixs_client,
    }
    result = {}
    for path, (module, name, _, _) in CASES.items():
        result[path] = Mock(return_value={"ok": True, "texto": "Borrador"})
        monkeypatch.setattr(modules[module], name, result[path])
    return result


@pytest.mark.parametrize("path", CASES)
@pytest.mark.parametrize("ok", [True, False])
def test_exact_service_response_and_project(client, services, path, ok):
    result = {"ok": ok, "texto": "Borrador", "error": "Pendiente"}
    services[path].return_value = result
    response = client.post(
        BASE + path, PAYLOAD, content_type="application/json"
    )
    assert response.status_code == 200
    assert response.json() == {"data": result, "meta": {}}
    services[path].assert_called_once_with(*CASES[path][3])


@pytest.mark.parametrize("path", CASES)
@pytest.mark.parametrize("grant", ["none", "limited", "anonymous", "full"])
def test_permission_before_services(client, services, enforced, path, grant):
    enforced(
        "Ana",
        caps=frozenset() if grant == "none" else frozenset({CASES[path][2]}),
        scope=AccessScope.limited(accounts=["ACME"])
        if grant == "limited"
        else AccessScope.everything(),
    )
    if grant == "anonymous":
        client.logout()
    response = client.post(
        BASE + path, PAYLOAD, content_type="application/json"
    )
    if grant == "full":
        assert response.status_code == 200
        services[path].assert_called_once()
    else:
        assert response.status_code in {401, 403}
        services[path].assert_not_called()


@pytest.mark.parametrize("path", CASES)
def test_csrf_invalid_body_and_safe_errors(client, services, path):
    assert (
        Client(enforce_csrf_checks=True)
        .post(BASE + path, PAYLOAD, content_type="application/json")
        .status_code
        == 403
    )
    assert (
        client.post(
            BASE + path, [], content_type="application/json"
        ).status_code
        == 400
    )
    services[path].assert_not_called()
    services[path].side_effect = SheetsError("Error simulado")
    response = client.post(
        BASE + path, PAYLOAD, content_type="application/json"
    )
    assert response.status_code == 200
    assert response.json()["data"]["ok"] is False
    assert client.get(BASE + path).status_code == 405
