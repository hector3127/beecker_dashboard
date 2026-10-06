"""Ejecucion en paralelo de consultas a APIs externas."""

from collections.abc import Callable, Sequence
from concurrent.futures import ThreadPoolExecutor

"""BKD.003.006 - Consultas en paralelo
Ejecuta varias consultas HTTP a la vez para reducir la primera carga.
Cada tarea debe crear su propio cliente HTTP: las conexiones no se
comparten entre hilos.
"""


def map_in_parallel[ItemType, ResultType](
    task: Callable[[ItemType], ResultType],
    items: Sequence[ItemType],
    max_workers: int,
) -> list[ResultType]:
    """
    Aplica la tarea a cada elemento usando varios hilos.

    Args:
        task: Funcion que procesa un elemento.
        items: Elementos a procesar.
        max_workers: Cantidad maxima de hilos.

    Returns:
        Los resultados en el mismo orden que los elementos.
    """
    if len(items) <= 1 or max_workers <= 1:
        return [task(item) for item in items]

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        return list(executor.map(task, items))
