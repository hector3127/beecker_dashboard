"""Conversiones numericas que replican el comportamiento de JavaScript."""

import math

from core.utils.cell_types import CellValue

"""BKD.003.001 - Utilidades numericas
Replica Math.round y Number() de Apps Script para que los KPIs en Python
den exactamente los mismos resultados que el sistema original.
"""


def round_half_up(value: float, decimals: int = 0) -> float:
    """
    Redondea igual que Math.round(value * 10^n) / 10^n en JavaScript.

    La funcion round() de Python usa redondeo bancario (2.5 -> 2) y
    JavaScript redondea los medios hacia arriba (2.5 -> 3, -2.5 -> -2).

    Args:
        value: Numero a redondear.
        decimals: Cantidad de decimales a conservar.

    Returns:
        El numero redondeado.
    """
    factor: float = 10.0**decimals

    return math.floor(value * factor + 0.5) / factor


def round_half_up_int(value: float) -> int:
    """
    Redondea a entero igual que Math.round() de JavaScript.

    Args:
        value: Numero a redondear.

    Returns:
        El entero mas cercano, con los medios redondeados hacia arriba.
    """
    return math.floor(value + 0.5)


def to_number(value: CellValue) -> float:
    """
    Convierte un valor de celda a numero como Number(x) || 0.

    Args:
        value: Valor leido de Google Sheets.

    Returns:
        El numero equivalente, o 0 cuando el valor no es numerico.
    """
    if isinstance(value, bool):
        return 1.0 if value else 0.0

    if isinstance(value, int | float):
        number = float(value)
    elif isinstance(value, str):
        number = parse_numeric_text(value)
    else:
        number = 0.0

    if math.isnan(number) or math.isinf(number):
        return 0.0

    return number


def parse_numeric_text(text: str) -> float:
    """
    Convierte un texto a numero sin aceptar separadores de miles.

    Args:
        text: Texto a convertir.

    Returns:
        El numero leido, o 0 cuando el texto no es un numero valido.
    """
    clean_text = text.strip()

    if not clean_text:
        return 0.0

    try:
        return float(clean_text)
    except ValueError:
        # Number("1,200") en JavaScript es NaN y el original lo trata
        # como cero; se conserva el mismo criterio.
        return 0.0
