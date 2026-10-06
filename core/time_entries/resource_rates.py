"""Tarifa de costo por recurso a partir de las hojas de bandas."""

from collections.abc import Sequence

from core.sheets import sheet_names
from core.sheets.protocols import SheetReader
from core.utils.cell_types import CellValue
from core.utils.numbers import to_number
from core.utils.text import normalize_name, to_text

"""BKD.005.005 - Tarifas por recurso
Equivale a leerBandaYCostingRatePorRecurso(): cruza "Banda salarial"
(nombre -> banda) con "Master rates" (banda -> costing rate).
"""

NAME_COLUMN_INDEX = 0
BAND_COLUMN_INDEX = 1
RATE_BAND_COLUMN_INDEX = 0
COSTING_RATE_COLUMN_INDEX = 3


def load_costing_rate_by_resource(reader: SheetReader) -> dict[str, float]:
    """
    Calcula el costing rate de cada recurso.

    Args:
        reader: Repositorio de lectura de Sheets.

    Returns:
        Nombre normalizado -> costing rate. Las hojas que no existen se
        tratan como vacias, igual que el original.
    """
    band_by_name = read_band_by_name(
        read_optional_values(reader, sheet_names.SHEET_SALARY_BANDS),
    )
    rate_by_band = read_rate_by_band(
        read_optional_values(reader, sheet_names.SHEET_MASTER_RATES),
    )

    return {
        normalized_name: rate_by_band.get(normalize_band(band), 0.0)
        for normalized_name, band in band_by_name.items()
    }


def load_band_info_by_resource(
    reader: SheetReader,
) -> dict[str, tuple[CellValue, float]]:
    """
    Lee la banda y el costing rate de cada recurso.

    Equivale a leerBandaYCostingRatePorRecurso().

    Args:
        reader: Repositorio de lectura de Sheets.

    Returns:
        Nombre normalizado -> (banda tal como esta en la hoja, rate).
    """
    band_by_name = read_band_by_name(
        read_optional_values(reader, sheet_names.SHEET_SALARY_BANDS),
    )
    rate_by_band = read_rate_by_band(
        read_optional_values(reader, sheet_names.SHEET_MASTER_RATES),
    )

    return {
        normalized_name: (band, rate_by_band.get(normalize_band(band), 0.0))
        for normalized_name, band in band_by_name.items()
    }


def read_optional_values(
    reader: SheetReader,
    sheet_name: str,
) -> list[list[CellValue]]:
    """
    Lee una hoja que puede no existir.

    Args:
        reader: Repositorio de lectura de Sheets.
        sheet_name: Nombre de la hoja.

    Returns:
        Las celdas de la hoja, o lista vacia si no existe.
    """
    if not reader.sheet_exists(sheet_name):
        return []

    return reader.read_values(sheet_name)


def read_band_by_name(
    values: Sequence[Sequence[CellValue]],
) -> dict[str, CellValue]:
    """
    Lee la hoja Banda salarial: columna A nombre, columna B banda.

    Args:
        values: Celdas de la hoja, con encabezados en la fila 1.

    Returns:
        Nombre normalizado -> banda.
    """
    band_by_name: dict[str, CellValue] = {}

    for row in values[1:]:
        resource_name = read_cell(row, NAME_COLUMN_INDEX)

        if resource_name:
            band_by_name[normalize_name(resource_name)] = read_cell(
                row,
                BAND_COLUMN_INDEX,
            )

    return band_by_name


def read_rate_by_band(
    values: Sequence[Sequence[CellValue]],
) -> dict[str, float]:
    """
    Lee la hoja Master rates: columna A banda, columna D costing rate.

    Args:
        values: Celdas de la hoja, con encabezados en la fila 1.

    Returns:
        Banda normalizada -> costing rate.
    """
    rate_by_band: dict[str, float] = {}

    for row in values[1:]:
        band = read_cell(row, RATE_BAND_COLUMN_INDEX)

        if band:
            rate_by_band[normalize_band(band)] = to_number(
                read_cell(row, COSTING_RATE_COLUMN_INDEX),
            )

    return rate_by_band


def normalize_band(band: CellValue) -> str:
    """
    Normaliza una banda como String(banda).trim().toUpperCase().

    Args:
        band: Valor de la banda.

    Returns:
        La banda en mayusculas y sin espacios externos.
    """
    return to_text(band).strip().upper()


def read_cell(row: Sequence[CellValue], column_index: int) -> CellValue:
    """
    Lee una celda tolerando filas recortadas por la API.

    Args:
        row: Fila de valores.
        column_index: Indice de la columna.

    Returns:
        El valor de la celda, o cadena vacia si no existe.
    """
    if column_index < len(row):
        return row[column_index]

    return ""
