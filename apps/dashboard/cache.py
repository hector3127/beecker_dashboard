"""Cache del dashboard general, equivalente a CacheService."""

import logging
from typing import Final

from django.conf import settings
from django.core.cache import cache

from apps.dashboard.services.response_builder import JsonObject

"""BKD.010.020 - Cache del dashboard
Guarda la vista general sin filtros durante DASHBOARD_CACHE_TTL_SECONDS
para que el panel cargue al instante.
"""

logger = logging.getLogger(__name__)

DASHBOARD_CACHE_KEY: Final[str] = "dashboard:general:v1"


def read_cached_dashboard() -> JsonObject | None:
    """
    Lee el dashboard general guardado en cache.

    Returns:
        La respuesta guardada, o None si no existe o esta danada.
    """
    cached_payload = cache.get(DASHBOARD_CACHE_KEY)

    if isinstance(cached_payload, dict):
        return cached_payload

    if cached_payload is not None:
        logger.warning("Cache del dashboard danada; se recalcula.")
        cache.delete(DASHBOARD_CACHE_KEY)

    return None


def save_cached_dashboard(payload: JsonObject) -> None:
    """
    Guarda el dashboard general en cache.

    Args:
        payload: Respuesta del dashboard.
    """
    cache.set(
        DASHBOARD_CACHE_KEY,
        payload,
        timeout=settings.DASHBOARD_CACHE_TTL_SECONDS,
    )


def clear_cached_dashboard() -> None:
    """Borra el dashboard general de la cache."""
    cache.delete(DASHBOARD_CACHE_KEY)
