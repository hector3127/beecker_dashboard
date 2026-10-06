"""Lectura de hojas con encabezados en cualquiera de las primeras filas."""

from collections.abc import Sequence
from dataclasses import dataclass

from apps.capacidad.constants import HEADER_SEARCH_ROWS
from apps.capacidad.exceptions import CapacityError
from apps.capacidad.services.capacity_text import normalize_capacity_text
from core.sheets.protocols import SheetReader
from core.utils.cell_types import CellValue

"""BKD.050.005 - Tablas de Capacidad instalada
Equivale a ciTabla_() y ciCampo_(): ubica la fila de encabezados en las
primeras 20 filas y lee columnas por cualquiera de sus alias.
"""

SheetValues = list[list[CellValue]]


@dataclass(frozen=True, slots=True)
class SheetTable:
    """Encabezados, filas de datos y posicion de la fila de encabezados."""

    headers: list[CellValue]
    rows: SheetValues
    header_index: int

    def read_field(
        self,
        row: Sequence[CellValue],
        aliases: Sequence[str],
    ) -> CellValue:
        """
        Lee la primera columna cuyo encabezado coincide con un alias.

        Args:
            row: Fila de datos.
            aliases: Nombres posibles de la columna.

        Returns:
            El valor de la celda; cadena vacia si la columna no existe.
        """
        column_index = self.find_column(aliases)

        if column_index < 0:
            return ""

        return read_cell(row, column_index)

    def find_column(self, aliases: Sequence[str]) -> int:
        """
        Busca la primera columna (de izquierda a derecha) de los alias.

        Args:
            aliases: Nombres posibles de la columna.

        Returns:
            El indice de la columna, o -1 si no existe.
        """
        keys = {normalize_capacity_text(alias) for alias in aliases}

        for column_index, header in enumerate(self.headers):
            if normalize_capacity_text(header) in keys:
                return column_index

        return -1


def read_sheet_table(
    reader: SheetReader,
    sheet_name: str,
    required_columns: Sequence[Sequence[str]],
) -> SheetTable:
    """
    Lee una hoja y ubica su fila de encabezados, como ciTabla_().

    Args:
        reader: Repositorio de lectura de Sheets.
        sheet_name: Nombre de la hoja.
        required_columns: Por cada columna obligatoria, sus alias ya
            normalizados.

    Returns:
        La tabla con encabezados y filas de datos.

    Raises:
        CapacityError: Cuando la hoja o los encabezados no existen.
    """
    if not reader.sheet_exists(sheet_name):
        raise CapacityError(f"No existe la hoja {sheet_name}.")

    values = reader.read_values(sheet_name)

    for row_index, row in enumerate(values[:HEADER_SEARCH_ROWS]):
        normalized_row = {normalize_capacity_text(cell) for cell in row}

        if all(
            any(alias in normalized_row for alias in aliases)
            for aliases in required_columns
        ):
            first_data_row = row_index + 1

            return SheetTable(
                headers=list(row),
                rows=values[first_data_row:],
                header_index=row_index,
            )

    raise CapacityError(f"No se reconocen los encabezados de {sheet_name}.")


def read_cell(row: Sequence[CellValue], column_index: int) -> CellValue:
    """
    Lee una celda; las filas cortas de la API se completan con None.

    Args:
        row: Fila de valores.
        column_index: Columna en base 0.

    Returns:
        El valor, o None si la fila no llega a esa columna.
    """
    return row[column_index] if column_index < len(row) else None
