"""Carga del historico de KPIs con cache corta y errores controlados."""

import logging
from dataclasses import dataclass

from django.core.cache import cache
from django.utils import timezone

from apps.capacidad.services.mpb_projects import load_optional_mpb_projects
from apps.dashboard.services.delivery_managers import load_delivery_managers
from apps.dashboard.services.record_reader import (
    read_project_records,
    read_risk_records,
)
from apps.portal.constants import (
    KPI_HISTORY_CACHE_KEY,
    KPI_HISTORY_CACHE_SECONDS,
)
from apps.portal.schemas import KpiHistory
from apps.portal.services.kpi_history import (
    HistorySources,
    build_kpi_history,
)
from apps.portal.services.portfolio_source import ManagerLookup
from core.exceptions import DashboardError
from core.sheets.factory import build_sheet_repository
from core.time_entries.factory import build_time_entry_provider

"""BKD.120.027 - Cargador del historico de KPIs
Lee Proyectos, Riesgos, MPB, Historico_Proyectos y las horas de Clockify
(solo lectura, sin guardar nada) y reconstruye los cortes de cada mes. El
resultado correcto se guarda 10 minutos; un error se regresa como texto.
"""

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class KpiHistoryLoad:
    """Historico de KPIs y el motivo si no se pudo reconstruir."""

    history: KpiHistory | None
    error: str = ""


def load_kpi_history(year: int | None = None) -> KpiHistoryLoad:
    """
    Reconstruye los KPIs por mes y trimestre de un ano.

    Args:
        year: Ano a reconstruir; el actual si no se indica.

    Returns:
        El historico, o None con el motivo si una fuente fallo.
    """
    now = timezone.localtime().replace(tzinfo=None)
    chosen = year or now.year
    key = f"{KPI_HISTORY_CACHE_KEY}:{chosen}"
    cached = cache.get(key)

    if isinstance(cached, KpiHistory):
        return KpiHistoryLoad(history=cached)

    try:
        reader = build_sheet_repository()
        projects = read_project_records(reader)
        managers = ManagerLookup(
            load_optional_mpb_projects(reader)[0],
            load_delivery_managers(reader),
        ).as_mapping([item.project_id for item in projects])
        entries = build_time_entry_provider(reader).load_time_entries().entries
        history = build_kpi_history(
            HistorySources(
                projects=projects,
                entries=entries,
                risks=read_risk_records(reader),
                managers=managers,
            ),
            now,
            chosen,
        )
    except DashboardError as error:
        logger.warning("No se pudo reconstruir el historico: %s", error)

        return KpiHistoryLoad(history=None, error=error.build_message())

    cache.set(key, history, KPI_HISTORY_CACHE_SECONDS)

    return KpiHistoryLoad(history=history)
