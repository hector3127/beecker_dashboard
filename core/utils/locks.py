"""Candado de escritura como LockService.getScriptLock() de Apps Script."""

import threading
from collections.abc import Iterator
from contextlib import contextmanager

from core.exceptions import DashboardError

"""BKD.002.005 - Candado de escritura
Evita que dos escrituras a la misma hoja se mezclen dentro de un proceso
del servidor. Con varios procesos cada uno tiene su propio candado.
"""

LOCK_TIMEOUT_MESSAGE = (
    "Lock timeout: another process was holding the lock for too long."
)

_SCRIPT_LOCK = threading.Lock()


class LockTimeoutError(DashboardError):
    """El candado no se libero a tiempo (mismo texto que Apps Script)."""

    code = "ERR_LOCK_TIMEOUT"
    expose_detail = True


@contextmanager
def script_lock(timeout_seconds: float) -> Iterator[None]:
    """
    Espera el candado como lock.waitLock(milisegundos).

    Args:
        timeout_seconds: Segundos maximos de espera.

    Raises:
        LockTimeoutError: Si el candado no se libera a tiempo.
    """
    if not _SCRIPT_LOCK.acquire(timeout=timeout_seconds):
        raise LockTimeoutError(LOCK_TIMEOUT_MESSAGE)

    try:
        yield
    finally:
        _SCRIPT_LOCK.release()
