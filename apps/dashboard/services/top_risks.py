"""Lista de riesgos abiertos mas importantes del portafolio."""

from collections.abc import Collection, Sequence

from apps.dashboard.constants import (
    IMPACT_ORDER,
    RISK_STATUS_OPEN,
    TOP_RISKS_LIMIT,
)
from apps.dashboard.schemas.records import ProjectRecord, RiskRecord
from core.utils.cell_types import CellValue

"""BKD.010.014 - Top riesgos
Ordena los riesgos abiertos por impacto (Alto primero) y conserva los
15 primeros.
"""


def build_top_risks(
    risks: Sequence[RiskRecord],
    projects: Sequence[ProjectRecord],
    project_ids: Collection[str],
) -> list[dict[str, CellValue]]:
    """
    Construye la lista de riesgos para la tarjeta Top riesgos.

    Args:
        risks: Riesgos de la hoja Riesgos.
        projects: Todos los proyectos, para resolver nombres.
        project_ids: IDs de los proyectos filtrados.

    Returns:
        Riesgos con descripcion, impacto y nombre del proyecto.
    """
    name_by_project_id = {
        project.project_id: project.display_name for project in projects
    }
    open_risks = [
        risk
        for risk in risks
        if risk.status == RISK_STATUS_OPEN and risk.project_id in project_ids
    ]
    open_risks.sort(
        key=lambda risk: IMPACT_ORDER.get(risk.impact, 0),
        reverse=True,
    )

    return [
        {
            "descripcion": risk.description,
            "impacto": risk.impact,
            "proyecto": name_by_project_id.get(
                risk.project_id,
                risk.project_id,
            ),
        }
        for risk in open_risks[:TOP_RISKS_LIMIT]
    ]
