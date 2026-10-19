"""Descarga los Team Projects de Azure DevOps a la base diaria."""

import logging
import time
from dataclasses import dataclass, field
from typing import Any

from django.core.cache import cache

from apps.azure_devops.constants import MAX_PARALLEL_REQUESTS
from apps.azure_devops.exceptions import AzureDevOpsRequestError
from apps.azure_devops.gateway import AzureDevOpsGateway
from apps.azure_devops.services import raid_cache
from apps.datastore.services import azure_store
from core.exceptions import DashboardError
from core.utils.parallel import map_in_parallel

"""BKD.130.012 - Sincronizacion de Azure DevOps
Lee de cada Team Project lo mismo que lee el gateway (work items, RAID,
campos de Risk e iteraciones) y lo guarda. Las llamadas HTTP van en hilos
y solo el hilo principal escribe en la base. Un proyecto que falla conserva
su copia anterior; los que ya no existen se borran.
"""

logger = logging.getLogger(__name__)

JsonObject = dict[str, Any]
ProjectData = tuple[
    list[JsonObject], list[JsonObject], list[JsonObject], list[JsonObject]
]


@dataclass
class AzureSyncResult:
    """Lo que dejo la sincronizacion."""

    projects: int = 0
    work_items: int = 0
    iterations: int = 0
    removed: int = 0
    seconds: float = 0.0
    failed: list[str] = field(default_factory=list)
    no_risk_fields: list[str] = field(default_factory=list)


def fetch_project(
    gateway: AzureDevOpsGateway, name: str
) -> tuple[ProjectData, bool] | str:
    """
    Lee un Team Project (sin tocar la base: corre en un hilo).

    Args:
        gateway: Acceso a Azure DevOps.
        name: Nombre del Team Project.

    Returns:
        Los datos y si los campos de Risk se leyeron bien, o el mensaje de
        error si el proyecto no se pudo leer.
    """
    client = gateway.create_client()
    try:
        work_items = client.list_work_items(name)
        raid = client.list_raid_items(name)
        iterations = client.list_iterations(name)
    except AzureDevOpsRequestError as error:
        return f"{name}: {error.detail}"
    try:
        risk_fields = client.list_risk_fields(name)
        fields_ok = True
    except DashboardError as error:
        logger.info(
            "Campos de Risk no disponibles en %s: %s", name, error.detail
        )
        risk_fields, fields_ok = [], False
    return (work_items, raid, risk_fields, iterations), fields_ok


def sync_azure(
    gateway: AzureDevOpsGateway,
    only: list[str] | None = None,
) -> AzureSyncResult:
    """
    Guarda en la base los Team Projects de la organizacion.

    Args:
        gateway: Acceso a Azure DevOps.
        only: Sincroniza solo estos proyectos (None: todos).

    Returns:
        Conteos y proyectos que fallaron.
    """
    started = time.perf_counter()
    result = AzureSyncResult()
    names = gateway.create_client().list_project_names()
    positions = {name: position for position, name in enumerate(names)}
    wanted = [name for name in names if only is None or name in only]
    fetched = map_in_parallel(
        lambda name: fetch_project(gateway, name), wanted, MAX_PARALLEL_REQUESTS
    )
    version = raid_cache.read_version(cache)
    for name, outcome in zip(wanted, fetched, strict=True):
        if isinstance(outcome, str):
            result.failed.append(outcome)
            continue
        data, fields_ok = outcome
        azure_store.save_project(
            name, positions[name], data, version, fields_ok
        )
        result.projects += 1
        result.work_items += len(data[0]) + len(data[1])
        result.iterations += len(data[3])
        if not fields_ok:
            result.no_risk_fields.append(name)
    if only is None:
        result.removed = azure_store.drop_projects_except(names)
    result.seconds = time.perf_counter() - started
    return result
