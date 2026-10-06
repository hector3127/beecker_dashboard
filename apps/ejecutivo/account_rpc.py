"""Funciones de la vista de cuenta Beecker expuestas al frontend por RPC."""

import logging
from datetime import date
from typing import Any

from django.core.cache import cache
from django.utils import timezone

from apps.clockify.provider import build_clockify_loader
from apps.clockify.services.time_entry_loader import ClockifyTimeEntryLoader
from apps.ejecutivo.services import account_actions, account_view
from core.exceptions import DashboardError, describe_error
from core.rpc.registry import register_rpc
from core.sheets.factory import build_sheet_repository
from core.time_entries.models import TimeEntry

"""BKD.040.012 - RPC de la vista de cuenta
Registra obtenerVistaCuentaBeecker, obtenerOportunidadesCuentaBeecker,
beeCuentaGuardarOportunidad y obtenerConsumosMPBCuenta con los mismos
nombres y respuestas que DailyPanelService.gs.
"""

logger = logging.getLogger(__name__)

JsonObject = dict[str, Any]


@register_rpc("obtenerVistaCuentaBeecker")
def get_account_view(client: object = None) -> JsonObject:
    """Proyectos, ROC, MPB y oportunidades de la cuenta."""
    try:
        return account_view.build_account_view(
            build_sheet_repository(),
            client,
            cache,
            timezone.localdate(),
        )
    except DashboardError as error:
        logger.warning("Vista de cuenta no disponible: %s", error.detail)
        return {"ok": False, "error": describe_error(error)}


@register_rpc("obtenerOportunidadesCuentaBeecker")
def get_account_opportunities(client: object = None) -> JsonObject:
    """Oportunidades abiertas de la cuenta en el backlog."""
    try:
        data = account_view.load_opportunities(
            build_sheet_repository(),
            client,
            cache,
        )
    except DashboardError as error:
        return {"ok": False, "error": describe_error(error)}

    return {"ok": True, **data}


@register_rpc("beeCuentaGuardarOportunidad")
def save_account_opportunity(
    client: object = None,
    payload: object = None,
) -> JsonObject:
    """Agrega una oportunidad al backlog de la cuenta."""
    try:
        repository = build_sheet_repository()
        return account_actions.save_opportunity(
            (repository, repository),
            client,
            payload,
            cache,
        )
    except DashboardError as error:
        return {"ok": False, "error": describe_error(error)}


@register_rpc("obtenerConsumosMPBCuenta")
def get_account_consumption(
    client: object = None,
    offset: object = None,
    limit: object = None,
    pending_ids: object = None,
) -> JsonObject:
    """Horas de Clockify de un lote de proyectos MPB de la cuenta."""
    try:
        repository = build_sheet_repository()
        loaders: list[ClockifyTimeEntryLoader] = []

        def load_entries(
            project_id: str,
            date_range: tuple[date, date],
        ) -> list[TimeEntry]:
            # El cargador se crea al primer proyecto: sin configuracion de
            # Clockify el error queda en cada elemento, como el original.
            if not loaders:
                loaders.append(build_clockify_loader(repository))

            return loaders[0].load_project(project_id, date_range)

        return account_actions.load_account_consumption(
            (repository, repository),
            (client, offset, limit, pending_ids),
            load_entries,
            timezone.localdate(),
            cache,
        )
    except DashboardError as error:
        return {"ok": False, "error": describe_error(error), "items": []}
