"""Contratos de lectura y escritura sobre Google Sheets."""

from collections.abc import Iterable, Mapping, Sequence
from datetime import datetime
from typing import Protocol

from core.utils.cell_types import CellValue, SheetRow

"""BKD.004.003 - Contratos de acceso a Sheets
Permite que los servicios de negocio dependan de una interfaz y no del
cliente de Google, lo que facilita las pruebas unitarias.
"""


class SheetReader(Protocol):
    """Operaciones de lectura que necesitan los servicios de negocio."""

    def sheet_exists(self, sheet_name: str) -> bool:
        """Indica si la hoja existe en el Spreadsheet."""
        ...

    def prefetch(self, sheet_names: Iterable[str]) -> None:
        """Precarga varias hojas en una sola llamada."""
        ...

    def list_sheet_names(self) -> list[str]:
        """Nombres de las hojas en el orden de las pestanas."""
        ...

    def read_previews(
        self,
        sheet_names: Sequence[str],
        row_count: int,
        column_count: int,
    ) -> dict[str, list[list[CellValue]]]:
        """Inicio de varias hojas (filas y columnas desde A1)."""
        ...

    def read_values(self, sheet_name: str) -> list[list[CellValue]]:
        """Lee todas las celdas de la hoja como matriz."""
        ...

    def read_as_objects(self, sheet_name: str) -> list[SheetRow]:
        """Lee la hoja como lista de diccionarios por encabezado."""
        ...


class SheetWriter(Protocol):
    """Operaciones de escritura que necesitan los servicios de negocio."""

    def ensure_sheet(
        self,
        sheet_name: str,
        headers: Sequence[str],
    ) -> bool:
        """Crea la hoja con encabezados si todavia no existe."""
        ...

    def append_row(
        self,
        sheet_name: str,
        values: Sequence[CellValue | datetime],
    ) -> None:
        """Agrega una fila al final de la hoja."""
        ...

    def upsert_row(
        self,
        sheet_name: str,
        id_column: str,
        data: Mapping[str, CellValue | datetime],
    ) -> None:
        """Actualiza la fila con el mismo ID o la agrega si no existe."""
        ...

    def write_cell(
        self,
        sheet_name: str,
        row_number: int,
        column_number: int,
        value: CellValue,
    ) -> None:
        """Escribe una sola celda (fila y columna en base 1)."""
        ...

    def write_row(
        self,
        sheet_name: str,
        row_number: int,
        values: Sequence[CellValue | datetime],
    ) -> None:
        """Escribe una fila desde la columna A (fila en base 1)."""
        ...

    def replace_rows(
        self,
        sheet_name: str,
        first_row: int,
        rows: Sequence[Sequence[CellValue | datetime]],
        text_columns: Sequence[int] = (),
    ) -> None:
        """Reemplaza todo lo que hay desde una fila (base 1)."""
        ...

    def insert_column_after(
        self,
        sheet_name: str,
        column_number: int,
    ) -> None:
        """Inserta una columna vacia despues de la columna dada."""
        ...

    def write_text_cells(
        self,
        sheet_name: str,
        cells: Sequence[tuple[int, int, str]],
    ) -> None:
        """Escribe celdas (fila, columna, texto) como texto plano."""
        ...

    def delete_sheet(self, sheet_name: str) -> None:
        """Elimina una hoja completa."""
        ...

    def delete_row_range(
        self,
        sheet_name: str,
        first_row: int,
        row_count: int,
    ) -> None:
        """Elimina varias filas seguidas (base 1)."""
        ...

    def delete_row(self, sheet_name: str, row_number: int) -> None:
        """Elimina una fila completa (base 1)."""
        ...
