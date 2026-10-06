"""Contrato de cache compartido por las integraciones."""

from typing import Protocol

"""BKD.003.005 - Contrato de cache
Permite inyectar la cache de Django en produccion y un diccionario en
las pruebas, en lugar de usar CacheService.
"""


class CacheStore(Protocol):
    """Cache clave-valor con expiracion (la cache de Django la cumple)."""

    def get(self, key: str) -> object:
        """Lee un valor; None si no existe."""
        ...

    def set(self, key: str, value: object, timeout: int) -> None:
        """Guarda un valor durante timeout segundos."""
        ...
