"""Funciones de GSE expuestas al frontend por RPC."""

import logging
from typing import Any

from django.conf import settings
from django.core.cache import cache
from django.utils import timezone

from apps.clockify.services.clockify_client import ClockifyClient
from apps.gse.services.base_store import BaseStore, build_connection
from apps.gse.services.base_writer import BaseWriter, SheetStore
from apps.gse.services.batch_read import get_batch
from apps.gse.services.clockify_ids import IdsContext, get_clockify_ids
from apps.gse.services.clockify_month import MonthReportLoader
from apps.gse.services.month_report import GseContext, get_month
from apps.gse.services.result_cache import ResultCache
from apps.gse.services.roster import list_areas
from apps.gse.services.year_base import get_year
from core.exceptions import DashboardError, describe_error
from core.rpc.registry import register_rpc
from core.sheets.factory import build_sheet_repository

"""BKD.100.013 - RPC de GSE
Registra gseObtenerAreas, gseObtenerMes, gseObtenerAnoBase,
gseObtenerLoteBase, gseLeerResultadoCache y gseGuardarResultadoCache con
los mismos nombres y respuestas que en Apps Script.
"""

logger = logging.getLogger(__name__)

JsonObject = dict[str, Any]


def build_context(reader: SheetStore) -> GseContext:
    """
    Arma las hojas, la base guardada y la fuente de Clockify.

    Args:
        reader: Repositorio de Sheets de la peticion.

    Returns:
        El contexto para las consultas de GSE.
    """
    connection = build_connection(
        settings.CLOCKIFY_API_KEY,
        settings.CLOCKIFY_WORKSPACE_ID,
    )
    store = BaseStore(reader, connection, timezone.now())
    loader = MonthReportLoader(
        (
            settings.CLOCKIFY_API_KEY,
            settings.CLOCKIFY_WORKSPACE_ID,
            settings.TIME_ZONE,
        ),
        (store, connection, cache),
        BaseWriter(reader, connection, timezone.now()).save_month,
    )

    return GseContext(reader, store, loader)


def build_result_cache() -> ResultCache:
    """Cache del resultado anual con la cache de Django."""
    return ResultCache(
        cache,
        settings.GOOGLE_SPREADSHEET_ID,
        timezone.localdate(),
    )


@register_rpc("gseObtenerAreas")
def get_gse_areas() -> JsonObject:
    """
    Lista las areas (ROL de Bandas/rol) sin llamar a Clockify.

    Returns:
        {"ok": True, "areas": [...]} o {"ok": False, "error"}.
    """
    try:
        return {"ok": True, "areas": list_areas(build_sheet_repository())}
    except DashboardError as error:
        logger.warning("GSE areas no disponibles: %s", error.detail)

        return {"ok": False, "error": describe_error(error)}


@register_rpc("gseObtenerMes")
def get_gse_month(
    month: object = "",
    source: object = "",
    force_refresh: object = False,
    selected_area: object = "",
) -> JsonObject:
    """
    Devuelve las horas del mes por area, persona y categoria.

    Args:
        month: Mes YYYY-MM.
        source: "sheet" para la base en Sheets; otro valor usa la API.
        force_refresh: Ignora la base guardada y la cache de Clockify.
        selected_area: Area elegida; vacio para todas.

    Returns:
        El resultado del mes o {"ok": False, "mes", "error"}.
    """
    try:
        context = build_context(build_sheet_repository())
    except DashboardError as error:
        return {"ok": False, "mes": month, "error": describe_error(error)}

    return get_month(
        context,
        (month, source, bool(force_refresh), selected_area),
    )


@register_rpc("gseObtenerAnoBase")
def get_gse_year(
    year: object = None,
    selected_area: object = "",
) -> JsonObject:
    """
    Lee del ano todos los meses transcurridos desde la base en Sheets.

    Args:
        year: Ano a consultar.
        selected_area: Area elegida; vacio para todas.

    Returns:
        {"ok", "data", "milliseconds"} o {"ok": False, "error"}.
    """
    try:
        context = build_context(build_sheet_repository())
    except DashboardError as error:
        return {"ok": False, "error": describe_error(error)}

    return get_year(context, (year, selected_area), timezone.localdate())


@register_rpc("gseObtenerLoteBase")
def get_gse_batch(
    year: object = None,
    selected_area: object = "",
    cursor: object = 0,
    expected_rows: object = None,
) -> JsonObject:
    """
    Lee un bloque de la base anual (las filas mas recientes primero).

    Args:
        year: Ano a consultar.
        selected_area: Area elegida; vacio para todas.
        cursor: Filas ya leidas.
        expected_rows: Filas que tenia la base en el primer bloque.

    Returns:
        El bloque con sus registros o {"ok": False, "error"}.
    """
    try:
        context = build_context(build_sheet_repository())
    except DashboardError as error:
        return {"ok": False, "error": describe_error(error)}

    return get_batch(
        context,
        (year, selected_area, cursor, expected_rows),
    )


@register_rpc("gseLeerResultadoCache")
def read_gse_result_cache(
    year: object = None,
    area: object = "",
    clear: object = False,
) -> JsonObject:
    """
    Lee (o borra) el resultado anual guardado.

    Args:
        year: Ano consultado.
        area: Area consultada; vacio para todas.
        clear: Borra el resultado guardado.

    Returns:
        {"ok": True, "cached": bool, ...}.
    """
    return build_result_cache().read((year, area, bool(clear)))


@register_rpc("gseGuardarResultadoCache")
def save_gse_result_cache(
    year: object = None,
    area: object = "",
    result: object = None,
) -> JsonObject:
    """
    Guarda el resultado anual terminado durante 6 horas.

    Args:
        year: Ano consultado.
        area: Area consultada; vacio para todas.
        result: {"data", "bandas", "total"} armado por el frontend.

    Returns:
        {"ok": True, "savedAt"} o {"ok": False, "error"}.
    """
    return build_result_cache().save(year, area, result)


@register_rpc("gseObtenerIDsClockify")
def get_gse_clockify_ids(
    month: object = "",
    report_only: object = False,
) -> JsonObject:
    """
    Busca los IDs de Clockify y los guarda en la columna de Bandas/rol.

    Args:
        month: Mes YYYY-MM para el reporte cuando no se puede listar.
        report_only: Salta la lista de usuarios y usa solo el reporte.

    Returns:
        {"ok", "guardados", "pendientes", "fuente", "aviso"} o
        {"ok": False, "error"}.
    """
    try:
        sheets = build_sheet_repository()
        context = build_context(sheets)
    except DashboardError as error:
        return {"ok": False, "error": describe_error(error)}

    api_key = settings.CLOCKIFY_API_KEY

    return get_clockify_ids(
        IdsContext(
            sheets,
            ClockifyClient(api_key) if api_key else None,
            settings.CLOCKIFY_WORKSPACE_ID,
            context.load_api_hours,
        ),
        month,
        report_only,
    )
