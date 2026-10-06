"""Cliente minimo de la API de mensajes de Claude (Anthropic)."""

import json
from dataclasses import dataclass
from typing import Any

import requests

from core.exceptions import DashboardError

"""BKD.008.001 - Cliente de Claude
Equivale a las llamadas UrlFetchApp a https://api.anthropic.com/v1/messages
de DailyPanelService.gs. La API key llega desde ANTHROPIC_API_KEY del .env
y nunca se regresa al frontend.
"""

MESSAGES_URL = "https://api.anthropic.com/v1/messages"
API_VERSION = "2023-06-01"
DEFAULT_MODEL = "claude-haiku-4-5-20251001"
REQUEST_TIMEOUT_SECONDS = 55

JsonObject = dict[str, Any]


class ClaudeConnectionError(DashboardError):
    """No se pudo conectar con la API de Claude."""

    code = "ERR_CLAUDE_CONNECTION"
    expose_detail = True


@dataclass(frozen=True, slots=True)
class ClaudeResponse:
    """Respuesta HTTP de la API (codigo y cuerpo sin interpretar)."""

    status_code: int
    body: str

    def json(self) -> JsonObject:
        """Cuerpo como JSON (JSON.parse del original)."""
        data = json.loads(self.body)
        return data if isinstance(data, dict) else {}


class ClaudeClient:
    """Envia mensajes a Claude con la API key del servidor."""

    def __init__(
        self,
        api_key: str,
        session: requests.Session | None = None,
    ) -> None:
        self._api_key = api_key
        self._session = session or requests.Session()

    def create_message(self, payload: JsonObject) -> ClaudeResponse:
        """
        Envia un mensaje y regresa la respuesta sin validar el codigo.

        Args:
            payload: Cuerpo de /v1/messages (model, max_tokens, messages).

        Returns:
            El codigo HTTP y el cuerpo.

        Raises:
            ClaudeConnectionError: Si no hubo respuesta del servidor.
        """
        try:
            response = self._session.post(
                MESSAGES_URL,
                json=payload,
                headers={
                    "x-api-key": self._api_key,
                    "anthropic-version": API_VERSION,
                },
                timeout=REQUEST_TIMEOUT_SECONDS,
            )
        except requests.RequestException as error:
            raise ClaudeConnectionError(
                f"No se pudo conectar con Claude: {type(error).__name__}",
            ) from error

        return ClaudeResponse(response.status_code, response.text)


def text_blocks(data: JsonObject) -> list[str]:
    """
    Textos de los bloques type "text" de la respuesta.

    El arreglo content puede traer bloques de razonamiento antes del texto.

    Args:
        data: Respuesta de /v1/messages.

    Returns:
        Los textos en orden.
    """
    content = data.get("content")
    blocks = content if isinstance(content, list) else []

    return [
        str(block.get("text") or "")
        for block in blocks
        if isinstance(block, dict) and block.get("type") == "text"
    ]
