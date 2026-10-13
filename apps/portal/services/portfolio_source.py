"""Lectura de solo lectura del portafolio para las vistas nuevas."""

from datetime import datetime

from apps.dashboard.schemas.dashboard_models import ProjectMetrics
from apps.dashboard.services.delivery_managers import load_delivery_managers
from apps.dashboard.services.orchestrator import DASHBOARD_SHEETS
from apps.dashboard.services.portfolio_costs import calculate_portfolio_costs
from apps.dashboard.services.project_metrics import (
    build_project_metrics,
    calculate_burn_by_project,
)
from apps.dashboard.services.record_reader import (
    read_project_records,
    read_risk_records,
)
from apps.portal.constants import NO_DELIVERY_MANAGER
from apps.portal.schemas import ProjectView
from core.sheets import sheet_names
from core.sheets.protocols import SheetReader
from core.time_entries.protocols import TimeEntryProvider
from core.time_entries.resource_rates import load_costing_rate_by_resource
from core.utils.text import to_text

"""BKD.120.004 - Fuente de datos del portafolio
Reutiliza los calculos del dashboard (ProjectMetrics) pero solo LEE:
no guarda el snapshot de KPIs ni escribe en Sheets, Azure DevOps o
Clockify.
"""


def build_project_views(
    reader: SheetReader,
    time_entry_provider: TimeEntryProvider,
    now: datetime,
) -> tuple[ProjectView, ...]:
    """
    Calcula los indicadores de cada proyecto sin escribir nada.

    Args:
        reader: Repositorio de lectura de Sheets.
        time_entry_provider: Fuente de las horas registradas.
        now: Fecha y hora local actual.

    Returns:
        Un ProjectView por proyecto de la hoja Proyectos.
    """
    reader.prefetch(DASHBOARD_SHEETS)

    projects = read_project_records(reader)
    risks = read_risk_records(reader)
    time_entries = time_entry_provider.load_time_entries().entries

    costs = calculate_portfolio_costs(
        reader.read_as_objects(sheet_names.SHEET_RESOURCES),
        load_costing_rate_by_resource(reader),
        time_entries,
    )
    burn_by_project = calculate_burn_by_project(time_entries)
    manager_by_project = load_delivery_managers(reader)

    return tuple(
        to_project_view(
            build_project_metrics(project, burn_by_project, risks, costs, now),
            manager_by_project,
        )
        for project in projects
    )


def to_project_view(
    metric: ProjectMetrics,
    manager_by_project: dict[str, str],
) -> ProjectView:
    """
    Convierte los indicadores de un proyecto en su vista.

    Args:
        metric: Indicadores calculados por el dashboard.
        manager_by_project: Delivery Manager por ID de proyecto.

    Returns:
        El proyecto listo para las plantillas.
    """
    project = metric.project

    return ProjectView(
        project_id=project.project_id,
        name=to_text(project.display_name),
        client=to_text(project.client),
        delivery_manager=(
            manager_by_project.get(project.project_id) or NO_DELIVERY_MANAGER
        ),
        service=project.service,
        status_category=metric.status_category,
        health=metric.health,
        risk_level=metric.risk_level,
        progress_percent=metric.progress_percent,
        delay_days=metric.delay_days,
        budget_hours=metric.budget_hours,
        burn_hours=metric.burn_hours,
        etc_hours=metric.etc_hours,
    )
