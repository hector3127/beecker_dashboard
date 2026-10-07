"""Lectura de celdas y fechas de las hojas de GSE."""

import math
from collections.abc import Sequence
from datetime import datetime

from apps.capacidad.services.capacity_text import normalize_capacity_text
from apps.gse.constants import ISO_DATE, LOCAL_DATE
from core.utils.cell_types import CellValue
from core.utils.dates import to_datetime
from core.utils.js_values import js_or_text

"""BKD.100.004 - Celdas de GSE
Equivale a gseNorm_() y gseBaseFecha_(); ademas lee celdas que pueden
faltar al final de una fila, como row[i] de JavaScript.
"""

# Numeros de serie de Sheets entre el 2000-01-01 y el 2100-12-31.
MIN_DATE_SERIAL = 36_526
MAX_DATE_SERIAL = 73_415

SheetValues = list[list[CellValue]]


def norm(value: CellValue) -> str:
    """
    Normaliza un texto como gseNorm_().

    Args:
        value: Valor de la celda.

    Returns:
        Texto sin acentos, en minusculas y sin signos.
    """
    return normalize_capacity_text(value)


def cell_at(row: Sequence[CellValue], index: int) -> CellValue:
    """
    Lee la celda de una columna; None si la fila es mas corta.

    Args:
        row: Fila de la hoja.
        index: Posicion de la columna (-1 si la columna no existe).

    Returns:
        El valor, o None cuando no hay celda.
    """
    if 0 <= index < len(row):
        return row[index]

    return None


def trimmed(value: CellValue) -> str:
    """
    Texto sin espacios laterales, como String(x || '').trim().

    Args:
        value: Valor de la celda.

    Returns:
        El texto; vacio si la celda esta vacia o vale cero.
    """
    return js_or_text(value).strip()


def find_header(headers: Sequence[str], names: Sequence[str]) -> int:
    """
    Busca el primer encabezado entre varios nombres, en orden.

    Args:
        headers: Encabezados ya normalizados.
        names: Nombres a intentar; el primero que exista gana.

    Returns:
        La posicion de la columna, o -1 si ninguno existe.
    """
    for name in names:
        if name in headers:
            return headers.index(name)

    return -1


def format_base_date(value: CellValue | datetime) -> str:
    """
    Convierte la fecha de la base a YYYY-MM-DD como gseBaseFecha_().

    Args:
        value: Numero de serie, fecha ISO o dd/MM/yyyy.

    Returns:
        La fecha ISO, o cadena vacia si no se reconoce.
    """
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d")

    if isinstance(value, int | float) and not isinstance(value, bool):
        return format_serial_date(float(value))

    text = trimmed(value)
    iso_match = ISO_DATE.match(text)

    if iso_match:
        return iso_match.group(1)

    local_match = LOCAL_DATE.match(text)

    if not local_match:
        return ""

    day, month, year = local_match.groups()

    return f"{year}-{month.zfill(2)}-{day.zfill(2)}"


def format_serial_date(serial: float) -> str:
    """Fecha ISO de un numero de serie de Sheets; vacio si no es fecha."""
    if not math.isfinite(serial):
        return ""

    if not MIN_DATE_SERIAL <= serial <= MAX_DATE_SERIAL:
        return ""

    moment = to_datetime(serial)

    return moment.strftime("%Y-%m-%d") if moment else ""
