"""Costo estimado, costo real y margen por proyecto."""

from collections.abc import Mapping, Sequence

from apps.dashboard.schemas.dashboard_models import PortfolioCosts
from core.time_entries.models import TimeEntry
from core.utils.cell_types import SheetRow
from core.utils.numbers import round_half_up_int, to_number
from core.utils.text import get_flexible_value, normalize_name, to_text

"""BKD.010.007 - Costos del portafolio
Equivale a calcularCostosPortafolio() y margenProyecto().
Margen = (costo estimado - costo real) / costo estimado * 100.
"""

PROJECT_COLUMNS = ("Proyecto",)

RESOURCE_NAME_COLUMNS = (
    "Nombre del recurso",
    "Nombre_del_recurso",
    "Recurso",
    "Nombre",
)

ESTIMATED_HOURS_COLUMNS = (
    "Horas Estimadas",
    "Horas_Estimadas",
    "HorasEstimadas",
)


def calculate_portfolio_costs(
    assignment_rows: Sequence[SheetRow],
    costing_rate_by_resource: Mapping[str, float],
    time_entries: Sequence[TimeEntry],
) -> PortfolioCosts:
    """
    Calcula el costo estimado y real de todos los proyectos.

    Args:
        assignment_rows: Filas de la hoja Recursos (asignaciones).
        costing_rate_by_resource: Nombre normalizado -> costing rate.
        time_entries: Registros de tiempo del portafolio.

    Returns:
        Los costos por proyecto.
    """
    estimated_cost_by_project: dict[str, float] = {}

    for assignment_row in assignment_rows:
        project_id = to_text(
            get_flexible_value(assignment_row, PROJECT_COLUMNS)
        )

        if not project_id:
            continue

        resource_name = get_flexible_value(
            assignment_row,
            RESOURCE_NAME_COLUMNS,
        )
        estimated_hours = to_number(
            get_flexible_value(assignment_row, ESTIMATED_HOURS_COLUMNS),
        )
        costing_rate = costing_rate_by_resource.get(
            normalize_name(resource_name),
            0.0,
        )
        estimated_cost_by_project[project_id] = (
            estimated_cost_by_project.get(project_id, 0.0)
            + estimated_hours * costing_rate
        )

    actual_cost_by_project: dict[str, float] = {}

    for time_entry in time_entries:
        if not time_entry.is_billable or not time_entry.project_id:
            continue

        actual_cost_by_project[time_entry.project_id] = (
            actual_cost_by_project.get(time_entry.project_id, 0.0)
            + time_entry.duration_hours * time_entry.costing_rate
        )

    return PortfolioCosts(
        estimated_cost_by_project=estimated_cost_by_project,
        actual_cost_by_project=actual_cost_by_project,
    )


def calculate_project_margin(
    project_id: str,
    costs: PortfolioCosts,
) -> float | None:
    """
    Calcula el margen porcentual de un proyecto con un decimal.

    Args:
        project_id: ID del proyecto.
        costs: Costos del portafolio.

    Returns:
        El margen; None cuando no hay costo estimado para comparar.
    """
    estimated_cost = costs.estimated_cost_by_project.get(project_id, 0.0)
    actual_cost = costs.actual_cost_by_project.get(project_id, 0.0)

    if not estimated_cost:
        return None

    margin_ratio = (estimated_cost - actual_cost) / estimated_cost

    return round_half_up_int(margin_ratio * 1000) / 10
