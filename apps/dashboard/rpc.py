"""Funciones del dashboard expuestas al frontend por RPC."""

from django.utils import timezone

from apps.dashboard.cache import read_cached_dashboard, save_cached_dashboard
from apps.dashboard.schemas.dashboard_filters import parse_dashboard_filters
from apps.dashboard.services.filters import build_available_filters
from apps.dashboard.services.orchestrator import DashboardOrchestrator
from apps.dashboard.services.record_reader import read_project_records
from apps.dashboard.services.response_builder import JsonObject
from core.rpc.registry import register_rpc
from core.sheets.factory import build_sheet_repository
from core.time_entries.factory import build_time_entry_provider

"""BKD.010.021 - RPC del dashboard
Registra getDashboardData y getFiltrosDisponibles con los mismos nombres
que tenian en Apps Script.
"""


@register_rpc("getDashboardData")
def get_dashboard_data(filters_payload: object = None) -> JsonObject:
    """
    Devuelve todos los KPIs y datasets del dashboard ejecutivo.

    Args:
        filters_payload: Objeto {proyecto, cliente} del frontend.

    Returns:
        El JSON con el mismo contrato que getDashboardData().
    """
    filters = parse_dashboard_filters(filters_payload)

    if filters.is_empty:
        cached_payload = read_cached_dashboard()

        if cached_payload is not None:
            return cached_payload

    repository = build_sheet_repository()
    orchestrator = DashboardOrchestrator(
        reader=repository,
        writer=repository,
        time_entry_provider=build_time_entry_provider(repository),
    )
    local_now = timezone.localtime().replace(tzinfo=None)
    result = orchestrator.build_dashboard(filters, local_now)

    if result.is_cacheable:
        save_cached_dashboard(result.payload)

    return result.payload


@register_rpc("getFiltrosDisponibles")
def get_available_filters() -> JsonObject:
    """
    Devuelve las opciones de los selectores de proyecto y cliente.

    Returns:
        {"proyectos": [...], "clientes": [...]}.
    """
    repository = build_sheet_repository()

    return dict(build_available_filters(read_project_records(repository)))
