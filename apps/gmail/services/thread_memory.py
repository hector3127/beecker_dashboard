"""Recuerda que hilo se eligio para cada proyecto."""

from typing import Any, Protocol

from apps.gmail.services.thread_finder import normalize_text

"""BKD.110.010 - Hilo elegido por proyecto
Guarda en la cache de Django el hilo que se uso la ultima vez para que
la siguiente extension del mismo proyecto lo muestre como sugerido.
"""

KEY_PREFIX = "gmail:thread:"


class MemoryStore(Protocol):
    """Lo que se usa de la cache de Django."""

    def get(self, key: str, default: Any = None) -> Any:
        """Lee una llave."""
        ...

    def set(self, key: str, value: Any, timeout: int | None = ...) -> None:
        """Guarda una llave."""
        ...


def remember_thread(store: MemoryStore, project: str, thread_id: str) -> None:
    """
    Guarda el hilo elegido para un proyecto, sin vencimiento.

    Args:
        store: Cache de Django.
        project: ID del proyecto.
        thread_id: Hilo elegido.
    """
    key = normalize_text(project)

    if key and thread_id:
        store.set(f"{KEY_PREFIX}{key}", thread_id, None)


def recall_thread(store: MemoryStore, project: str) -> str:
    """
    Lee el hilo elegido antes para un proyecto.

    Args:
        store: Cache de Django.
        project: ID del proyecto.

    Returns:
        El ID del hilo, o cadena vacia si no hay.
    """
    key = normalize_text(project)

    if not key:
        return ""

    value = store.get(f"{KEY_PREFIX}{key}")

    return value if isinstance(value, str) else ""
