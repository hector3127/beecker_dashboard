"""Lectura de valores de la hoja MPB."""

import math
import re
from collections.abc import Sequence

from core.utils.cell_types import CellValue
from core.utils.dates import to_datetime
from core.utils.text import strip_accents, to_text

"""BKD.040.002 - Valores de MPB
Equivale a beeCuentaNormalizar_(), beeCuentaNumero_(), beeCuentaHoras_()
y beeCuentaFecha_() de DailyPanelService.gs.
"""

ISO_DATE_PREFIX = re.compile(r"^\d{4}-\d{2}-\d{2}")
DAY_MONTH_YEAR = re.compile(r"^(\d{1,2})/(\d{1,2})/(\d{4})$")
NUMBER_NOISE = re.compile(r"[%$h\s]", re.IGNORECASE)


def normalize_mpb(value: CellValue) -> str:
    """
    Normaliza texto: sin acentos, minusculas y espacios simples.

    Args:
        value: Valor de la celda.

    Returns:
        El texto normalizado.
    """
    lowered_text = strip_accents(to_text(value)).lower()

    return re.sub(r"\s+", " ", lowered_text).strip()


def parse_mpb_number(value: CellValue) -> float | None:
    """
    Lee un numero quitando comas, %, $, h y espacios.

    Args:
        value: Valor de la celda.

    Returns:
        El numero, o None si la celda no es numerica.
    """
    if isinstance(value, bool):
        return None

    if isinstance(value, int | float):
        number = float(value)
        return number if math.isfinite(number) else None

    cleaned_text = NUMBER_NOISE.sub("", to_text(value).replace(",", ""))

    if not cleaned_text:
        return None

    try:
        number = float(cleaned_text)
    except ValueError:
        # Texto no numerico: se trata como celda vacia, igual que el
        # original.
        return None

    return number if math.isfinite(number) else None


def parse_mpb_hours(value: CellValue) -> float:
    """
    Lee horas; una celda no numerica cuenta como cero.

    Args:
        value: Valor de la celda.

    Returns:
        Las horas.
    """
    hours = parse_mpb_number(value)

    return hours if hours is not None else 0.0


def parse_mpb_date(value: CellValue) -> str:
    """
    Convierte una fecha de MPB a texto YYYY-MM-DD.

    Args:
        value: Numero de serie de Sheets o texto de fecha.

    Returns:
        La fecha YYYY-MM-DD, o cadena vacia si no es fecha.
    """
    if isinstance(value, int | float) and not isinstance(value, bool):
        moment = to_datetime(value)
        return moment.strftime("%Y-%m-%d") if moment is not None else ""

    text = to_text(value).strip()

    if ISO_DATE_PREFIX.match(text):
        return text[:10]

    match = DAY_MONTH_YEAR.match(text)

    if not match:
        return ""

    day_text, month_text, year_text = match.groups()

    return f"{year_text}-{month_text.zfill(2)}-{day_text.zfill(2)}"


def read_cell(row: Sequence[CellValue], column_index: int) -> CellValue:
    """
    Lee una celda tolerando filas recortadas por la API.

    Args:
        row: Fila de valores.
        column_index: Indice de la columna.

    Returns:
        El valor de la celda, o cadena vacia si no existe.
    """
    if 0 <= column_index < len(row):
        return row[column_index]

    return ""
