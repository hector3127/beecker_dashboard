"""Acceso a Azure DevOps con la configuracion y la cache de Django."""

import hashlib
import logging
from collections.abc import Callable, Sequence

from django.conf import settings
from django.core.cache import cache

from apps.azure_devops.constants import (
    ITERATIONS_CACHE_SECONDS,
    MAX_PARALLEL_REQUESTS,
    PROJECTS_CACHE_SECONDS,
    WORK_ITEMS_CACHE_SECONDS,
)
from apps.azure_devops.exceptions import (
    AzureDevOpsConfigurationError,
    AzureDevOpsRequestError,
)
from apps.azure_devops.services.azure_client import (
    AzureDevOpsClient,
    JsonObject,
)
from core.utils.parallel import map_in_parallel

"""BKD.030.008 - Acceso con cache a Azure DevOps
Guarda en cache la lista de proyectos, las iteraciones y los work items.
Cada consulta crea su propio cliente HTTP para poder ejecutarse en
paralelo sin compartir conexiones entre hilos.
"""

logger = logging.getLogger(__name__)


class AzureDevOpsGateway:
    """Cliente de Azure DevOps con cache compartida."""

    def __init__(self) -> None:
        self.organization = settings.AZURE_DEVOPS_ORGANIZATION
        personal_access_token = settings.AZURE_DEVOPS_PAT

        if not self.organization or not personal_access_token:
            raise AzureDevOpsConfigurationError(
                "Define AZURE_DEVOPS_ORGANIZATION y AZURE_DEVOPS_PAT en el "
                "archivo .env.",
            )

        self._personal_access_token = personal_access_token
        token_fingerprint = hashlib.sha256(
            personal_access_token.encode("utf-8"),
        ).hexdigest()[:16]
        self._cache_prefix = f"azure:v1:{self.organization}:{token_fingerprint}"

    def list_project_names(self) -> list[str]:
        """
        Lista los Team Projects de la organizacion, con cache.

        Returns:
            Los nombres de los proyectos.
        """
        cache_key = f"{self._cache_prefix}:projects"
        cached_names = cache.get(cache_key)

        if isinstance(cached_names, list):
            return cached_names

        project_names = self._build_client().list_project_names()
        cache.set(cache_key, project_names, PROJECTS_CACHE_SECONDS)

        return project_names

    def list_work_items(self, project_name: str) -> list[JsonObject]:
        """
        Lee los work items de un Team Project, con cache.

        Args:
            project_name: Nombre del Team Project.

        Returns:
            Los work items del proyecto.
        """
        cache_key = f"{self._cache_prefix}:work_items:{project_name}"
        cached_items = cache.get(cache_key)

        if isinstance(cached_items, list):
            return cached_items

        work_items = self._build_client().list_work_items(project_name)
        cache.set(cache_key, work_items, WORK_ITEMS_CACHE_SECONDS)

        return work_items

    def list_iterations(
        self,
        project_name: str,
        force_refresh: bool = False,
    ) -> list[JsonObject]:
        """
        Lee las iteraciones de un Team Project, con cache de 15 minutos.

        Args:
            project_name: Nombre del Team Project.
            force_refresh: Ignora la cache y vuelve a consultar Azure.

        Returns:
            Las iteraciones en lista plana.
        """
        cache_key = f"{self._cache_prefix}:iterations:{project_name}"
        cached_iterations = cache.get(cache_key)

        if isinstance(cached_iterations, list) and not force_refresh:
            return cached_iterations

        iterations = self._build_client().list_iterations(project_name)
        cache.set(cache_key, iterations, ITERATIONS_CACHE_SECONDS)

        return iterations

    def create_client(self) -> AzureDevOpsClient:
        """Cliente HTTP nuevo, sin cache (consultas puntuales)."""
        return self._build_client()

    def prefetch(
        self,
        project_names: Sequence[str],
        include_iterations: bool,
    ) -> None:
        """
        Descarga en paralelo varios Team Projects y los deja en cache.

        Los errores se registran y se omiten: la consulta individual
        posterior vuelve a intentarlo y reporta el error.

        Args:
            project_names: Team Projects a precargar.
            include_iterations: Tambien precarga las iteraciones.
        """
        unique_names = [name for name in dict.fromkeys(project_names) if name]
        loaders: list[ProjectLoader] = [self.list_work_items]

        if include_iterations:
            loaders.append(self.list_iterations)

        tasks = [
            (loader, project_name)
            for project_name in unique_names
            for loader in loaders
        ]
        map_in_parallel(run_prefetch_task, tasks, MAX_PARALLEL_REQUESTS)

    def _build_client(self) -> AzureDevOpsClient:
        """Crea un cliente HTTP nuevo para la consulta actual."""
        return AzureDevOpsClient(
            self.organization,
            self._personal_access_token,
        )


ProjectLoader = Callable[[str], list[JsonObject]]


def run_prefetch_task(task: tuple[ProjectLoader, str]) -> None:
    """
    Ejecuta una precarga y registra el error si falla.

    Args:
        task: Funcion de carga y nombre del Team Project.
    """
    loader, project_name = task

    try:
        loader(project_name)
    except AzureDevOpsRequestError as error:
        logger.warning(
            "Precarga de Azure omitida para %s: %s",
            project_name,
            error.detail,
        )
