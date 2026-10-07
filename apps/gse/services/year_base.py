"""Lectura de un ano completo desde la base en Sheets."""

import math
import time
from collections.abc import Callable
from datetime import date
from typing import Any

from apps.gse.constants import MAX_YEAR, MIN_YEAR
from apps.gse.services.month_report import (
    SOURCE_SHEET,
    GseContext,
    get_month,
)
from core.utils.js_values import js_number

"""BKD.100.009 - Ano de GSE desde la base
Equivale a gseObtenerAnoBase(): consulta cada mes transcurrido del ano
con la base en Sheets, sin llamar a Clockify.
"""

JsonObject = dict[str, Any]

MILLISECONDS = 1000


def parse_year(value: object) -> int | None:
    """
    Convierte el ano recibido como Number.isInteger() de JavaScript.

    Args:
        value: Ano recibido del frontend.

    Returns:
        El ano entero entre 2000 y 2100; None si no es valido.
    """
    number = js_number(value)

    if not math.isfinite(number) or number != int(number):
        return None

    year = int(number)

    return year if MIN_YEAR <= year <= MAX_YEAR else None


def get_year(
    context: GseContext,
    request: tuple[object, object],
    today: date,
    clock: Callable[[], float] = time.monotonic,
) -> JsonObject:
    """
    Lee del ano todos los meses transcurridos desde la base en Sheets.

    Args:
        context: Hojas, base y fuente de Clockify.
        request: Ano y area elegida (vacio para todas).
        today: Fecha local de hoy.
        clock: Reloj en segundos, para medir la duracion.

    Returns:
        {"ok", "data": {mes: resultado}, "milliseconds"} o
        {"ok": False, "error"}.
    """
    started = clock()
    year = parse_year(request[0])

    if year is None:
        return {"ok": False, "error": "Año inválido."}

    data = {
        f"{year}-{month:02d}": get_month(
            context,
            (f"{year}-{month:02d}", SOURCE_SHEET, False, request[1]),
        )
        for month in range(1, last_month(year, today) + 1)
    }

    return {
        "ok": True,
        "data": data,
        "milliseconds": round((clock() - started) * MILLISECONDS),
    }


def last_month(year: int, today: date) -> int:
    """Ultimo mes a consultar: 12 en anos pasados, el actual en este."""
    if year < today.year:
        return 12

    return today.month if year == today.year else 0
