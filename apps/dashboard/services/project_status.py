"""Categoria de estado y nivel de riesgo de cada proyecto."""

from collections.abc import Sequence

from apps.dashboard.constants import (
    CATEGORY_ACTIVE,
    RISK_HIGH,
    RISK_LOW,
    RISK_MEDIUM,
    RISK_STATUS_OPEN,
    STATUS_CATEGORY_BY_STATUS,
)
from apps.dashboard.schemas.records import RiskRecord
from core.utils.cell_types import CellValue
from core.utils.text import to_text

"""BKD.010.005 - Estado y riesgo del proyecto
Equivale a categoriaEstadoProyecto() y nivelRiesgoProyecto().
"""


def categorize_project_status(status: CellValue) -> str:
    """
    Convierte el Estado de la hoja a la categoria del dashboard.

    Args:
        status: Valor de la columna Estado.

    Returns:
        Activo, En Pausa, Planificacion o Cerrado. Un valor no
        reconocido se cuenta como Activo, igual que el original.
    """
    normalized_status = to_text(status).strip().lower()

    return STATUS_CATEGORY_BY_STATUS.get(normalized_status, CATEGORY_ACTIVE)


def calculate_project_risk_level(
    project_id: str,
    risks: Sequence[RiskRecord],
) -> str:
    """
    Calcula el nivel de riesgo a partir de los riesgos abiertos.

    Args:
        project_id: ID del proyecto.
        risks: Todos los riesgos de la hoja Riesgos.

    Returns:
        Alto, Medio o Bajo segun el peor riesgo abierto, o cadena
        vacia si el proyecto no tiene riesgos abiertos.
    """
    open_impacts = [
        risk.impact
        for risk in risks
        if risk.project_id == project_id and risk.status == RISK_STATUS_OPEN
    ]

    if RISK_HIGH in open_impacts:
        return RISK_HIGH

    if RISK_MEDIUM in open_impacts:
        return RISK_MEDIUM

    if open_impacts:
        return RISK_LOW

    return ""
