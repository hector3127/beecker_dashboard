"""Indice anual compartido para consultas mensuales de EVA-04."""

import hashlib
import threading
from typing import Any

from django.conf import settings
from django.core.cache import cache

from apps.portal.services.eva4_hours import build_hour_index
from core.sheets.protocols import SheetReader

_LOCKS = [threading.RLock() for _ in range(16)]


def index_key(year: int) -> str:
    """Separa el indice por archivo de Sheets y ano de la base."""
    scope = hashlib.sha256(settings.GOOGLE_SPREADSHEET_ID.encode()).hexdigest()
    return f"portal:eva4:hours-index:v1:{scope}:{year}"


def load_hour_index(reader: SheetReader, year: int) -> dict[str, Any]:
    """Reutiliza doce meses y agrupa solicitudes simultaneas."""
    key = index_key(year)
    with _LOCKS[year % len(_LOCKS)]:
        cached = cache.get(key)
        if isinstance(cached, dict):
            return cached
        index = build_hour_index(
            reader.read_values(f"08.Base Clockify {year}"), year
        )
        cache.set(key, index, 300)
        return index


def invalidate_year(year: int) -> None:
    """Invalida el indice cuando la aplicacion sincroniza su base."""
    with _LOCKS[year % len(_LOCKS)]:
        cache.delete(index_key(year))
