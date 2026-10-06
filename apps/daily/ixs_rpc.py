"""Funciones de la vista IXS (panel Azure y RAID) expuestas por RPC."""

import contextlib
import time
from collections.abc import Callable
from typing import Any

from django.conf import settings
from django.core.cache import cache
from django.utils import timezone

from apps.azure_devops.gateway import AzureDevOpsGateway, clear_raid_cache
from apps.azure_devops.services.project_resolver import (
    normalize_azure_name,
    resolve_azure_project,
)
from apps.daily.rpc import build_daily_azure, build_sheets, build_store
from apps.daily.services import daily_sheets, ixs_raid, risk_form
from apps.daily.services.daily_azure_client import DailyAzureClient
from apps.daily.services.ixs_functions import SHEET_FUNCTIONS, call_action
from apps.daily.services.ixs_panel import IxsAzure, load_panel
from apps.daily.services.ixs_store import IxsStore, run_safely
from core.exceptions import DashboardError
from core.rpc.registry import register_rpc
from core.sheets.factory import build_sheet_repository
from core.utils.text import extract_base_id

"""BKD.070.014 - RPC de la vista IXS
Registra obtenerPanelAzureProyectoIXS() y las funciones ixsRaid* con
los mismos nombres y respuestas que DailyPanelService.gs.
"""

JsonObject = dict[str, Any]


def now_ms() -> int:
    """Milisegundos actuales, como Date.now()."""
    return time.time_ns() // 10**6


def resolve_project(project_id: str, active_project: str) -> str:
    """
    Team Project del ID interno, como _altoNivelResolverProyectoAzure().

    Args:
        project_id: ID interno.
        active_project: Proyecto activo del selector o del .env.

    Returns:
        El Team Project, el activo si comparte el ID base, o cadena vacia.
    """
    resolved = resolve_azure_project(
        project_id,
        AzureDevOpsGateway().list_project_names(),
    )

    if resolved:
        return resolved

    active_base = normalize_azure_name(extract_base_id(active_project))

    if active_base == normalize_azure_name(extract_base_id(project_id)):
        return active_project

    return ""


def build_ixs_azure() -> IxsAzure:
    """Configuracion del .env, resolver de proyectos y cache."""
    organization = settings.AZURE_DEVOPS_ORGANIZATION
    personal_access_token = settings.AZURE_DEVOPS_PAT

    active_project = build_store().active_project()

    return IxsAzure(
        organization=organization,
        personal_access_token=personal_access_token,
        active_project=active_project,
        resolve_project=lambda project_id: resolve_project(
            project_id,
            active_project,
        ),
        build_client=lambda: DailyAzureClient(
            organization,
            personal_access_token,
        ),
        cache=cache,
        load_progress=lambda: daily_sheets.load_progress_map(build_sheets()),
    )


@register_rpc("obtenerPanelAzureProyectoIXS")
def get_ixs_panel(
    project_id: object = "",
    force_refresh: object = False,
) -> JsonObject:
    """Work items del proyecto con avance y alertas de seguimiento."""
    return load_panel(build_ixs_azure(), project_id, force_refresh, now_ms())


@register_rpc("ixsRaidListarProyecto")
def list_raid(
    project_id: object = "", force_refresh: object = False
) -> JsonObject:
    """Risks, Issues y Opportunities del proyecto con su detalle."""
    return ixs_raid.list_raid(
        build_ixs_azure(),
        project_id,
        force_refresh,
        now_ms(),
    )


@register_rpc("ixsRaidCamposTipo")
def raid_field_types(
    project_id: object = "", raid_type: object = ""
) -> JsonObject:
    """Opciones de los campos principales del tipo RAID."""
    return ixs_raid.raid_field_types(build_ixs_azure(), project_id, raid_type)


@register_rpc("ixsRaidAltaOpciones")
def raid_creation_options(
    project_id: object = "",
    raid_type: object = "",
) -> JsonObject:
    """Iteraciones, usuarios, relacionados y campos para el alta."""
    return ixs_raid.raid_creation_options(
        build_ixs_azure(),
        project_id,
        raid_type,
    )


@register_rpc("ixsRaidCrearRegistro")
def create_raid_record(
    project_id: object = "",
    raid_type: object = "",
    data: object = None,
) -> JsonObject:
    """Crea el Risk, Issue u Opportunity en Azure DevOps."""
    result = ixs_raid.create_raid_record(
        build_ixs_azure(),
        project_id,
        raid_type,
        data,
    )

    if result.get("ok"):
        # Como _limpiarCacheAzureDevOps(): las tarjetas del Daily se
        # vuelven a consultar con el registro nuevo.
        with contextlib.suppress(DashboardError):
            risk_form.clear_work_item_cache(build_daily_azure())

        clear_raid_cache()

    return result


# --- Cliente, acciones, recursos, planeacion y beeCom --------------------


def build_store_sheets() -> IxsStore:
    """Hojas de la vista IXS con la hora actual."""
    repository = build_sheet_repository()

    return IxsStore(reader=repository, writer=repository, now=timezone.now())


def sheet_rpc(
    name: str,
    action: Callable[..., JsonObject],
) -> None:
    """Registra una funcion de las hojas IXS con el manejo de errores."""

    def handler(*args: object) -> JsonObject:
        return run_safely(
            lambda: call_action(action, build_store_sheets(), args),
        )

    handler.__name__ = name
    handler.__doc__ = action.__doc__
    register_rpc(name)(handler)


for _name, _action in SHEET_FUNCTIONS.items():
    sheet_rpc(_name, _action)
