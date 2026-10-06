"""Organizacion, proyecto activo y PAT de Azure DevOps del panel Daily."""

import hashlib
from dataclasses import dataclass
from typing import Protocol

"""BKD.070.004 - Conexion de Azure del Daily
Equivale a ixsCredenciales_() en modo compartido: la organizacion y el
PAT vienen del .env; el proyecto activo se guarda en la cache
persistente para que el selector del panel pueda cambiarlo.
"""

ACTIVE_PROJECT_KEY = "daily:azure:active_project"


class DailyCache(Protocol):
    """Cache con borrado (la cache de Django la cumple)."""

    def get(self, key: str) -> object:
        """Lee un valor; None si no existe."""
        ...

    def set(self, key: str, value: object, timeout: int | None) -> None:
        """Guarda un valor; timeout None no expira."""
        ...

    def delete(self, key: str) -> object:
        """Borra un valor."""
        ...


@dataclass(frozen=True, slots=True)
class AzureConnection:
    """Datos para llamar a Azure DevOps."""

    organization: str
    project: str
    personal_access_token: str

    @property
    def is_complete(self) -> bool:
        """Indica si hay organizacion, proyecto y PAT."""
        return bool(
            self.organization and self.project and self.personal_access_token,
        )

    @property
    def cache_prefix(self) -> str:
        """Prefijo de cache por credencial y proyecto activo."""
        fingerprint = hashlib.sha256(
            f"{self.organization}|{self.personal_access_token}".encode(),
        ).hexdigest()[:16]

        return f"daily:azure:{fingerprint}:{self.project}"


class ConnectionStore:
    """Lee la configuracion y guarda el proyecto activo."""

    def __init__(
        self,
        cache: DailyCache,
        organization: str,
        personal_access_token: str,
        default_project: str,
    ) -> None:
        self._cache = cache
        self.organization = organization
        self.personal_access_token = personal_access_token
        self._default_project = default_project

    def load(self) -> AzureConnection:
        """
        Arma la conexion con el proyecto activo.

        Returns:
            La conexion (puede estar incompleta).
        """
        return AzureConnection(
            self.organization,
            self.active_project(),
            self.personal_access_token,
        )

    def active_project(self) -> str:
        """
        Proyecto elegido en el selector o el del .env.

        Returns:
            El nombre del Team Project.
        """
        stored = self._cache.get(ACTIVE_PROJECT_KEY)

        if isinstance(stored, str) and stored:
            return stored

        return self._default_project

    def set_active_project(self, project: str) -> None:
        """
        Guarda el proyecto activo sin expiracion.

        Args:
            project: Nombre del Team Project.
        """
        self._cache.set(ACTIVE_PROJECT_KEY, project, None)

    def clear_active_project(self) -> None:
        """Vuelve al proyecto del .env."""
        self._cache.delete(ACTIVE_PROJECT_KEY)
