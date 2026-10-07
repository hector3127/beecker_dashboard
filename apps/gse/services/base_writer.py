"""Guardado de las horas de Clockify en la base de GSE."""

import json
from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Protocol

from apps.gse.constants import (
    BASE_HEADER_TITLES,
    CONTROL_HEADERS,
    CONTROL_SHEET,
)
from apps.gse.exceptions import GseError
from apps.gse.services.base_store import (
    Connection,
    HourRecord,
    base_sheet_title,
    check_base_schema,
    find_base_sheet,
    unique_ids,
)
from apps.gse.services.cells import SheetValues, cell_at, format_base_date
from core.sheets.protocols import SheetReader, SheetWriter
from core.utils.cell_types import CellValue
from core.utils.locks import LockTimeoutError, script_lock
from core.utils.text import to_text

"""BKD.100.014 - Guardado de la base de GSE
Equivale a gseBaseGuardar_(), gseBaseSheet_() y gseBaseControl_():
reemplaza en 08.Base Clockify AAAA los registros del mes y la conexion
y anota la cobertura en GSE_Base_Control. Antes de borrar nada marca la
cobertura anterior como incompleta, asi una falla a medias nunca queda
como mes completo.
"""

LOCK_SECONDS = 10
LOCK_MESSAGE = "La base está siendo actualizada; reintenta."


class SheetStore(SheetReader, SheetWriter, Protocol):
    """Hojas que se pueden leer y escribir."""


class BaseWriter:
    """Guarda en Sheets los registros de un mes de Clockify."""

    def __init__(
        self,
        sheets: SheetStore,
        connection: Connection,
        now: datetime,
    ) -> None:
        """
        Crea el escritor de la base.

        Args:
            sheets: Repositorio de Sheets con lectura y escritura.
            connection: Conexion activa de Clockify.
            now: Momento actual con zona horaria.
        """
        self._sheets = sheets
        self._connection = connection
        self._now = now

    def save_month(
        self,
        month: str,
        records: Sequence[HourRecord],
        user_ids: Sequence[str] | None,
    ) -> None:
        """
        Guarda los registros del mes y marca su cobertura.

        Args:
            month: Mes YYYY-MM.
            records: Registros descargados de Clockify.
            user_ids: IDs por los que se filtro; None si fueron todos.

        Raises:
            GseError: Cuando otro proceso guarda a la vez o la hoja de la
                base tiene otro formato.
        """
        try:
            with script_lock(LOCK_SECONDS):
                self._save(month, records, unique_ids(user_ids))
        except LockTimeoutError as error:
            raise GseError(LOCK_MESSAGE) from error

    def _save(
        self,
        month: str,
        records: Sequence[HourRecord],
        ids: list[str] | None,
    ) -> None:
        """Reemplaza los datos del mes y escribe la cobertura."""
        sheet_name = self._ensure_base_sheet(month[:4])
        values = self._sheets.read_values(sheet_name)
        headers = check_base_schema(sheet_name, values)
        self._sheets.ensure_sheet(CONTROL_SHEET, CONTROL_HEADERS)
        control = self._sheets.read_values(CONTROL_SHEET)
        ids_text = json.dumps(ids, separators=(",", ":"), ensure_ascii=False)
        scope = f"{self._connection.key}|{month}|{ids_text}"
        saved_at = format_timestamp(self._now)
        old_index = next(
            (
                index
                for index, row in enumerate(control)
                if index > 0 and cell_at(row, 0) == scope
            ),
            -1,
        )

        if old_index > 0:
            self._sheets.write_cell(CONTROL_SHEET, old_index + 1, 4, "")

        combined = self._keep_rows(values, headers, month, ids) + [
            self._build_row(record, headers, saved_at) for record in records
        ]
        self._sheets.replace_rows(
            sheet_name,
            2,
            combined,
            text_columns=[headers.index("start date") + 1],
        )
        self._clear_overlapping(control, month, scope)
        row_number = old_index + 1 if old_index > 0 else len(control) + 1
        self._sheets.write_text_cells(
            CONTROL_SHEET,
            [
                (row_number, 1, scope),
                (row_number, 2, month),
                (row_number, 3, ids_text),
                (row_number, 4, saved_at),
            ],
        )
        self._sheets.write_cell(CONTROL_SHEET, row_number, 5, len(records))

    def _ensure_base_sheet(self, year: str) -> str:
        """Nombre de la hoja de la base; la crea con encabezados si falta."""
        existing = find_base_sheet(self._sheets, year)

        if existing is not None:
            return existing

        title = base_sheet_title(year)
        self._sheets.ensure_sheet(title, BASE_HEADER_TITLES)

        return title

    def _keep_rows(
        self,
        values: SheetValues,
        headers: list[str],
        month: str,
        ids: list[str] | None,
    ) -> list[list[CellValue]]:
        """Filas que no se reemplazan: otra conexion, mes o personas."""
        connection_column = headers.index("conexion gse")
        date_column = headers.index("start date")
        id_column = headers.index("id clockify")
        kept: list[list[CellValue]] = []

        for row in values[1:]:
            replaced = (
                to_text(cell_at(row, connection_column)) == self._connection.key
                and format_base_date(cell_at(row, date_column)).startswith(
                    month,
                )
                and (ids is None or to_text(cell_at(row, id_column)) in ids)
            )

            if not replaced:
                kept.append(pad_row(row, len(headers)))

        return kept

    def _build_row(
        self,
        record: HourRecord,
        headers: list[str],
        saved_at: str,
    ) -> list[CellValue]:
        """Fila de la base de un registro, segun el orden de columnas."""
        row: list[CellValue] = [""] * len(headers)
        fields: dict[str, CellValue] = {
            "project": record.project,
            "user": record.resource,
            "start date": record.day,
            "duration decimal": record.hours,
            "task": record.task,
            "tags": ", ".join(record.tags),
            "billable": "Yes" if record.billable else "No",
            "id registro": record.record_id,
            "id clockify": record.user_id,
            "workspace": self._connection.workspace,
            "conexion gse": self._connection.key,
            "actualizado": saved_at,
        }

        for name, value in fields.items():
            row[headers.index(name)] = value

        return row

    def _clear_overlapping(
        self,
        control: SheetValues,
        month: str,
        scope: str,
    ) -> None:
        """Invalida otras coberturas del mes con registros que ya no valen."""
        prefix = f"{self._connection.key}|{month}|"

        for index, row in enumerate(control[1:], 2):
            key = cell_at(row, 0)

            if to_text(key).startswith(prefix) and key != scope:
                self._sheets.write_cell(CONTROL_SHEET, index, 4, "")


def pad_row(row: Sequence[CellValue], width: int) -> list[CellValue]:
    """Fila con al menos width celdas (la API omite las vacias finales)."""
    padded = list(row)

    while len(padded) < width:
        padded.append("")

    return padded


def format_timestamp(moment: datetime) -> str:
    """Momento en UTC como toISOString(): 2026-10-02T18:00:00.000Z."""
    utc = moment.astimezone(UTC)

    return f"{utc:%Y-%m-%dT%H:%M:%S}.{utc.microsecond // 1000:03d}Z"
