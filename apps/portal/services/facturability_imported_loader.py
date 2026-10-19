"""Carga de GSE (Clockify) para Facturabilidad, sin escribir nada."""

import logging
from dataclasses import dataclass, field
from typing import Any

from django.conf import settings
from django.core.cache import cache
from django.utils import timezone

from apps.gse.services.base_store import build_base_store, build_connection
from apps.gse.services.clockify_month import MonthReportLoader
from apps.gse.services.month_report import GseContext, get_month
from apps.portal.constants import (
    FACTURABILITY_CACHE_PREFIX,
    FACTURABILITY_CACHE_SECONDS,
)
from apps.portal.services.facturability_roster import apply_roster, attach_month_roster
from core.exceptions import DashboardError, describe_error
from core.sheets.factory import build_sheet_repository

"""BKD.120.024 - Cargador de Facturabilidad
Lee cada mes igual que GSE con la fuente "API Clockify": usa la base de
Clockify guardada en Sheets cuando cubre el mes y, si no, descarga el
reporte de Clockify. La plantilla se lee directamente de Bandas/rol para
el mes, sin exigir Recursos ni MPB. Si falta la columna mensual se usan
las personas con horas de GSE con un aviso. Nunca guarda lo
descargado en Sheets (persist=None): solo lectura. El resultado correcto
se guarda 10 minutos por mes en la cache de Django.
"""

logger = logging.getLogger(__name__)

GSE_SOURCE_API = "api"
FIRST_MONTH = 1


@dataclass(frozen=True, slots=True)
class MonthSources:
    """Horas de GSE (por area, persona y categoria) de un mes."""

    month: str
    gse: dict[str, Any] = field(default_factory=dict)
    error: str = ""


def read_gse_month(month: str) -> dict[str, Any]:
    """
    Lee un mes de GSE desde Clockify sin escribir en Sheets.

    Args:
        month: Mes valido YYYY-MM.

    Returns:
        El resultado de gseObtenerMes o {"ok": False, "error"}.
    """
    try:
        reader = build_sheet_repository()
        connection = build_connection(
            settings.CLOCKIFY_API_KEY,
            settings.CLOCKIFY_WORKSPACE_ID,
        )
        store = build_base_store(reader, connection, timezone.now())
        loader = MonthReportLoader(
            (
                settings.CLOCKIFY_API_KEY,
                settings.CLOCKIFY_WORKSPACE_ID,
                settings.TIME_ZONE,
            ),
            (store, connection, cache),
            persist=None,
        )
        context = GseContext(reader, store, loader)
    except DashboardError as error:
        return {"ok": False, "mes": month, "error": describe_error(error)}

    result = get_month(context, (month, GSE_SOURCE_API, False, ""))
    if result.get("ok") is not True:
        return result
    try:
        return attach_month_roster(result, reader, month)
    except DashboardError as error:
        return {"ok": False, "mes": month, "error": describe_error(error)}


def load_month_sources(month: str) -> MonthSources:
    """
    Lee las horas de GSE de un mes.

    Args:
        month: Mes valido YYYY-MM.

    Returns:
        Los datos del mes; con error si GSE no se pudo leer.
    """
    key = f"portal:facturability:imported:v7:{month}"
    cached = cache.get(key)

    if isinstance(cached, MonthSources):
        return cached

    gse = read_gse_month(month)

    if gse.get("ok") is not True:
        error = f"GSE: {gse.get('error') or 'sin datos'}"
        logger.warning("Facturabilidad %s incompleta: %s", month, error)

        return MonthSources(month=month, error=error)

    people = gse.get("plantilla")
    if isinstance(people, list):
        gse = apply_roster(gse, people)
    result = MonthSources(month=month, gse=gse)
    cache.set(key, result, FACTURABILITY_CACHE_SECONDS)

    return result


def year_months(month: str) -> list[str]:
    """
    Meses del ano hasta el mes elegido.

    Args:
        month: Mes valido YYYY-MM.

    Returns:
        ["2026-01", ..., month].
    """
    year, last = month[:4], int(month[5:7])

    return [f"{year}-{number:02d}" for number in range(FIRST_MONTH, last + 1)]


def load_year_sources(month: str) -> list[MonthSources]:
    """
    Lee de enero al mes elegido.

    Args:
        month: Mes valido YYYY-MM.

    Returns:
        Los datos de cada mes, en orden.
    """
    return [load_month_sources(item) for item in year_months(month)]


def peek_month_sources(month: str) -> MonthSources | None:
    """
    Datos de un mes solo si ya estan en cache (no lee Sheets).

    Args:
        month: Mes valido YYYY-MM.

    Returns:
        Los datos guardados, o None.
    """
    cached = cache.get(f"portal:facturability:imported:v7:{month}")

    return cached if isinstance(cached, MonthSources) else None

