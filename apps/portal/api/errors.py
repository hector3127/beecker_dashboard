"""Cuerpo de error comun de la API v1."""

from typing import Any

from rest_framework.response import Response

"""BKD.120.017 - Errores de la API v1
Un solo formato: {"error": {"code", "message", "fields"?}}. El cliente JS lo
convierte en un ApiError con el mismo codigo y mensaje.
"""


def error_response(
    status: int, code: str, message: str, fields: dict[str, Any] | None = None
) -> Response:
    """Respuesta de error con codigo estable y mensaje para la persona."""
    error: dict[str, Any] = {"code": code, "message": message}
    if fields:
        error["fields"] = fields
    return Response({"error": error}, status=status)
