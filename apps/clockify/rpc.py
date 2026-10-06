"""Funciones de Clockify expuestas al frontend por RPC."""

from django.conf import settings

from apps.clockify.services.clockify_client import ClockifyClient, JsonObject
from core.exceptions import DashboardError
from core.rpc.registry import register_rpc

"""BKD.020.011 - RPC de Clockify
Registra obtenerConfigClockify y listarWorkspacesClockify con los mismos
nombres y respuestas que en Apps Script.
"""

KEY_SUFFIX_LENGTH = 4


@register_rpc("obtenerConfigClockify")
def get_clockify_config() -> JsonObject:
    """
    Indica si Clockify esta configurado, sin exponer la API key.

    Returns:
        El mismo objeto que regresaba obtenerConfigClockify().
    """
    api_key = settings.CLOCKIFY_API_KEY

    return {
        "ok": True,
        "configurado": bool(api_key),
        "global": True,
        "sufijo": api_key[-KEY_SUFFIX_LENGTH:] if api_key else "",
        "workspaceId": settings.CLOCKIFY_WORKSPACE_ID,
        "workspaceName": settings.CLOCKIFY_WORKSPACE_ID,
    }


@register_rpc("listarWorkspacesClockify")
def list_clockify_workspaces(api_key: str = "") -> JsonObject:
    """
    Lista los workspaces visibles con la API key.

    Args:
        api_key: API key escrita en el panel; si viene vacia se usa la
            configurada en .env.

    Returns:
        {"ok": bool, "workspaces": [...], "error": str}.
    """
    effective_key = api_key or settings.CLOCKIFY_API_KEY

    if not effective_key:
        return {
            "ok": False,
            "error": "Falta la API key de Clockify.",
            "workspaces": [],
        }

    try:
        workspaces = ClockifyClient(effective_key).list_workspaces()
    except DashboardError as error:
        return {"ok": False, "error": error.build_message(), "workspaces": []}

    return {"ok": True, "workspaces": workspaces}
