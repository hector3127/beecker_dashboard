"""Hojas manuales del dashboard AER (planeacion, riesgos, cliente...)."""

import uuid
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any

from apps.aer.constants import (
    DATE_COLUMNS,
    MANUAL_SHEETS,
    MAX_EFFORT,
    SHEET_DATE_COLUMNS,
)
from apps.aer.services.aer_values import clamp, date_iso, sheet_date, text
from core.sheets.protocols import SheetReader, SheetWriter
from core.utils.cell_types import CellValue
from core.utils.dates import to_local_naive

"""BKD.080.004 - Hojas manuales AER
Equivale a _aertymEnsureManualSheet(), _aertymReadManual(),
_aertymUpsertManual() y _aertymDeleteManual(): cada registro es una fila
con UID y las columnas de MANUAL_SHEETS; las columnas que faltan se
agregan al final de los encabezados.
"""

JsonObject = dict[str, Any]
Row = dict[str, Any]


@dataclass(slots=True)
class AerStore:
    """Lector, escritor, reloj y generador de UID de las hojas AER."""

    reader: SheetReader
    writer: SheetWriter
    now: datetime
    new_uid: Callable[[], str] = field(default=lambda: str(uuid.uuid4()))
    ensured: bool = False

    def local_now(self) -> datetime:
        """Fecha y hora actual en la zona del script."""
        return to_local_naive(self.now) if self.now.tzinfo else self.now

    def today(self) -> date:
        """Hoy en la zona del script."""
        return self.local_now().date()

    def now_text(self) -> str:
        """yyyy-MM-dd HH:mm:ss (_aertymAhoraTexto)."""
        return self.local_now().strftime("%Y-%m-%d %H:%M:%S")

    def values(self, sheet_name: str) -> list[list[CellValue]]:
        """Celdas de la hoja (vacio si no existe)."""
        if not self.reader.sheet_exists(sheet_name):
            return []

        return [list(row) for row in self.reader.read_values(sheet_name)]

    def ensure_sheets(self) -> None:
        """Crea las hojas y agrega los encabezados que falten."""
        if self.ensured:
            return

        self.reader.prefetch(list(MANUAL_SHEETS))

        for name, headers in MANUAL_SHEETS.items():
            self.ensure_sheet(name, headers)

        self.ensured = True

    def ensure_sheet(self, name: str, headers: tuple[str, ...]) -> None:
        """Una hoja manual (_aertymEnsureManualSheet)."""
        values = self.values(name)
        width = max((len(row) for row in values), default=0)

        if not values or not width:
            self.writer.ensure_sheet(name, headers)
            return

        current = [text(cell) for cell in pad(values[0], width)]
        missing = [header for header in headers if header not in current]

        for offset, header in enumerate(missing):
            self.writer.write_cell(name, 1, len(current) + offset + 1, header)

    def headers(self, name: str) -> list[str]:
        """Encabezados actuales de la hoja (todas sus columnas)."""
        values = self.values(name)
        width = max((len(row) for row in values), default=0)

        return [text(cell) for cell in pad(values[0], width)] if values else []

    def read(self, name: str) -> list[Row]:
        """
        Filas como objetos con _row (_aertymReadManual).

        Las fechas de la hoja llegan como numero de serie y se convierten a
        datetime, como los Date que entregaba getValues().
        """
        self.ensure_sheets()
        values = self.values(name)

        if len(values) < 2:
            return []

        width = max(len(row) for row in values)
        headers = [text(cell) for cell in pad(values[0], width)]
        rows: list[Row] = []

        for number, raw in enumerate(values[1:], start=2):
            row: Row = {"_row": number}

            for header, cell_value in zip(
                headers, pad(raw, width), strict=True
            ):
                row[header] = (
                    sheet_date(cell_value)
                    if header in SHEET_DATE_COLUMNS
                    else cell_value
                )

            rows.append(row)

        return rows

    def upsert(self, name: str, payload: dict[str, Any]) -> str:
        """
        Actualiza la fila del UID o agrega una nueva (_aertymUpsertManual).

        Args:
            name: Hoja manual.
            payload: Valores por encabezado (se agregan UID y Actualizado).

        Returns:
            El UID guardado.
        """
        self.ensure_sheets()
        headers = self.headers(name)
        uid = text(payload.get("UID")) or self.new_uid()
        payload["UID"] = uid
        payload["Actualizado"] = self.now_text()
        values = self.values(name)
        target = 0

        if len(values) >= 2 and "UID" in headers:
            uid_index = headers.index("UID")
            target = next(
                (
                    number
                    for number, row in enumerate(values[1:], start=2)
                    if display_text(cell_at(row, uid_index)) == uid
                ),
                0,
            )

        row = [row_value(header, payload.get(header)) for header in headers]

        if target:
            self.writer.write_row(name, target, row)
        else:
            self.writer.append_row(name, row)

        return uid

    def delete(self, name: str, uid: object) -> bool:
        """
        Borra la fila del UID (_aertymDeleteManual).

        Returns:
            True si se encontro y se borro.
        """
        values = self.values(name)

        if len(values) < 2:
            return False

        headers = [display_text(cell) for cell in values[0]]

        if "UID" not in headers:
            return False

        uid_index = headers.index("UID")
        wanted = text(uid)
        target = next(
            (
                number
                for number, row in enumerate(values[1:], start=2)
                if display_text(cell_at(row, uid_index)).strip() == wanted
            ),
            0,
        )

        if not target:
            return False

        self.writer.delete_row(name, target)

        return True

    def delete_rows(self, name: str, row_numbers: list[int]) -> None:
        """Borra filas de abajo hacia arriba."""
        for number in sorted(set(row_numbers), reverse=True):
            self.writer.delete_row(name, number)


def pad(row: list[CellValue], width: int) -> list[CellValue]:
    """Fila con celdas vacias hasta el ancho de la hoja."""
    return list(row) + [""] * (width - len(row))


def cell_at(row: list[CellValue], index: int) -> CellValue:
    """Celda de la fila o vacia."""
    return row[index] if 0 <= index < len(row) else ""


def display_text(value: CellValue) -> str:
    """Texto visible de una celda de texto (getDisplayValues)."""
    return text(value)


def row_value(header: str, value: object) -> Any:
    """Valor a escribir: fechas YYYY-MM-DD, avance y esfuerzo acotados."""
    if header in DATE_COLUMNS:
        value = date_iso(value)

    if header == "Avance":
        value = clamp(value, 0, 100)

    if header == "Orden":
        value = clamp(value, 0, MAX_EFFORT)

    return "" if value is None else value


def project_rows(store: AerStore, name: str, project: str) -> list[Row]:
    """Filas de la hoja manual que son del proyecto."""
    return [
        row
        for row in store.read(name)
        if text(row.get("ID_Proyecto")) == project
    ]


def copy_row(row: Mapping[str, Any]) -> dict[str, Any]:
    """Copia de la fila sin _row."""
    return {key: value for key, value in row.items() if key != "_row"}
