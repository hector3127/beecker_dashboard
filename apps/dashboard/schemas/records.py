"""Registros de las hojas Proyectos, Riesgos y Sprints."""

from dataclasses import dataclass
from datetime import datetime

from core.utils.cell_types import CellValue, SheetRow
from core.utils.dates import to_datetime
from core.utils.numbers import to_number
from core.utils.text import get_flexible_value, text_or_default, to_text

"""BKD.010.002 - Registros del dashboard
Convierte las filas de Sheets en objetos con tipos claros para que los
calculos no dependan de los nombres de columna.
"""


@dataclass(frozen=True, slots=True)
class ProjectRecord:
    """Fila de la hoja Proyectos."""

    project_id: str
    display_name: CellValue
    client: CellValue
    status: CellValue
    service: str
    budget_hours: float
    start_date: datetime | None
    end_date: datetime | None


@dataclass(frozen=True, slots=True)
class RiskRecord:
    """Fila de la hoja Riesgos."""

    project_id: str
    impact: str
    status: str
    description: CellValue


@dataclass(frozen=True, slots=True)
class SprintRecord:
    """Fila de la hoja Sprints."""

    project_id: str
    status: str
    velocity: float


def build_project_record(row: SheetRow) -> ProjectRecord:
    """
    Convierte una fila de Proyectos.

    Args:
        row: Fila de la hoja Proyectos.

    Returns:
        El registro del proyecto.
    """
    project_id = to_text(row.get("ID_Proyecto"))

    return ProjectRecord(
        project_id=project_id,
        display_name=text_or_default(row.get("Nombre"), project_id),
        client=row.get("Cliente", ""),
        status=row.get("Estado", ""),
        service=to_text(
            get_flexible_value(row, ["Servicio", "Service"]),
        ).strip(),
        budget_hours=to_number(row.get("Budget_Hrs")),
        start_date=to_datetime(row.get("Fecha_Inicio")),
        end_date=to_datetime(row.get("Fecha_Fin_Estimada")),
    )


def build_risk_record(row: SheetRow) -> RiskRecord:
    """
    Convierte una fila de Riesgos.

    Args:
        row: Fila de la hoja Riesgos.

    Returns:
        El registro del riesgo.
    """
    return RiskRecord(
        project_id=to_text(row.get("ID_Proyecto")),
        impact=to_text(row.get("Impacto")),
        status=to_text(row.get("Estado")),
        description=text_or_default(row.get("Descripcion"), ""),
    )


def build_sprint_record(row: SheetRow) -> SprintRecord:
    """
    Convierte una fila de Sprints.

    Args:
        row: Fila de la hoja Sprints.

    Returns:
        El registro del sprint.
    """
    return SprintRecord(
        project_id=to_text(row.get("ID_Proyecto")),
        status=to_text(row.get("Estado")),
        velocity=to_number(row.get("Velocity")),
    )
