"""Cache del resultado anual de GSE."""

import hashlib
import json
import time
from collections.abc import Callable
from datetime import date
from typing import Any

from apps.gse.constants import (
    RESULT_CACHE_SCOPE,
    RESULT_CACHE_SECONDS,
    RESULT_MAX_CHARS,
)
from apps.gse.services.cells import norm
from apps.gse.services.year_base import parse_year
from core.sheets.read_cache import CacheStore

"""BKD.100.011 - Cache del resultado de GSE
Equivale a gseLeerResultadoCache() y gseGuardarResultadoCache(): guarda
el resultado anual terminado por ano y area durante 6 horas.
"""

JsonObject = dict[str, Any]

MILLISECONDS = 1000
CACHE_KEY_PREFIX = "gse:result:"


class ResultCache:
    """Resultado anual guardado por libro, ano, area y mes."""

    def __init__(
        self,
        store: CacheStore,
        spreadsheet_id: str,
        today: date,
        clock: Callable[[], float] = time.time,
    ) -> None:
        """
        Crea la cache del resultado anual.

        Args:
            store: Donde se guarda (la cache de Django).
            spreadsheet_id: ID del Spreadsheet.
            today: Fecha local de hoy.
            clock: Reloj en segundos desde 1970.
        """
        self._store = store
        self._spreadsheet_id = spreadsheet_id
        self._month = today.strftime("%Y-%m")
        self._clock = clock

    def read(
        self,
        request: tuple[object, object, bool],
    ) -> JsonObject:
        """
        Lee el resultado guardado, o lo borra si se pide.

        Args:
            request: Ano, area y si se debe borrar.

        Returns:
            {"ok": True, "cached": False} o el resultado guardado.
        """
        year, area, clear = request
        area_text = area if isinstance(area, str) else ""
        key = self._key(year, area_text)

        if clear:
            self._store.delete(key)

            if area_text:
                self._store.delete(self._key(year, ""))

            return {"ok": True, "cached": False}

        stored = self._store.get(key)

        if not isinstance(stored, dict):
            return self._read_global(year, area_text)

        if self._clock() * MILLISECONDS - stored["savedAt"] > (
            RESULT_CACHE_SECONDS * MILLISECONDS
        ):
            return {"ok": True, "cached": False}

        return {
            "ok": True,
            "cached": True,
            "data": stored["data"],
            "bandas": stored["bandas"],
            "savedAt": stored["savedAt"],
            "total": stored["total"],
            "scopeArea": area_text,
        }

    def save(
        self,
        year: object,
        area: object,
        result: object,
    ) -> JsonObject:
        """
        Guarda un resultado terminado.

        Args:
            year: Ano consultado.
            area: Area consultada; vacio para todas.
            result: {"data", "bandas", "total"} que armo el frontend.

        Returns:
            {"ok": True, "savedAt"} o {"ok": False, "error"}.
        """
        data = result.get("data") if isinstance(result, dict) else None

        if not data or any(
            isinstance(month, dict)
            and (month.get("pending") or month.get("parcial"))
            for month in data.values()
        ):
            return {
                "ok": False,
                "error": "Solo se guardan lecturas terminadas.",
            }

        assert isinstance(result, dict)
        saved_at = int(self._clock() * MILLISECONDS)
        stored = {
            "data": data,
            "bandas": result.get("bandas") or [],
            "total": result.get("total"),
            "savedAt": saved_at,
        }

        if len(json.dumps(stored, default=str)) > RESULT_MAX_CHARS:
            return {
                "ok": False,
                "error": "Resultado demasiado grande para caché.",
            }

        area_text = area if isinstance(area, str) else ""
        self._store.set(
            self._key(year, area_text),
            stored,
            RESULT_CACHE_SECONDS,
        )

        return {"ok": True, "savedAt": saved_at}

    def _read_global(self, year: object, area: str) -> JsonObject:
        """Si no hay resultado del area, usa el de todas las areas."""
        if area:
            general = self.read((year, "", False))

            if general.get("cached"):
                return {**general, "scopeArea": ""}

        return {"ok": True, "cached": False}

    def _key(self, year: object, area: str) -> str:
        """Llave con el libro, el ano, el area y el mes de hoy."""
        scope = json.dumps(
            [
                RESULT_CACHE_SCOPE,
                self._spreadsheet_id,
                parse_year(year) or str(year),
                norm(area),
                self._month,
            ],
            separators=(",", ":"),
            ensure_ascii=False,
        )
        digest = hashlib.sha256(scope.encode()).hexdigest()

        return f"{CACHE_KEY_PREFIX}{digest}"
