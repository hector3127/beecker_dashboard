"""Cache compartida de lecturas de Google Sheets."""

import hashlib
from typing import Any, Final, Protocol

from core.utils.cell_types import CellValue

"""BKD.004.008 - Cache de lecturas de Sheets
Guarda las hojas leidas en la cache de Django para que las siguientes
peticiones no vuelvan a pedirlas a Google. Cada escritura de la app
invalida su hoja; los cambios hechos a mano en el Spreadsheet se ven al
vencer SHEETS_READ_CACHE_SECONDS.
"""

KEY_PREFIX: Final[str] = "sheets:v1"
SHEET_IDS_KEY: Final[str] = "ids"

SheetValues = list[list[CellValue]]


class CacheStore(Protocol):
    """Cache con borrado (la cache de Django la cumple)."""

    def get(self, key: str) -> Any:
        """Lee un valor; None si no existe."""
        ...

    def set(self, key: str, value: object, timeout: int | None) -> None:
        """Guarda un valor."""
        ...

    def delete(self, key: str) -> Any:
        """Borra un valor."""
        ...


def django_cache() -> CacheStore:
    """La cache de Django, importada al usarla para no exigirla antes."""
    from django.core.cache import cache

    django_store: CacheStore = cache

    return django_store


class SheetReadCache:
    """Valores de hojas y nombres de pestanas con vencimiento."""

    def __init__(
        self,
        spreadsheet_id: str,
        seconds: int,
        store: CacheStore | None = None,
    ) -> None:
        """
        Crea la cache de un Spreadsheet.

        Args:
            spreadsheet_id: ID del Spreadsheet.
            seconds: Segundos de vida; 0 apaga la cache.
            store: Donde se guardan los datos; por defecto la de Django.
        """
        self._seconds = seconds
        self._store = store
        self._prefix = (
            f"{KEY_PREFIX}:"
            f"{hashlib.sha256(spreadsheet_id.encode()).hexdigest()[:12]}"
        )

    @property
    def enabled(self) -> bool:
        """Indica si la cache esta encendida."""
        return self._seconds > 0

    def get_values(self, sheet_name: str) -> SheetValues | None:
        """
        Lee los valores guardados de una hoja.

        Args:
            sheet_name: Nombre de la hoja.

        Returns:
            Los valores, o None si no hay o estan danados.
        """
        stored = self._get(self._values_key(sheet_name))

        return stored if isinstance(stored, list) else None

    def set_values(self, sheet_name: str, values: SheetValues) -> None:
        """
        Guarda los valores de una hoja.

        Args:
            sheet_name: Nombre de la hoja.
            values: Matriz leida de Sheets.
        """
        self._set(self._values_key(sheet_name), values)

    def get_sheet_ids(self) -> dict[str, int] | None:
        """Nombres e IDs de las hojas, o None si no estan guardados."""
        stored = self._get(f"{self._prefix}:{SHEET_IDS_KEY}")

        return stored if isinstance(stored, dict) else None

    def set_sheet_ids(self, sheet_ids: dict[str, int]) -> None:
        """Guarda los nombres e IDs de las hojas."""
        self._set(f"{self._prefix}:{SHEET_IDS_KEY}", sheet_ids)

    def invalidate_values(self, sheet_name: str) -> None:
        """Borra los valores guardados de una hoja."""
        self._delete(self._values_key(sheet_name))

    def invalidate_sheet_ids(self) -> None:
        """Borra los nombres de hojas (se creo o elimino una pestana)."""
        self._delete(f"{self._prefix}:{SHEET_IDS_KEY}")

    def _cache(self) -> CacheStore:
        """El almacen configurado o la cache de Django."""
        return self._store if self._store is not None else django_cache()

    def _values_key(self, sheet_name: str) -> str:
        """Llave de una hoja; el nombre va en hash por sus acentos."""
        digest = hashlib.sha256(sheet_name.encode()).hexdigest()[:16]

        return f"{self._prefix}:values:{digest}"

    def _get(self, key: str) -> Any:
        """Lee una llave si la cache esta encendida."""
        if not self.enabled:
            return None
        try:
            return self._cache().get(key)
        except OSError:
            # Windows niega borrar o leer un archivo que otro proceso tiene
            # abierto; se toma como falla de cache y se lee de Google.
            return None

    def _set(self, key: str, value: object) -> None:
        """Guarda una llave si la cache esta encendida."""
        if not self.enabled:
            return
        try:
            self._cache().set(key, value, self._seconds)
        except OSError:
            return

    def _delete(self, key: str) -> None:
        """Borra una llave; un archivo bloqueado no detiene la peticion."""
        if not self.enabled:
            return
        try:
            self._cache().delete(key)
        except OSError:
            return
