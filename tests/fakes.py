"""Dobles de prueba para Sheets y fuentes de horas."""

from collections.abc import Iterable, Mapping, Sequence
from datetime import datetime

from core.exceptions import SheetNotFoundError
from core.time_entries.models import TimeEntryBatch
from core.utils.cell_types import CellValue, SheetRow
from core.utils.text import to_text


class InMemorySheetRepository:
    """Repositorio en memoria con la misma interfaz que el real."""

    def __init__(self, sheets: dict[str, list[list[CellValue]]]) -> None:
        self.sheets = sheets
        self.appended_rows: list[tuple[str, list[object]]] = []
        self.replaced_rows: list[tuple[str, int, int]] = []

    def sheet_exists(self, sheet_name: str) -> bool:
        return sheet_name in self.sheets

    def prefetch(self, sheet_names: Iterable[str]) -> None:
        return None

    def list_sheet_names(self) -> list[str]:
        return list(self.sheets)

    def read_previews(
        self,
        sheet_names: Sequence[str],
        row_count: int,
        column_count: int,
    ) -> dict[str, list[list[CellValue]]]:
        previews = {}

        for name in sheet_names:
            if name not in self.sheets:
                continue

            rows = [
                list(row[:column_count])
                for row in self.sheets[name][:row_count]
            ]

            for row in rows:
                while row and row[-1] in ("", None):
                    row.pop()

            while rows and not rows[-1]:
                rows.pop()

            previews[name] = rows

        return previews

    def read_values(self, sheet_name: str) -> list[list[CellValue]]:
        if sheet_name not in self.sheets:
            raise SheetNotFoundError(f"Hoja no encontrada: {sheet_name}")

        return self.sheets[sheet_name]

    def read_as_objects(self, sheet_name: str) -> list[SheetRow]:
        values = self.read_values(sheet_name)

        if len(values) < 2:
            return []

        headers = [to_text(header) for header in values[0]]

        return [
            {
                header: row[index] if index < len(row) else ""
                for index, header in enumerate(headers)
            }
            for row in values[1:]
            if any(cell not in ("", None) for cell in row)
        ]

    def ensure_sheet(self, sheet_name: str, headers: Sequence[str]) -> bool:
        if sheet_name in self.sheets:
            return False

        self.sheets[sheet_name] = [list(headers)]
        return True

    def append_row(
        self,
        sheet_name: str,
        values: Sequence[CellValue | datetime],
    ) -> None:
        self.appended_rows.append((sheet_name, list(values)))
        self.sheets[sheet_name].append(list(values))

    def upsert_row(
        self,
        sheet_name: str,
        id_column: str,
        data: Mapping[str, CellValue | datetime],
    ) -> None:
        rows = self.sheets[sheet_name]
        headers = [to_text(header) for header in rows[0]]
        id_index = headers.index(id_column)
        values = [data.get(header, "") for header in headers]

        for row_index, row in enumerate(rows[1:], start=1):
            if id_index < len(row) and row[id_index] == data.get(id_column):
                rows[row_index] = list(values)
                return

        self.append_row(sheet_name, values)

    def write_cell(
        self,
        sheet_name: str,
        row_number: int,
        column_number: int,
        value: CellValue,
    ) -> None:
        rows = self.sheets[sheet_name]

        while len(rows) < row_number:
            rows.append([])

        row = rows[row_number - 1]

        while len(row) < column_number:
            row.append("")

        row[column_number - 1] = value

    def write_row(
        self,
        sheet_name: str,
        row_number: int,
        values: Sequence[CellValue | datetime],
    ) -> None:
        rows = self.sheets[sheet_name]

        while len(rows) < row_number:
            rows.append([])

        row = rows[row_number - 1]

        while len(row) < len(values):
            row.append("")

        row[: len(values)] = list(values)

    def replace_rows(
        self,
        sheet_name: str,
        first_row: int,
        rows: Sequence[Sequence[CellValue | datetime]],
        text_columns: Sequence[int] = (),
    ) -> None:
        if sheet_name not in self.sheets:
            raise SheetNotFoundError(f"Hoja no encontrada: {sheet_name}")

        kept = self.sheets[sheet_name][: first_row - 1]
        self.sheets[sheet_name] = kept + [list(row) for row in rows]
        self.replaced_rows.append((sheet_name, first_row, len(rows)))

    def insert_column_after(self, sheet_name: str, column_number: int) -> None:
        if sheet_name not in self.sheets:
            raise SheetNotFoundError(f"Hoja no encontrada: {sheet_name}")

        for row in self.sheets[sheet_name]:
            while len(row) < column_number:
                row.append("")

            row.insert(column_number, "")

    def write_text_cells(
        self,
        sheet_name: str,
        cells: Sequence[tuple[int, int, str]],
    ) -> None:
        for row_number, column_number, text in cells:
            self.write_cell(sheet_name, row_number, column_number, text)

    def delete_sheet(self, sheet_name: str) -> None:
        if sheet_name not in self.sheets:
            raise SheetNotFoundError(f"Hoja no encontrada: {sheet_name}")

        del self.sheets[sheet_name]

    def delete_row_range(
        self,
        sheet_name: str,
        first_row: int,
        row_count: int,
    ) -> None:
        del self.sheets[sheet_name][first_row - 1 : first_row - 1 + row_count]

    def delete_row(self, sheet_name: str, row_number: int) -> None:
        del self.sheets[sheet_name][row_number - 1]


class StaticTimeEntryProvider:
    """Fuente de horas que regresa un lote fijo."""

    def __init__(self, batch: TimeEntryBatch) -> None:
        self.batch = batch

    def load_time_entries(self) -> TimeEntryBatch:
        return self.batch
