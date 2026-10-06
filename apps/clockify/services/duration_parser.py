"""Conversion de duraciones de Clockify a horas."""

import re

from apps.clockify.exceptions import ClockifyRequestError

"""BKD.020.003 - Duraciones de Clockify
Equivale a _duracionClockifyAHoras(): acepta segundos o ISO 8601 (PT#H#M#S).
"""

SECONDS_PER_HOUR = 3600

MINUTES_PER_HOUR = 60

ISO_DURATION_PATTERN = re.compile(r"^PT")

HOURS_PATTERN = re.compile(r"(\d+)H")
MINUTES_PATTERN = re.compile(r"(\d+)M")
SECONDS_PATTERN = re.compile(r"(\d+)S")


def parse_duration_hours(raw_duration: object, entry_id: str) -> float:
    """
    Convierte la duracion de un registro de Clockify a horas.

    Args:
        raw_duration: Segundos (numero) o texto ISO 8601 como PT1H30M.
        entry_id: ID del registro, para el mensaje de error.

    Returns:
        La duracion en horas.

    Raises:
        ClockifyRequestError: Cuando la duracion no es valida; el
            original tampoco guardaba totales parciales.
    """
    if isinstance(raw_duration, bool):
        raise build_invalid_duration_error(entry_id)

    if isinstance(raw_duration, int | float):
        hours = float(raw_duration) / SECONDS_PER_HOUR
    elif isinstance(raw_duration, str) and ISO_DURATION_PATTERN.match(
        raw_duration,
    ):
        hours = (
            read_duration_part(HOURS_PATTERN, raw_duration)
            + read_duration_part(MINUTES_PATTERN, raw_duration)
            / MINUTES_PER_HOUR
            + read_duration_part(SECONDS_PATTERN, raw_duration)
            / SECONDS_PER_HOUR
        )
    else:
        raise build_invalid_duration_error(entry_id)

    if hours < 0:
        raise build_invalid_duration_error(entry_id)

    return hours


def read_duration_part(pattern: re.Pattern[str], text: str) -> float:
    """
    Lee una parte numerica de la duracion ISO 8601.

    Args:
        pattern: Expresion de la parte (horas, minutos o segundos).
        text: Duracion completa.

    Returns:
        El numero encontrado, o 0 si la parte no existe.
    """
    match = pattern.search(text)

    return float(match.group(1)) if match else 0.0


def build_invalid_duration_error(entry_id: str) -> ClockifyRequestError:
    """
    Construye el error de duracion invalida.

    Args:
        entry_id: ID del registro con la duracion invalida.

    Returns:
        La excepcion a lanzar.
    """
    return ClockifyRequestError(
        f"Clockify devolvio una duracion no valida en el registro "
        f"{entry_id}. No se guardo un total parcial.",
    )
