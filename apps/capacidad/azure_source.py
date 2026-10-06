"""Iteraciones de Azure DevOps para Capacidad instalada."""

from typing import Any

from apps.azure_devops.exceptions import AzureDevOpsConfigurationError
from apps.azure_devops.gateway import AzureDevOpsGateway
from apps.azure_devops.services.project_resolver import resolve_azure_project
from apps.capacidad.exceptions import CapacityError

"""BKD.050.012 - Azure para Capacidad instalada
Equivale a ixsRaidContexto_() y a la lectura del arbol de iteraciones de
capacidadInstaladaProyecto(), usando la cache compartida de Azure.
"""

JsonObject = dict[str, Any]


class GatewayIterationSource:
    """Resuelve Team Projects y lee sus iteraciones con cache."""

    def __init__(self) -> None:
        try:
            self._gateway = AzureDevOpsGateway()
        except AzureDevOpsConfigurationError as error:
            raise CapacityError(
                "Conecta Azure DevOps desde Configuración.",
            ) from error

    def resolve_project(self, project_id: str) -> str:
        """
        Busca el Team Project de un ID interno.

        Args:
            project_id: ID interno del proyecto.

        Returns:
            El Team Project, o cadena vacia si no hay coincidencia.
        """
        return resolve_azure_project(
            project_id,
            self._gateway.list_project_names(),
        )

    def list_iterations(
        self,
        azure_project: str,
        force_refresh: bool,
    ) -> list[JsonObject]:
        """
        Lee las iteraciones del Team Project.

        Args:
            azure_project: Nombre del Team Project.
            force_refresh: Ignora la cache.

        Returns:
            Las iteraciones en lista plana.
        """
        return self._gateway.list_iterations(
            azure_project,
            force_refresh=force_refresh,
        )
