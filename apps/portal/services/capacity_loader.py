"""Carga de las asignaciones del mes para Capacidad instalada."""

import logging
from dataclasses import dataclass, field
from typing import Any

from django.core.cache import cache

from apps.capacidad.rpc import get_capacity_base
from apps.portal.constants import (
    CAPACITY_CACHE_PREFIX,
    CAPACITY_CACHE_SECONDS,
)

"""BKD.120.016 - Cargador de Capacidad instalada
Lee capacidadInstaladaBase(mes) (solo hojas de Sheets, lectura) y lo guarda
5 minutos por mes. Un error se regresa como texto para mostrarlo.
"""

logger = logging.getLogger(__name__)

DEFAULT_ERROR = "No se pudo leer Capacidad instalada."


@dataclass(frozen=True, slots=True)
class CapacityLoad:
    """Asignaciones del mes y el motivo si no se pudieron leer."""

    data: dict[str, Any] = field(default_factory=dict)
    error: str = ""


def load_capacity(month: str, refresh: bool = False) -> CapacityLoad:
    """
    Carga las asignaciones de un mes.

    Args:
        month: Mes valido YYYY-MM.
        refresh: Ignora la cache y vuelve a leer las hojas.

    Returns:
        Los datos, o vacios con el motivo si no se pudo leer.
    """
    key = f"{CAPACITY_CACHE_PREFIX}{month}"
    data = None if refresh else cache.get(key)

    if not isinstance(data, dict):
        data = get_capacity_base(month)

        if data.get("ok") is True:
            cache.set(key, data, CAPACITY_CACHE_SECONDS)

    if data.get("ok") is not True:
        error = str(data.get("error") or DEFAULT_ERROR)
        logger.warning("No se pudo cargar Capacidad instalada: %s", error)

        return CapacityLoad(error=error)

    return CapacityLoad(data=data)
