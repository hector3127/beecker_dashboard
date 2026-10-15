"""Personas, areas y bandas de la hoja Bandas/rol."""

from collections.abc import Sequence
from dataclasses import dataclass, field

from apps.capacidad.constants import MONTH_NAMES
from apps.gse.constants import HEADER_SEARCH_ROWS, SHEET_ROSTER
from apps.gse.exceptions import GseError
from apps.gse.services.cells import (
    SheetValues,
    cell_at,
    find_header,
    norm,
    trimmed,
)
from core.sheets.protocols import SheetReader
from core.utils.cell_types import CellValue

"""BKD.100.006 - Personas de GSE
Lee Bandas/rol: area, banda del mes e ID de Clockify por encabezado.
"""

BAND_ALIASES_TAIL = "banda"


@dataclass(frozen=True, slots=True)
class Person:
    """Persona de Bandas/rol con su area, banda e ID de Clockify."""

    name: str
    area: str
    baja: bool
    clockify_id: str
    band: str
    row: Sequence[CellValue] = field(default=(), repr=False)


@dataclass(frozen=True, slots=True)
class RosterSheet:
    """Hoja Bandas/rol con su fila de encabezados."""

    rows: SheetValues
    header_index: int
    headers: list[str]

    @property
    def data_rows(self) -> SheetValues:
        """Filas despues de los encabezados."""
        return self.rows[self.header_index + 1 :]

    @property
    def role_column(self) -> int:
        """Posicion del encabezado ROL, independiente del orden del Sheet."""
        return self.headers.index("rol")


def read_roster_sheet(
    reader: SheetReader,
    error_text: str,
) -> RosterSheet:
    """
    Lee Bandas/rol y ubica la fila con Nombre y ROL.

    Args:
        reader: Repositorio de Sheets.
        error_text: Mensaje si no hay fila de encabezados.

    Returns:
        La hoja con sus encabezados normalizados.

    Raises:
        GseError: Cuando la hoja o sus encabezados faltan.
    """
    if not reader.sheet_exists(SHEET_ROSTER):
        raise GseError("Falta Bandas/rol.")

    rows = reader.read_values(SHEET_ROSTER)
    header_index = find_header_row(rows)

    if header_index < 0:
        raise GseError(error_text)

    headers = [norm(value) for value in rows[header_index]]

    return RosterSheet(rows, header_index, headers)


def find_header_row(rows: SheetValues) -> int:
    """Fila (en las primeras 20) con Nombre y ROL; -1 si no existe."""
    for index, row in enumerate(rows[:HEADER_SEARCH_ROWS]):
        norms = [norm(value) for value in row]

        if "nombre" not in norms or "rol" not in norms:
            continue

        return index

    return -1


def list_areas(reader: SheetReader) -> list[str]:
    """
    Areas unicas de la columna con encabezado ROL, ordenadas.

    Args:
        reader: Repositorio de Sheets.

    Returns:
        Los nombres de area sin repetir.

    Raises:
        GseError: Cuando falta la hoja o el encabezado ROL.
    """
    sheet = read_roster_sheet(reader, "Bandas/rol requiere Nombre y ROL.")
    unique: dict[str, str] = {}

    for row in sheet.data_rows:
        value = trimmed(cell_at(row, sheet.role_column))
        key = norm(value)

        if key and key not in unique:
            unique[key] = value

    return sorted(unique.values())


def find_band_column(
    headers: Sequence[str],
    month_index: int,
    year: str,
) -> int:
    """
    Columna de la banda del mes (enero 2026, 2026 01, enero o banda).

    Args:
        headers: Encabezados normalizados.
        month_index: Mes de 1 a 12.
        year: Ano en texto.

    Returns:
        La posicion de la columna, o -1 si no hay.
    """
    names = [norm(f"{year}-{month_index:02d}"), BAND_ALIASES_TAIL]

    if 1 <= month_index <= len(MONTH_NAMES):
        month = MONTH_NAMES[month_index - 1]
        names = [f"{month} {year}", names[0], month, BAND_ALIASES_TAIL]

    return find_header(headers, names)


def read_clockify_id(headers: Sequence[str], row: Sequence[CellValue]) -> str:
    """ID Clockify de la fila; vacio si no hay columna."""
    index = headers.index("id clockify") if "id clockify" in headers else -1

    return trimmed(cell_at(row, index))
