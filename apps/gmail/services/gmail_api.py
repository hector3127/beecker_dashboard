"""Llamadas a la API REST de Gmail con el acceso del usuario."""

from typing import Any

import requests

from apps.gmail.constants import GMAIL_API_URL, HTTP_TIMEOUT_SECONDS
from apps.gmail.exceptions import GmailApiError, GmailNotConnectedError

"""BKD.110.006 - API de Gmail
Busca hilos, lee sus encabezados y crea borradores o envia mensajes. Se
usa requests en lugar del SDK para poder probarlo sin red.
"""

METADATA_HEADERS = (
    "Subject",
    "From",
    "To",
    "Cc",
    "Reply-To",
    "Date",
    "Message-ID",
    "References",
    "In-Reply-To",
)

JsonObject = dict[str, Any]


class GmailApi:
    """Cliente de Gmail de un usuario."""

    def __init__(self, access_token: str, session: Any = None) -> None:
        self._token = access_token
        self._http: Any = session if session is not None else requests

    def search_thread_ids(self, query: str, limit: int) -> list[str]:
        """
        Busca hilos con la sintaxis de busqueda de Gmail.

        Args:
            query: Busqueda, por ejemplo subject:"Inicio de".
            limit: Maximo de hilos.

        Returns:
            Los IDs de los hilos, del mas reciente al mas antiguo.
        """
        payload = self._request(
            "GET",
            "/threads",
            params={"q": query, "maxResults": limit},
        )
        threads = payload.get("threads")

        if not isinstance(threads, list):
            return []

        return [
            str(thread["id"])
            for thread in threads
            if isinstance(thread, dict) and thread.get("id")
        ]

    def get_thread(self, thread_id: str) -> JsonObject:
        """
        Lee un hilo solo con los encabezados que se necesitan.

        Args:
            thread_id: ID del hilo.

        Returns:
            El hilo con sus mensajes.
        """
        return self._request(
            "GET",
            f"/threads/{thread_id}",
            params={
                "format": "metadata",
                "metadataHeaders": list(METADATA_HEADERS),
            },
        )

    def create_draft(self, raw: str, thread_id: str) -> JsonObject:
        """
        Crea un borrador dentro de un hilo.

        Args:
            raw: Mensaje MIME en base64 url-safe.
            thread_id: Hilo al que pertenece.

        Returns:
            El borrador creado.
        """
        return self._request(
            "POST",
            "/drafts",
            body={"message": {"raw": raw, "threadId": thread_id}},
        )

    def send_message(self, raw: str, thread_id: str) -> JsonObject:
        """
        Envia un mensaje dentro de un hilo.

        Args:
            raw: Mensaje MIME en base64 url-safe.
            thread_id: Hilo al que pertenece.

        Returns:
            El mensaje enviado.
        """
        return self._request(
            "POST",
            "/messages/send",
            body={"raw": raw, "threadId": thread_id},
        )

    def _request(
        self,
        method: str,
        path: str,
        params: dict[str, Any] | None = None,
        body: JsonObject | None = None,
    ) -> JsonObject:
        """Hace la llamada y convierte las fallas en errores del proyecto."""
        try:
            response = self._http.request(
                method,
                f"{GMAIL_API_URL}{path}",
                params=params,
                json=body,
                headers={"Authorization": f"Bearer {self._token}"},
                timeout=HTTP_TIMEOUT_SECONDS,
            )
        except requests.RequestException as error:
            raise GmailApiError("Gmail no respondio.") from error

        if response.status_code == 401:
            raise GmailNotConnectedError

        if response.status_code == 403:
            raise GmailApiError(
                "La cuenta no dio permiso para leer o crear correos.",
            )

        if response.status_code == 404:
            raise GmailApiError("El hilo ya no existe en esta cuenta.")

        if not 200 <= response.status_code < 300:
            raise GmailApiError(f"Gmail respondio {response.status_code}.")

        try:
            payload = response.json()
        except ValueError as error:
            raise GmailApiError("Gmail respondio algo ilegible.") from error

        return payload if isinstance(payload, dict) else {}
