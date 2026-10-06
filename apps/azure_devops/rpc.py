"""Funciones de Azure DevOps expuestas al frontend por RPC."""

import logging
from collections.abc import Callable

from django.conf import settings
from django.core.cache import cache

from apps.azure_devops.exceptions import AzureDevOpsConfigurationError
from apps.azure_devops.gateway import AzureDevOpsGateway
from apps.azure_devops.services.azure_client import JsonObject
from apps.azure_devops.services.portfolio_risks import (
    build_portfolio_risks,
    group_projects_by_azure,
)
from apps.azure_devops.services.project_raid import build_project_raid
from apps.daily.constants import SHEET_DAILY_PENDING
from apps.daily.services.azure_connection import ConnectionStore
from apps.daily.services.ixs_functions import fill_args
from core.exceptions import DashboardError
from core.rpc.registry import register_rpc
from core.sheets import sheet_names
from core.sheets.factory import build_sheet_repository
from core.utils.cell_types import SheetRow

"""BKD.030.009 - RPC de Azure DevOps
Registra obtenerTopRiesgosPortafolioAzure y obtenerRaidProyectoEjecutivoAzure
con los mismos nombres y respuestas que en Apps Script.
"""

logger = logging.getLogger(__name__)


@register_rpc("obtenerTopRiesgosPortafolioAzure")
def get_portfolio_top_risks() -> JsonObject:
    """
    Devuelve los riesgos Active/Proposed de todo el portafolio.

    Returns:
        {"ok", "riesgos", "total", "riesgosAltos"}; con ok en False y
        el mensaje de error cuando falla, como el original.
    """
    try:
        gateway = AzureDevOpsGateway()
        project_rows = build_sheet_repository().read_as_objects(
            sheet_names.SHEET_PROJECTS,
        )
        groups = group_projects_by_azure(
            project_rows,
            gateway.list_project_names(),
        )
        gateway.prefetch(list(groups), include_iterations=False)

        return build_portfolio_risks(
            groups,
            gateway.list_work_items,
            gateway.organization,
        )
    except DashboardError as error:
        logger.warning("Top riesgos no disponibles: %s", error.detail)

        return {
            "ok": False,
            "riesgos": [],
            "total": 0,
            "riesgosAltos": 0,
            "error": error.build_message(),
        }


@register_rpc("obtenerRaidProyectoEjecutivoAzure")
def get_project_raid(*args: object) -> JsonObject:
    """
    RAID del dashboard ejecutivo de un proyecto (solo consulta Azure).

    Returns:
        El mismo objeto que obtenerRaidProyectoEjecutivoAzure().
    """
    (project_id,) = fill_args(args, 1)
    repository = build_sheet_repository()

    def pending_rows() -> list[SheetRow]:
        if not repository.sheet_exists(SHEET_DAILY_PENDING):
            return []

        return repository.read_as_objects(SHEET_DAILY_PENDING)

    try:
        gateway: AzureDevOpsGateway | None = AzureDevOpsGateway()
    except AzureDevOpsConfigurationError:
        gateway = None

    try:
        project_names = gateway.list_project_names() if gateway else []
    except DashboardError as error:
        logger.warning("Proyectos de Azure no disponibles: %s", error.detail)
        project_names = []

    return build_project_raid(
        project_id,
        project_names,
        active_daily_project(),
        build_raid_loader(gateway) if gateway else None,
        pending_rows,
        gateway.organization if gateway else "",
    )


def build_raid_loader(
    gateway: AzureDevOpsGateway,
) -> Callable[[str], tuple[list[JsonObject], list[JsonObject]]]:
    """Work items RAID y campos de Risk de un Team Project, con cache."""
    return gateway.list_raid


def active_daily_project() -> str:
    """Proyecto activo del panel Daily (solo lectura)."""
    return ConnectionStore(
        cache,
        settings.AZURE_DEVOPS_ORGANIZATION,
        settings.AZURE_DEVOPS_PAT,
        settings.AZURE_DEVOPS_PROJECT,
    ).active_project()
