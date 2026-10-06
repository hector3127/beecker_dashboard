"""Alta, edicion y baja de hitos adicionales en la hoja Proyectos."""

import re
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from apps.ejecutivo.services.additional_milestones import (
    ENTRY_SEPARATOR,
    FIRST_MILESTONE_COLUMN,
    NOTE_SEPARATOR,
    last_column_count,
    read_additional_milestones,
    read_cell,
)
from core.exceptions import InvalidRequestError
from core.sheets import sheet_names
from core.sheets.protocols import SheetReader, SheetWriter
from core.utils.cell_types import CellValue
from core.utils.dates import to_datetime
from core.utils.text import normalize_name, to_text

"""BKD.040.015 - Escritura de hitos adicionales
Equivale a guardarHitosAdicionalesLote(), editarHitoAdicional() y
eliminarHitoAdicional():
- Cada tipo de hito es una columna desde la L.
- Una celda guarda "dd/mm/aaaa::observacion" separados por " | ".
- Un tipo nuevo crea su columna al final.
"""

JsonObject = dict[str, Any]

JOINED_SEPARATOR = " | "
ISO_DAY = re.compile(r"(\d{4})-(\d{2})-(\d{2})")


@dataclass(frozen=True, slots=True)
class MilestoneCell:
    """Celda de un tipo de hito para un proyecto (base 1)."""

    row_number: int
    column_number: int


class MilestoneSheet:
    """Lee y escribe los hitos adicionales de la hoja Proyectos."""

    def __init__(self, reader: SheetReader, writer: SheetWriter) -> None:
        self._reader = reader
        self._writer = writer
        self._values = [
            list(row) for row in reader.read_values(sheet_names.SHEET_PROJECTS)
        ]

    def find_project_row(self, project_id: str) -> int:
        """
        Busca la fila del proyecto (base 1).

        Args:
            project_id: ID del proyecto, sin importar mayusculas.

        Returns:
            El numero de fila en la hoja.

        Raises:
            InvalidRequestError: Cuando falta la columna o el proyecto.
        """
        headers = self._values[0] if self._values else []
        id_key = normalize_name("ID_Proyecto")
        id_column = next(
            (
                index
                for index, header in enumerate(headers)
                if normalize_name(header) == id_key
            ),
            -1,
        )

        if id_column < 0:
            raise InvalidRequestError(
                'No se encontró la columna "ID_Proyecto" en Proyectos.',
            )

        wanted_id = project_id.strip().lower()

        for row_index, row in enumerate(self._values[1:], start=2):
            row_id = to_text(read_cell(row, id_column) or "").strip().lower()

            if row_id == wanted_id:
                return row_index

        raise InvalidRequestError(
            f'No se encontró el proyecto "{project_id}" en la hoja Proyectos.',
        )

    def find_type_column(self, milestone_type: str) -> int:
        """
        Busca la columna de un tipo de hito (base 1); -1 si no existe.

        Args:
            milestone_type: Tipo de hito.

        Returns:
            El numero de columna.
        """
        headers = self._values[0] if self._values else []
        wanted_type = milestone_type.strip().lower()

        for column_index in range(FIRST_MILESTONE_COLUMN, len(headers)):
            header = to_text(headers[column_index] or "").strip().lower()

            if header == wanted_type:
                return column_index + 1

        return -1

    def locate(self, project_id: str, milestone_type: str) -> MilestoneCell:
        """
        Ubica la celda de un tipo de hito, como _ubicarFilaColumnaHito().

        Args:
            project_id: ID del proyecto.
            milestone_type: Tipo de hito.

        Returns:
            La celda.

        Raises:
            InvalidRequestError: Cuando no existe el proyecto o el tipo.
        """
        row_number = self.find_project_row(project_id)
        column_number = self.find_type_column(milestone_type)

        if column_number < 0:
            raise InvalidRequestError(
                f'No se encontró el tipo de hito "{milestone_type}".',
            )

        return MilestoneCell(row_number, column_number)

    def read_entries(self, cell: MilestoneCell) -> list[str]:
        """
        Lee las entradas de una celda.

        Args:
            cell: Celda del hito.

        Returns:
            Las entradas "fecha::observacion".
        """
        return split_entries(self.read_text(cell))

    def read_text(self, cell: MilestoneCell) -> str:
        """
        Lee el texto de una celda.

        Args:
            cell: Celda del hito.

        Returns:
            El texto sin espacios externos.
        """
        row_index = cell.row_number - 1
        row = self._values[row_index] if row_index < len(self._values) else []

        return to_text(read_cell(row, cell.column_number - 1) or "").strip()

    def write(self, cell: MilestoneCell, value: CellValue) -> None:
        """
        Escribe una celda y conserva la copia local actualizada.

        Args:
            cell: Celda a escribir.
            value: Valor nuevo.
        """
        self._writer.write_cell(
            sheet_names.SHEET_PROJECTS,
            cell.row_number,
            cell.column_number,
            value,
        )

        while len(self._values) < cell.row_number:
            self._values.append([])

        row = self._values[cell.row_number - 1]

        while len(row) < cell.column_number:
            row.append("")

        row[cell.column_number - 1] = value

    def milestones(self, project_id: str) -> list[JsonObject]:
        """
        Lee los hitos del proyecto con los cambios ya aplicados.

        Args:
            project_id: ID del proyecto.

        Returns:
            Los hitos adicionales del proyecto.
        """
        return read_additional_milestones(self._values, project_id)

    @property
    def values(self) -> list[list[CellValue]]:
        """Copia local de la hoja Proyectos."""
        return self._values


def split_entries(cell_text: str) -> list[str]:
    """
    Separa las entradas de una celda.

    Args:
        cell_text: Texto de la celda.

    Returns:
        Las entradas no vacias.
    """
    return [
        entry.strip()
        for entry in cell_text.split(ENTRY_SEPARATOR)
        if entry.strip()
    ]


def build_entry(date_value: object, note: object) -> str:
    """
    Arma la entrada "dd/mm/aaaa::observacion".

    Args:
        date_value: Fecha del frontend (YYYY-MM-DD del input date).
        note: Observacion.

    Returns:
        La entrada lista para guardar.
    """
    clean_note = (
        to_text(note if isinstance(note, str) else "")
        .replace(ENTRY_SEPARATOR, "/")
        .replace(NOTE_SEPARATOR, ":")
        .strip()
    )

    return f"{format_milestone_date(date_value)}{NOTE_SEPARATOR}{clean_note}"


def format_milestone_date(date_value: object) -> str:
    """
    Convierte la fecha del input a dd/mm/aaaa.

    El dia elegido se guarda tal cual; el original lo convertia desde
    medianoche UTC y en Mexico guardaba el dia anterior.

    Args:
        date_value: Fecha enviada por el frontend.

    Returns:
        La fecha dd/mm/aaaa, o el texto original si no es fecha.
    """
    text = date_value if isinstance(date_value, str) else to_text(None)
    iso_match = ISO_DAY.fullmatch(text.strip())

    if iso_match:
        year, month, day = iso_match.groups()
        return f"{day}/{month}/{year}"

    moment = to_datetime(text) if text else None

    return moment.strftime("%d/%m/%Y") if moment is not None else text


def read_index(index: object, entries: Sequence[str], action: str) -> int:
    """
    Valida el indice de la entrada.

    Args:
        index: Indice recibido.
        entries: Entradas de la celda.
        action: editar o eliminar, para el mensaje.

    Returns:
        El indice como entero.

    Raises:
        InvalidRequestError: Cuando el indice no existe.
    """
    if isinstance(index, bool) or not isinstance(index, int | float):
        position = -1
    else:
        position = int(index) if index == int(index) else -1

    if not 0 <= position < len(entries):
        raise InvalidRequestError(
            f"No se encontró la entrada a {action} (índice fuera de rango).",
        )

    return position


def edit_milestone(
    sheet: MilestoneSheet,
    request: tuple[str, str, object],
    date_value: object,
    note: object,
) -> list[JsonObject]:
    """
    Reemplaza la fecha y observacion de una entrada.

    Args:
        sheet: Hoja Proyectos.
        request: ID del proyecto, tipo e indice de la entrada.
        date_value: Fecha nueva.
        note: Observacion nueva.

    Returns:
        Los hitos actualizados.
    """
    project_id, milestone_type, index = request
    cell = sheet.locate(project_id, milestone_type)
    entries = sheet.read_entries(cell)
    entries[read_index(index, entries, "editar")] = build_entry(
        date_value, note
    )
    sheet.write(cell, JOINED_SEPARATOR.join(entries))

    return sheet.milestones(project_id)


def delete_milestone(
    sheet: MilestoneSheet,
    project_id: str,
    milestone_type: str,
    index: object,
) -> list[JsonObject]:
    """
    Elimina una entrada de un tipo de hito.

    Args:
        sheet: Hoja Proyectos.
        project_id: ID del proyecto.
        milestone_type: Tipo de hito.
        index: Indice de la entrada.

    Returns:
        Los hitos actualizados.
    """
    cell = sheet.locate(project_id, milestone_type)
    entries = sheet.read_entries(cell)
    del entries[read_index(index, entries, "eliminar")]
    sheet.write(cell, JOINED_SEPARATOR.join(entries))

    return sheet.milestones(project_id)


def save_milestones(
    sheet: MilestoneSheet,
    project_id: str,
    new_milestones: Sequence[object],
) -> list[JsonObject]:
    """
    Agrega varios hitos; crea la columna del tipo si no existe.

    Args:
        sheet: Hoja Proyectos.
        project_id: ID del proyecto.
        new_milestones: Lista de {tipo, fechaISO, observacion}.

    Returns:
        Los hitos actualizados.

    Raises:
        InvalidRequestError: Cuando faltan datos o el proyecto.
    """
    if not project_id:
        raise InvalidRequestError("Falta el ID de proyecto.")

    if not new_milestones:
        raise InvalidRequestError("No hay hitos para guardar.")

    row_number = sheet.find_project_row(project_id)
    last_column = max(
        last_column_count(sheet.values),
        FIRST_MILESTONE_COLUMN,
    )

    for item in new_milestones:
        milestone = item if isinstance(item, dict) else {}
        milestone_type = to_text(
            milestone.get("tipo")
            if isinstance(milestone.get("tipo"), str)
            else "",
        ).strip()

        if not milestone_type:
            continue

        column_number = sheet.find_type_column(milestone_type)

        if column_number < 0:
            column_number = max(FIRST_MILESTONE_COLUMN + 1, last_column + 1)
            sheet.write(MilestoneCell(1, column_number), milestone_type)
            last_column = column_number

        cell = MilestoneCell(row_number, column_number)
        current_text = sheet.read_text(cell)
        new_entry = build_entry(
            milestone.get("fechaISO"),
            milestone.get("observacion"),
        )
        sheet.write(
            cell,
            f"{current_text}{JOINED_SEPARATOR}{new_entry}"
            if current_text
            else new_entry,
        )

    return sheet.milestones(project_id)
