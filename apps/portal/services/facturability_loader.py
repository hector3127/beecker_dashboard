"""Carga de GSE y Recursos para Facturabilidad (solo lectura)."""

import logging
from dataclasses import dataclass, field
from typing import Any

from django.core.cache import cache

from apps.gse.rpc import get_gse_month
from apps.portal.constants import (
    FACTURABILITY_CACHE_PREFIX,
    FACTURABILITY_CACHE_SECONDS,
)
from apps.portal.services.capacity_loader import load_capacity

"""BKD.120.024 - Cargador de Facturabilidad
Por cada mes lee las horas de GSE desde su base en Sheets (fuente "sheet":
nunca llama a la API de Clockify ni escribe) y las asignaciones de
Recursos. El resultado correcto se guarda 10 minutos por mes.
"""

logger = logging.getLogger(__name__)

GSE_SOURCE_SHEET = "sheet"
FIRST_MONTH = 1


@dataclass(frozen=True, slots=True)
class MonthSources:
    """Horas de GSE y capacidad de un mes."""

    month: str
    gse: dict[str, Any] = field(default_factory=dict)
    capacity: dict[str, Any] = field(default_factory=dict)
    error: str = ""


def load_month_sources(month: str) -> MonthSources:
    """
    Lee GSE y Recursos de un mes.

    Args:
        month: Mes valido YYYY-MM.

    Returns:
        Los datos del mes; con error si alguna fuente fallo.
    """
    key = f"{FACTURABILITY_CACHE_PREFIX}{month}"
    cached = cache.get(key)

    if isinstance(cached, MonthSources):
        return cached

    gse = get_gse_month(month, GSE_SOURCE_SHEET, False, "")
    capacity = load_capacity(month)
    errors = []

    if gse.get("ok") is not True:
        errors.append(f"GSE: {gse.get('error') or 'sin datos'}")

    if capacity.error:
        errors.append(f"Recursos: {capacity.error}")

    result = MonthSources(
        month=month,
        gse=gse if gse.get("ok") is True else {},
        capacity=capacity.data,
        error=" · ".join(errors),
    )

    if errors:
        logger.warning("Facturabilidad %s incompleta: %s", month, result.error)
    else:
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
    cached = cache.get(f"{FACTURABILITY_CACHE_PREFIX}{month}")

    return cached if isinstance(cached, MonthSources) else None
