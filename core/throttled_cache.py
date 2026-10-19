"""Cache de archivos que limpia entradas viejas cada cierto de escrituras."""

from typing import Any, Final

from core.cache import ConcurrentFileBasedCache

"""BKD.001.005 - Cache de archivos con limpieza espaciada
FileBasedCache.set lista todos los archivos de la cache en cada escritura
para ver si pasa de MAX_ENTRIES. Con miles de archivos eso cuesta mas que
guardar el dato. Aqui la revision se hace en la primera escritura de cada
proceso y despues una vez cada CULL_EVERY escrituras: la cache puede pasar
de MAX_ENTRIES por unas decenas de archivos, nada mas.
"""

CULL_EVERY: Final[int] = 100


class ThrottledCullFileCache(ConcurrentFileBasedCache):
    """Revisa el tamano de la cache cada CULL_EVERY escrituras."""

    def __init__(self, dir: str, params: dict[str, Any]) -> None:
        super().__init__(dir, params)
        # La primera escritura de cada proceso si revisa.
        self._writes_since_cull = CULL_EVERY

    def _cull(self) -> None:
        """Limpia solo cuando ya hubo CULL_EVERY escrituras desde la ultima."""
        self._writes_since_cull += 1
        if self._writes_since_cull < CULL_EVERY:
            return
        self._writes_since_cull = 0
        super()._cull()  # type: ignore[misc]  # privado, sin stub de Django
