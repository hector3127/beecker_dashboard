"""Reintentos para las llamadas a Clockify de la sincronizacion."""

import time
from collections.abc import Callable

from apps.clockify.exceptions import ClockifyRequestError

"""BKD.130.015 - Reintentos de la sincronizacion
La API de reportes de Clockify tiene picos intermitentes (respuestas de 30 s
o conexiones cortadas). Una tarea programada no debe fallar el dia por un
corte de unos segundos: las fallas de conexion se reintentan con espera
creciente. Una respuesta con codigo HTTP (403, 500...) no se reintenta aqui:
es una respuesta de Clockify, no una falla de conexion.
"""

ATTEMPTS = 3
WAIT_SECONDS = (5, 20)
# Fallas de conexion seguidas tras las cuales se deja de insistir en lo
# opcional (la verificacion de totales): Clockify no esta respondiendo.
MAX_CONSECUTIVE_FAILURES = 3


def with_retries[ResultType](
    call: Callable[[], ResultType],
    sleep: Callable[[float], None] = time.sleep,
) -> ResultType:
    """
    Ejecuta la llamada y la repite si fallo la conexion con Clockify.

    Args:
        call: Llamada a Clockify.
        sleep: Espera entre intentos (se cambia en las pruebas).

    Returns:
        El resultado de la llamada.

    Raises:
        ClockifyRequestError: Cuando la conexion sigue fallando tras los
            intentos, o cuando Clockify responde con un codigo de error.
    """
    for attempt in range(ATTEMPTS):
        try:
            return call()
        except ClockifyRequestError as error:
            if error.status_code or attempt == ATTEMPTS - 1:
                raise
            sleep(WAIT_SECONDS[min(attempt, len(WAIT_SECONDS) - 1)])
    raise AssertionError("inalcanzable")  # pragma: no cover
