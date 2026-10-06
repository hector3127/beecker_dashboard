"""Cache del RAID de cada Team Project para el dashboard ejecutivo."""

import logging
from collections.abc import Callable
from typing import Final, Protocol

from apps.azure_devops.constants import WORK_ITEMS_CACHE_SECONDS
from apps.azure_devops.services.azure_client import (
    AzureDevOpsClient,
    JsonObject,
)
from core.exceptions import DashboardError

"""BKD.030.012 - Cache del RAID
Guarda los work items RAID y los campos de Risk de cada Team Project.
Una version global invalida todos los proyectos a la vez cuando la app
crea un registro, sin tener que listar las llaves.
"""

logger = logging.getLogger(__name__)

RAID_VERSION_KEY: Final[str] = "azure:v1:raid_version"

RaidData = tuple[list[JsonObject], list[JsonObject]]


class CacheStore(Protocol):
    """Cache con borrado (la cache de Django la cumple)."""

    def get(self, key: str) -> object:
        """Lee un valor; None si no existe."""
        ...

    def set(self, key: str, value: object, timeout: int | None) -> None:
        """Guarda un valor; timeout None no expira."""
        ...


def clear_raid_cache(store: CacheStore) -> None:
    """
    Invalida el RAID guardado de todos los Team Projects.

    Args:
        store: Cache donde viven las versiones.
    """
    store.set(RAID_VERSION_KEY, read_version(store) + 1, None)


def read_version(store: CacheStore) -> int:
    """Version actual del RAID guardado; 0 si todavia no hay."""
    current = store.get(RAID_VERSION_KEY)

    return current if isinstance(current, int) else 0


def read_raid(
    store: CacheStore,
    cache_prefix: str,
    build_client: Callable[[], AzureDevOpsClient],
    project_name: str,
) -> RaidData:
    """
    Lee los work items RAID y los campos de Risk, con cache.

    No guarda el resultado cuando los campos de Risk no se pudieron
    leer, para que el siguiente intento los pida otra vez.

    Args:
        store: Cache compartida.
        cache_prefix: Prefijo ligado a la organizacion y al PAT.
        build_client: Crea un cliente HTTP nuevo (uno por consulta).
        project_name: Nombre del Team Project.

    Returns:
        Los work items RAID y los campos de Risk.
    """
    version = read_version(store)
    cache_key = f"{cache_prefix}:raid:{version}:{project_name}"
    cached_raid = store.get(cache_key)

    if isinstance(cached_raid, tuple):
        return cached_raid

    client = build_client()
    items = client.list_raid_items(project_name)

    try:
        fields = client.list_risk_fields(project_name)
    except DashboardError as error:
        logger.info("Campos de Risk no disponibles: %s", error.detail)

        return items, []

    store.set(cache_key, (items, fields), WORK_ITEMS_CACHE_SECONDS)

    return items, fields
