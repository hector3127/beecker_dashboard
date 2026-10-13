"""Carga de las pantallas EVA (solo lectura)."""

import logging
from dataclasses import dataclass

from django.core.cache import cache

from apps.ejecutivo.rpc import get_ixb_raas_summary, load_aer_tym_summary
from apps.portal.constants import EVA2_CACHE_KEY, EVA2_CACHE_SECONDS
from apps.portal.schemas import Eva1View, Eva2View
from apps.portal.services.eva1 import build_eva1_view
from apps.portal.services.eva2 import build_eva2_view
from core.exceptions import DashboardError
from core.sheets.factory import build_sheet_repository

"""BKD.120.015 - Carga de EVA
Lee la hoja MPB con el mismo servicio de apps/ejecutivo (que ya guarda
90 segundos en cache). Si falla, la pantalla muestra el aviso.
"""

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class Eva1Load:
    """Resultado de cargar EVA 1."""

    view: Eva1View
    error: str


def load_eva1() -> Eva1Load:
    """
    Carga EVA 1 desde la hoja MPB.

    Returns:
        La pantalla armada, o una vacia y el motivo si no se pudo leer.
    """
    try:
        summary = load_aer_tym_summary(build_sheet_repository())
    except DashboardError as error:
        logger.warning("No se pudo cargar EVA 1: %s", error)

        return Eva1Load(view=build_eva1_view([]), error=error.build_message())

    rows = summary.get("filas")

    return Eva1Load(
        view=build_eva1_view(rows if isinstance(rows, list) else []),
        error="",
    )


@dataclass(frozen=True, slots=True)
class Eva2Load:
    """Resultado de cargar EVA 2."""

    view: Eva2View
    error: str


def load_eva2() -> Eva2Load:
    """
    Carga EVA 2 con el resumen IXB/RaaS (Sheets, Clockify y Azure, lectura).

    La consulta es lenta porque revisa Azure DevOps y Clockify proyecto por
    proyecto, por eso el resumen se guarda 10 minutos en cache.

    Returns:
        La pantalla armada, o una vacia y el motivo si no se pudo leer.
    """
    summary = cache.get(EVA2_CACHE_KEY)

    if not isinstance(summary, dict):
        summary = get_ixb_raas_summary()

        if summary.get("ok") is True:
            cache.set(EVA2_CACHE_KEY, summary, EVA2_CACHE_SECONDS)

    if summary.get("ok") is not True:
        return Eva2Load(
            view=build_eva2_view([]),
            error=str(summary.get("error") or "No se pudo leer IXB y RaaS."),
        )

    rows = summary.get("filas")

    return Eva2Load(
        view=build_eva2_view(rows if isinstance(rows, list) else []),
        error="",
    )
