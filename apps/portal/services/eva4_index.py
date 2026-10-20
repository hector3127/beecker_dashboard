"""Indice anual compartido para consultas mensuales de EVA-04."""

import hashlib
import threading
from typing import Any

from django.conf import settings
from django.core.cache import cache

from apps.portal.services.eva4_hours import build_hour_index
from core.sheets.protocols import SheetReader

_LOCKS = [threading.RLock() for _ in range(16)]


def use_store(year: int) -> bool:
    """Indica si las horas del ano se leen de la base de datos."""
    if not settings.CLOCKIFY_STORE_ENABLED:
        return False
    # Import diferido: los modelos requieren las apps ya cargadas.
    from apps.datastore.services.stored_base import year_is_synced

    return year_is_synced(year)


def index_key(year: int) -> str:
    """Separa el indice por archivo de Sheets y ano de la base."""
    scope = hashlib.sha256(settings.GOOGLE_SPREADSHEET_ID.encode()).hexdigest()
    return f"portal:eva4:hours-index:v3:{scope}:{year}"


def load_hour_index(reader: SheetReader, year: int) -> dict[str, Any]:
    """Reutiliza doce meses y agrupa solicitudes simultaneas."""
    from_store = use_store(year)
    key = index_key(year)
    if from_store:
        from apps.datastore.services.clockify_store import store_stamp

        # Cada sincronizacion invalida el indice guardado.
        key += f":db:{store_stamp()}"
    with _LOCKS[year % len(_LOCKS)]:
        cached = cache.get(key)
        if isinstance(cached, dict):
            return cached
        if from_store:
            from apps.datastore.services.stored_base import (
                build_hour_index_from_store,
            )

            index = build_hour_index_from_store(year)
        else:
            index = build_hour_index(
                reader.read_values(f"08.Base Clockify {year}"), year
            )
        cache.set(key, index, 300)
        return index


def invalidate_year(year: int) -> None:
    """Invalida el indice cuando la aplicacion sincroniza su base."""
    with _LOCKS[year % len(_LOCKS)]:
        cache.delete(index_key(year))
