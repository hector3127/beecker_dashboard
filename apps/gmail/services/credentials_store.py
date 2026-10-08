"""Acceso temporal del usuario guardado en su sesion de Django."""

import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Protocol

from apps.gmail.constants import (
    EXPIRY_MARGIN_SECONDS,
    SESSION_CREDENTIALS_KEY,
)
from apps.gmail.exceptions import GmailNotConnectedError

"""BKD.110.005 - Acceso en la sesion
Guarda correo, acceso y vencimiento en la sesion del navegador. El
acceso dura una hora y no hay refresh token que proteger.
"""


class SessionLike(Protocol):
    """Lo que se usa de la sesion de Django."""

    def get(self, key: str, default: Any = None) -> Any:
        """Lee una llave."""
        ...

    def pop(self, key: str, default: Any = None) -> Any:
        """Quita una llave."""
        ...

    def __setitem__(self, key: str, value: Any) -> None:
        """Guarda una llave."""
        ...


@dataclass(frozen=True)
class StoredCredentials:
    """Cuenta conectada y su acceso temporal."""

    email: str
    access_token: str
    expires_at: float


def save_credentials(
    session: SessionLike,
    credentials: StoredCredentials,
) -> None:
    """
    Guarda el acceso del usuario en su sesion.

    Args:
        session: Sesion de Django.
        credentials: Cuenta y acceso recien obtenidos.
    """
    session[SESSION_CREDENTIALS_KEY] = {
        "email": credentials.email,
        "access_token": credentials.access_token,
        "expires_at": credentials.expires_at,
    }


def clear_credentials(session: SessionLike) -> None:
    """
    Quita el acceso guardado.

    Args:
        session: Sesion de Django.
    """
    session.pop(SESSION_CREDENTIALS_KEY, None)


def load_credentials(
    session: SessionLike,
    clock: Callable[[], float] = time.time,
) -> StoredCredentials | None:
    """
    Lee el acceso guardado si todavia sirve.

    Args:
        session: Sesion de Django.
        clock: Reloj, para poder probar el vencimiento.

    Returns:
        El acceso vigente, o None si no hay o ya vencio.
    """
    stored = session.get(SESSION_CREDENTIALS_KEY)

    if not isinstance(stored, dict):
        return None

    email = stored.get("email")
    token = stored.get("access_token")
    expires_at = stored.get("expires_at")

    if not (
        isinstance(email, str)
        and isinstance(token, str)
        and isinstance(expires_at, int | float)
    ):
        return None

    if expires_at - EXPIRY_MARGIN_SECONDS <= clock():
        clear_credentials(session)

        return None

    return StoredCredentials(email, token, float(expires_at))


def require_credentials(
    session: SessionLike,
    clock: Callable[[], float] = time.time,
) -> StoredCredentials:
    """
    Lee el acceso o pide conectar la cuenta.

    Args:
        session: Sesion de Django.
        clock: Reloj, para poder probar el vencimiento.

    Returns:
        El acceso vigente.

    Raises:
        GmailNotConnectedError: Cuando no hay acceso vigente.
    """
    credentials = load_credentials(session, clock)

    if credentials is None:
        raise GmailNotConnectedError

    return credentials
