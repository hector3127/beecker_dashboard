"""Fuente de horas basada en Clockify, con cache y respaldo."""

import hashlib
import logging
from typing import Final

from django.conf import settings
from django.core.cache import cache
from django.utils import timezone

from apps.clockify.constants import (
    ALL_ENTRIES_CACHE_SECONDS,
    BACKUP_CACHE_SECONDS,
)
from apps.clockify.exceptions import ClockifyConfigurationError
from apps.clockify.services.clockify_client import ClockifyClient
from apps.clockify.services.time_entry_loader import ClockifyTimeEntryLoader
from core.exceptions import TimeEntrySourceError
from core.sheets.protocols import SheetReader
from core.time_entries.models import TimeEntry, TimeEntryBatch

"""BKD.020.009 - Fuente de horas Clockify
Equivale al cache y al respaldo de leerRegistrosTiempo(): guarda el
agregado 15 minutos y un respaldo de 6 horas que se muestra con alerta
si Clockify falla.
"""

logger = logging.getLogger(__name__)

# Cambia la version al modificar TimeEntry para no leer datos viejos.
CACHE_VERSION: Final[str] = "v5"


def build_clockify_loader(reader: SheetReader) -> ClockifyTimeEntryLoader:
    """
    Crea el cargador de Clockify con la configuracion y cache de Django.

    Args:
        reader: Repositorio de Sheets de la peticion actual.

    Returns:
        El cargador listo para consultar proyectos.

    Raises:
        ClockifyConfigurationError: Cuando falta la configuracion.
    """
    api_key, workspace_id = read_clockify_settings()

    return ClockifyTimeEntryLoader(
        reader=reader,
        client_factory=lambda: ClockifyClient(api_key),
        workspace_id=workspace_id,
        today=timezone.localdate(),
        cache_store=cache,
        cache_prefix=build_cache_prefix(api_key, workspace_id),
    )


class ClockifyTimeEntryProvider:
    """Entrega las horas de todo el portafolio desde Clockify."""

    def __init__(self, reader: SheetReader) -> None:
        self._reader = reader

    def load_time_entries(self) -> TimeEntryBatch:
        """
        Regresa las horas del portafolio.

        Returns:
            Los registros; si Clockify falla y hay respaldo, el lote se
            marca como respaldo para que el panel muestre la alerta.

        Raises:
            ClockifyConfigurationError: Cuando falta la configuracion.
            TimeEntrySourceError: Cuando falla y no hay respaldo.
        """
        api_key, workspace_id = read_clockify_settings()
        cache_prefix = build_cache_prefix(api_key, workspace_id)
        all_entries_key = f"{cache_prefix}:all"
        backup_key = f"{cache_prefix}:backup"

        cached_entries = cache.get(all_entries_key)

        if isinstance(cached_entries, tuple):
            return TimeEntryBatch(entries=cached_entries)

        loader = build_clockify_loader(self._reader)

        try:
            entries = loader.load_all()
        except TimeEntrySourceError as error:
            return build_backup_batch(cache.get(backup_key), error)

        cache.set(all_entries_key, entries, ALL_ENTRIES_CACHE_SECONDS)
        cache.set(
            backup_key,
            {"date": timezone.now().isoformat(), "entries": entries},
            BACKUP_CACHE_SECONDS,
        )

        return TimeEntryBatch(entries=entries)


def read_clockify_settings() -> tuple[str, str]:
    """
    Lee la API key y el workspace configurados en .env.

    Returns:
        La API key y el ID del workspace.

    Raises:
        ClockifyConfigurationError: Cuando falta alguno de los dos.
    """
    api_key = settings.CLOCKIFY_API_KEY
    workspace_id = settings.CLOCKIFY_WORKSPACE_ID

    if not api_key:
        raise ClockifyConfigurationError(
            "Define CLOCKIFY_API_KEY en el archivo .env.",
        )

    if not workspace_id:
        raise ClockifyConfigurationError(
            "Define CLOCKIFY_WORKSPACE_ID en el archivo .env. Puedes ver "
            "los disponibles con: python manage.py clockify_workspaces",
        )

    return api_key, workspace_id


def build_cache_prefix(api_key: str, workspace_id: str) -> str:
    """
    Construye el prefijo de cache ligado a la credencial activa.

    Un cambio de API key no reutiliza datos de la cuenta anterior. La
    clave nunca se guarda: solo una huella corta.

    Args:
        api_key: API key de Clockify.
        workspace_id: ID del workspace.

    Returns:
        El prefijo de las llaves de cache.
    """
    key_fingerprint = hashlib.sha256(api_key.encode("utf-8")).hexdigest()[:16]

    return f"clockify:{CACHE_VERSION}:{workspace_id}:{key_fingerprint}"


def build_backup_batch(
    backup: object,
    error: TimeEntrySourceError,
) -> TimeEntryBatch:
    """
    Regresa el ultimo corte completo cuando Clockify falla.

    Args:
        backup: Respaldo guardado en cache, si existe.
        error: Error de la consulta actual.

    Returns:
        El lote marcado como respaldo.

    Raises:
        TimeEntrySourceError: Cuando no hay respaldo disponible.
    """
    if not isinstance(backup, dict) or not isinstance(
        backup.get("entries"),
        tuple,
    ):
        raise error

    logger.warning("Clockify fallo; se usa el respaldo: %s", error.detail)
    backup_entries: tuple[TimeEntry, ...] = backup["entries"]

    return TimeEntryBatch(
        entries=backup_entries,
        is_backup=True,
        backup_date=str(backup.get("date", "")),
        backup_error=error.detail,
    )
