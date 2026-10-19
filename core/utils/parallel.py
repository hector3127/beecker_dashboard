"""Ejecucion en paralelo de consultas a APIs externas."""

import threading
from collections.abc import Callable, Sequence
from contextvars import copy_context

from django.db import connections

"""BKD.003.006 - Consultas en paralelo
Ejecuta varias consultas HTTP a la vez para reducir la primera carga.
Cada tarea debe crear su propio cliente HTTP: las conexiones no se
comparten entre hilos. Los hilos tambien pueden leer la base de datos:
cada uno usa su propia conexion y la cierra al terminar su trabajo (una
sola vez, no por tarea), para no dejar conexiones abiertas en PostgreSQL.
"""

_state = threading.local()


def is_pool_worker() -> bool:
    """Indica si el hilo actual es un hilo de map_in_parallel."""
    return bool(getattr(_state, "worker", False))


def map_in_parallel[ItemType, ResultType](
    task: Callable[[ItemType], ResultType],
    items: Sequence[ItemType],
    max_workers: int,
) -> list[ResultType]:
    """
    Aplica la tarea a cada elemento usando varios hilos.

    Todas las tareas se ejecutan aunque alguna falle; despues se lanza el
    error del primer elemento (en orden) que fallo.

    Args:
        task: Funcion que procesa un elemento.
        items: Elementos a procesar.
        max_workers: Cantidad maxima de hilos.

    Returns:
        Los resultados en el mismo orden que los elementos.
    """
    if len(items) <= 1 or max_workers <= 1:
        return [task(item) for item in items]

    contexts = [copy_context() for _ in items]
    results: list[ResultType | None] = [None] * len(items)
    errors: dict[int, BaseException] = {}
    pending = iter(range(len(items)))
    lock = threading.Lock()

    def work() -> None:
        _state.worker = True
        try:
            while True:
                with lock:
                    index = next(pending, None)
                if index is None:
                    return
                try:
                    results[index] = contexts[index].run(task, items[index])
                except BaseException as error:  # noqa: BLE001
                    errors[index] = error
        finally:
            _state.worker = False
            connections.close_all()

    threads = [
        threading.Thread(target=work)
        for _ in range(min(max_workers, len(items)))
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    if errors:
        raise errors[min(errors)]
    return results  # type: ignore[return-value]
