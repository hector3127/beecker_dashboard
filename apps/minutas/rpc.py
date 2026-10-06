"""Funciones de Minutas IA expuestas al frontend por RPC."""

from typing import Any

from apps.minutas.scanner_factory import run_minutes_scan
from apps.minutas.services.minutes_view import (
    build_minutes_view,
    list_projects_with_minutes,
)
from core.rpc.registry import register_rpc
from core.sheets import sheet_names
from core.sheets.factory import build_sheet_repository

"""BKD.060.009 - RPC de Minutas
Registra getMinutasViewData, getProyectosConMinutas y
actualizarDesdeUltimaMinuta con los mismos nombres y respuestas que en
Apps Script.
"""

JsonObject = dict[str, Any]


@register_rpc("getMinutasViewData")
def get_minutes_view(filters: object = None) -> JsonObject:
    """
    Devuelve las minutas con sus pendientes, riesgos y acuerdos.

    Args:
        filters: {"fecha", "proyecto"} del panel.

    Returns:
        {"minutas": [...]}.
    """
    repository = build_sheet_repository()
    repository.prefetch(
        [
            sheet_names.SHEET_MINUTES,
            sheet_names.SHEET_MINUTES_PENDING,
            sheet_names.SHEET_RISKS,
        ],
    )

    return build_minutes_view(
        repository.read_as_objects(sheet_names.SHEET_MINUTES),
        repository.read_as_objects(sheet_names.SHEET_MINUTES_PENDING),
        repository.read_as_objects(sheet_names.SHEET_RISKS),
        filters,
    )


@register_rpc("getProyectosConMinutas")
def get_projects_with_minutes() -> list[str]:
    """
    Lista los proyectos que ya tienen minutas.

    Returns:
        "Todos los proyectos" seguido de los IDs.
    """
    repository = build_sheet_repository()

    return list_projects_with_minutes(
        repository.read_as_objects(sheet_names.SHEET_MINUTES),
        repository.read_as_objects(sheet_names.SHEET_PROJECTS),
    )


@register_rpc("actualizarDesdeUltimaMinuta")
def refresh_from_latest_minute(filters: object = None) -> JsonObject:
    """
    Escanea las minutas de hoy y regresa la vista actualizada.

    Args:
        filters: {"fecha", "proyecto"} del panel.

    Returns:
        {"minutas": [...]}.
    """
    run_minutes_scan()

    return get_minutes_view(filters)
