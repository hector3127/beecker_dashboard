"""Filtros de proyectos y catalogo de filtros disponibles."""

from collections.abc import Sequence

from apps.dashboard.constants import ALL_CLIENTS_LABEL
from apps.dashboard.schemas.dashboard_filters import DashboardFilters
from apps.dashboard.schemas.records import ProjectRecord
from core.utils.cell_types import CellValue
from core.utils.text import is_truthy, text_or_default, to_text

"""BKD.010.016 - Filtros del dashboard
Equivale a aplicarFiltros() y getFiltrosDisponibles() de Codigo.gs.
"""


def apply_filters(
    projects: Sequence[ProjectRecord],
    filters: DashboardFilters,
) -> list[ProjectRecord]:
    """
    Filtra los proyectos por ID y cliente.

    Args:
        projects: Todos los proyectos.
        filters: Filtros solicitados.

    Returns:
        Los proyectos que cumplen los filtros.
    """
    return [
        project
        for project in projects
        if (not filters.project_id or project.project_id == filters.project_id)
        and (not filters.client or to_text(project.client) == filters.client)
    ]


def build_available_filters(
    projects: Sequence[ProjectRecord],
) -> dict[str, list[CellValue] | list[dict[str, CellValue]]]:
    """
    Construye las opciones de los selectores de proyecto y cliente.

    Args:
        projects: Todos los proyectos de la hoja Proyectos.

    Returns:
        {"proyectos": [...], "clientes": [...]} como el original.
    """
    seen_ids: set[str] = set()
    project_options: list[dict[str, CellValue]] = []

    for project in projects:
        project_id = project.project_id.strip()

        if not project_id or project_id in seen_ids:
            continue

        seen_ids.add(project_id)
        project_options.append(
            {
                "id": project_id,
                "nombre": build_option_name(project, project_id),
                "cliente": text_or_default(project.client, ""),
                "servicio": project.service,
                "estado": text_or_default(project.status, ""),
            },
        )

    unique_clients = {
        to_text(project.client): project.client
        for project in projects
        if is_truthy(project.client)
    }
    client_options: list[CellValue] = [ALL_CLIENTS_LABEL]
    client_options.extend(
        unique_clients[client_key] for client_key in sorted(unique_clients)
    )

    return {
        "proyectos": project_options,
        "clientes": client_options,
    }


def build_option_name(project: ProjectRecord, clean_id: str) -> CellValue:
    """
    Elige el nombre visible del proyecto en el selector.

    Args:
        project: Registro del proyecto.
        clean_id: ID del proyecto sin espacios externos.

    Returns:
        El nombre del proyecto, o el ID limpio si no tiene nombre.
    """
    if to_text(project.display_name) == project.project_id:
        return clean_id

    return project.display_name
