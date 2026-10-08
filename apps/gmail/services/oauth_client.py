"""Inicio de sesion con Google (OAuth 2.0 sin guardar refresh token)."""

import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Protocol
from urllib.parse import urlencode

import requests

from apps.gmail.constants import (
    AUTH_URL,
    CODE_EXCHANGE_URL,
    HTTP_TIMEOUT_SECONDS,
    OAUTH_SCOPES,
    USERINFO_URL,
)
from apps.gmail.exceptions import GmailAuthError

"""BKD.110.004 - Cliente OAuth de Google
Arma la direccion de inicio de sesion e intercambia el codigo por un
acceso de corta vida. No pide acceso offline: no se guarda ningun
refresh token, asi que el acceso vence en una hora y se vuelve a pedir.
"""


class HttpSession(Protocol):
    """Lo que se usa de requests para poder probarlo sin red."""

    def post(self, url: str, **kwargs: Any) -> Any:
        """Envia un POST."""
        ...

    def get(self, url: str, **kwargs: Any) -> Any:
        """Envia un GET."""
        ...


@dataclass(frozen=True)
class AccessToken:
    """Acceso temporal a Gmail."""

    value: str
    expires_at: float


class GoogleOAuth:
    """Flujo OAuth del usuario que genera la extension."""

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        session: HttpSession | None = None,
        clock: Callable[[], float] = time.time,
    ) -> None:
        self._client_id = client_id
        self._client_secret = client_secret
        self._http: Any = session if session is not None else requests
        self._clock = clock

    def build_authorization_url(
        self,
        redirect_uri: str,
        state: str,
    ) -> str:
        """
        Arma la direccion a la que se manda al usuario para iniciar sesion.

        Args:
            redirect_uri: Direccion registrada en Google a la que regresa.
            state: Valor aleatorio que se compara al regresar.

        Returns:
            La direccion de autorizacion de Google.
        """
        query = urlencode(
            {
                "client_id": self._client_id,
                "redirect_uri": redirect_uri,
                "response_type": "code",
                "scope": " ".join(OAUTH_SCOPES),
                "state": state,
                "access_type": "online",
                "prompt": "select_account",
            },
        )

        return f"{AUTH_URL}?{query}"

    def exchange_code(self, code: str, redirect_uri: str) -> AccessToken:
        """
        Cambia el codigo de autorizacion por un acceso temporal.

        Args:
            code: Codigo que regreso Google.
            redirect_uri: La misma direccion usada al iniciar.

        Returns:
            El acceso y el momento en que vence.

        Raises:
            GmailAuthError: Cuando Google rechaza el codigo.
        """
        try:
            response = self._http.post(
                CODE_EXCHANGE_URL,
                data={
                    "code": code,
                    "client_id": self._client_id,
                    "client_secret": self._client_secret,
                    "redirect_uri": redirect_uri,
                    "grant_type": "authorization_code",
                },
                timeout=HTTP_TIMEOUT_SECONDS,
            )
            payload = response.json()
        except (requests.RequestException, ValueError) as error:
            raise GmailAuthError("Google no respondio.") from error

        token = payload.get("access_token") if isinstance(payload, dict) else ""

        if response.status_code != 200 or not token:
            raise GmailAuthError("Google rechazo el codigo de acceso.")

        lifetime = _as_seconds(payload.get("expires_in"))

        return AccessToken(str(token), self._clock() + lifetime)

    def fetch_email(self, access_token: str) -> str:
        """
        Lee el correo de la cuenta que inicio sesion.

        Args:
            access_token: Acceso temporal recien obtenido.

        Returns:
            El correo en minusculas.

        Raises:
            GmailAuthError: Cuando Google no entrega el correo.
        """
        try:
            response = self._http.get(
                USERINFO_URL,
                headers={"Authorization": f"Bearer {access_token}"},
                timeout=HTTP_TIMEOUT_SECONDS,
            )
            payload = response.json()
        except (requests.RequestException, ValueError) as error:
            raise GmailAuthError("Google no respondio.") from error

        email = payload.get("email") if isinstance(payload, dict) else ""

        if response.status_code != 200 or not email:
            raise GmailAuthError("No se pudo leer el correo de la cuenta.")

        return str(email).strip().lower()


def _as_seconds(value: object) -> float:
    """Convierte expires_in a segundos; una hora si viene mal."""
    try:
        seconds = float(str(value))
    except ValueError:
        return 3600.0

    return seconds if seconds > 0 else 3600.0


def build_oauth(
    client_id: str,
    client_secret: str,
) -> GoogleOAuth:
    """
    Crea el cliente OAuth con las credenciales del .env.

    Args:
        client_id: ID del cliente OAuth.
        client_secret: Secreto del cliente OAuth.

    Returns:
        El cliente listo para usarse.
    """
    return GoogleOAuth(client_id, client_secret)
