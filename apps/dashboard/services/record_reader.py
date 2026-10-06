"""Lectura de las hojas Proyectos, Riesgos y Sprints como registros."""

from apps.dashboard.schemas.records import (
    ProjectRecord,
    RiskRecord,
    SprintRecord,
    build_project_record,
    build_risk_record,
    build_sprint_record,
)
from core.sheets import sheet_names
from core.sheets.protocols import SheetReader

"""BKD.010.019 - Lectura de registros
Convierte las hojas que usa el dashboard en registros tipados.
"""


def read_project_records(reader: SheetReader) -> list[ProjectRecord]:
    """
    Lee la hoja Proyectos.

    Args:
        reader: Repositorio de lectura de Sheets.

    Returns:
        Los proyectos de la hoja.
    """
    rows = reader.read_as_objects(sheet_names.SHEET_PROJECTS)

    return [build_project_record(row) for row in rows]


def read_risk_records(reader: SheetReader) -> list[RiskRecord]:
    """
    Lee la hoja Riesgos.

    Args:
        reader: Repositorio de lectura de Sheets.

    Returns:
        Los riesgos de la hoja.
    """
    rows = reader.read_as_objects(sheet_names.SHEET_RISKS)

    return [build_risk_record(row) for row in rows]


def read_sprint_records(reader: SheetReader) -> list[SprintRecord]:
    """
    Lee la hoja Sprints.

    Args:
        reader: Repositorio de lectura de Sheets.

    Returns:
        Los sprints de la hoja.
    """
    rows = reader.read_as_objects(sheet_names.SHEET_SPRINTS)

    return [build_sprint_record(row) for row in rows]
