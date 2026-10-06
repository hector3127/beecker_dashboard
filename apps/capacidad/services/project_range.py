"""Inicio y fin de un proyecto desde MPB o Azure DevOps."""

from collections.abc import Callable
from typing import Any, Protocol

from apps.capacidad.constants import MPB_ONLY_PREFIX
from apps.capacidad.exceptions import CapacityError
from apps.capacidad.services.azure_range import resolve_azure_range
from apps.capacidad.services.mpb_projects import (
    MpbProject,
    find_mpb_project,
)
from core.exceptions import DashboardError, describe_error

"""BKD.050.010 - Rango del proyecto
Equivale a capacidadInstaladaProyecto(id, iteration, forzar):
- Los proyectos AER/T&M usan INICIO y FIN de MPB.
- El resto usa las iteraciones de su Team Project en Azure DevOps.
Nunca lanza error: regresa ok False con el mensaje.
"""

JsonObject = dict[str, Any]


class AzureIterationSource(Protocol):
    """Acceso a los Team Projects y sus iteraciones."""

    def resolve_project(self, project_id: str) -> str:
        """Regresa el Team Project del ID, o cadena vacia."""
        ...

    def list_iterations(
        self,
        azure_project: str,
        force_refresh: bool,
    ) -> list[JsonObject]:
        """Regresa las iteraciones del Team Project en lista plana."""
        ...


def resolve_project_range(
    project_id: str,
    iteration_path: str,
    force_refresh: bool,
    load_mpb_projects: Callable[[], dict[str, MpbProject]],
    build_azure_source: Callable[[], AzureIterationSource],
) -> JsonObject:
    """
    Calcula inicio y fin del proyecto.

    Args:
        project_id: ID interno del proyecto.
        iteration_path: Iteration Path de Recursos; vacio si no hay.
        force_refresh: Ignora la cache de iteraciones.
        load_mpb_projects: Lee los proyectos de MPB.
        build_azure_source: Crea el acceso a Azure DevOps.

    Returns:
        {"ok": True, "inicio", "fin", ...} o {"ok": False, "error"}.
    """
    try:
        mpb_project = find_mpb_project(load_mpb_projects(), project_id)

        if mpb_project is not None:
            return {
                "ok": True,
                "idProyecto": project_id,
                "inicio": mpb_project.start,
                "fin": mpb_project.finish,
                "fuente": "MPB",
            }

        if MPB_ONLY_PREFIX.search(project_id):
            raise CapacityError(
                f"No se encontró el ID AER/TYM en MPB: {project_id}",
            )

        clean_id = project_id.strip()

        if not clean_id:
            raise CapacityError("Selecciona un proyecto.")

        azure_source = build_azure_source()
        azure_project = azure_source.resolve_project(clean_id)

        if not azure_project:
            raise CapacityError(
                "No se pudo resolver el Team Project de Azure para "
                f"{clean_id}.",
            )

        start, finish = resolve_azure_range(
            azure_source.list_iterations(azure_project, force_refresh),
            project_id,
            iteration_path,
        )
    except DashboardError as error:
        return {
            "ok": False,
            "idProyecto": project_id,
            "iteration": iteration_path,
            "error": describe_error(error),
        }

    return {
        "ok": True,
        "idProyecto": project_id,
        "iteration": iteration_path,
        "proyectoAzure": azure_project,
        "inicio": start,
        "fin": finish,
    }
