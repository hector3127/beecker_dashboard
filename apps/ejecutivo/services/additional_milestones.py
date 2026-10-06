"""Hitos adicionales guardados en la hoja Proyectos (columna L en adelante)."""

from collections.abc import Sequence
from typing import Any

from core.utils.cell_types import CellValue
from core.utils.text import normalize_name, to_text

"""BKD.040.012 - Hitos adicionales
Equivale a obtenerHitosAdicionales(): cada encabezado desde la columna L
es un tipo de hito y cada celda guarda "fecha::observacion" separados
por "|".
"""

JsonObject = dict[str, Any]

FIRST_MILESTONE_COLUMN = 11  # Columna L en base 0.
ENTRY_SEPARATOR = "|"
NOTE_SEPARATOR = "::"


def read_additional_milestones(
    project_values: Sequence[Sequence[CellValue]],
    project_id: str,
) -> list[JsonObject]:
    """
    Lee los hitos adicionales de un proyecto.

    Args:
        project_values: Celdas de la hoja Proyectos.
        project_id: ID del proyecto (sin importar espacios ni
            mayusculas).

    Returns:
        Los hitos con tipo, indice, fecha y observacion.
    """
    if not project_values:
        return []

    headers = list(project_values[0])
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
        return []

    wanted_id = project_id.strip().lower()
    project_row = next(
        (
            row
            for row in project_values[1:]
            if to_text(read_cell(row, id_column) or "").strip().lower()
            == wanted_id
        ),
        None,
    )

    if project_row is None:
        return []

    milestones: list[JsonObject] = []

    for column_index in range(FIRST_MILESTONE_COLUMN, len(headers)):
        milestone_type = to_text(headers[column_index] or "").strip()
        cell_text = to_text(read_cell(project_row, column_index) or "").strip()

        if not milestone_type or not cell_text:
            continue

        entries = [
            entry.strip()
            for entry in cell_text.split(ENTRY_SEPARATOR)
            if entry.strip()
        ]

        for entry_index, entry in enumerate(entries):
            parts = entry.split(NOTE_SEPARATOR)
            milestones.append(
                {
                    "tipo": milestone_type,
                    "indice": entry_index,
                    "fecha": parts[0].strip(),
                    "observacion": parts[1].strip() if len(parts) > 1 else "",
                },
            )

    return milestones


def read_cell(row: Sequence[CellValue], column_index: int) -> CellValue:
    """
    Lee una celda tolerando filas recortadas por la API.

    Args:
        row: Fila de valores.
        column_index: Columna en base 0.

    Returns:
        El valor, o None si la fila es mas corta.
    """
    return row[column_index] if column_index < len(row) else None


def list_milestone_types(
    project_values: Sequence[Sequence[CellValue]],
) -> list[str]:
    """
    Lista los tipos de hito (encabezados desde la columna L).

    Equivale a obtenerTiposHitosExistentes().

    Args:
        project_values: Celdas de la hoja Proyectos.

    Returns:
        Los encabezados no vacios.
    """
    if not project_values:
        return []

    return [
        header_text
        for header in project_values[0][FIRST_MILESTONE_COLUMN:]
        if (header_text := to_text(header or "").strip())
    ]


def last_column_count(project_values: Sequence[Sequence[CellValue]]) -> int:
    """
    Ultima columna con datos en la hoja, como sheet.getLastColumn().

    Args:
        project_values: Celdas de la hoja Proyectos.

    Returns:
        El numero de columnas usadas.
    """
    return max((len(row) for row in project_values), default=0)
