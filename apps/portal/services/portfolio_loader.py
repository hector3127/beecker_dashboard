"""Carga del portafolio con cache corta y errores controlados."""

import logging
from dataclasses import dataclass
from datetime import datetime

from django.core.cache import cache
from django.utils import timezone

from apps.portal.constants import PORTFOLIO_CACHE_KEY, PORTFOLIO_CACHE_SECONDS
from apps.portal.schemas import ProjectView
from apps.portal.services.portfolio_source import build_project_views
from core.exceptions import DashboardError
from core.sheets.factory import build_sheet_repository
from core.time_entries.factory import build_time_entry_provider

"""BKD.120.009 - Carga del portafolio
Entrega los proyectos a las vistas. Si Sheets no responde, la pantalla
se muestra con un aviso en lugar de fallar.
"""

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class PortfolioLoad:
    """Resultado de cargar el portafolio."""

    projects: tuple[ProjectView, ...]
    error: str
    loaded_at: datetime


def load_portfolio() -> PortfolioLoad:
    """
    Carga los proyectos desde la cache o desde Sheets (solo lectura).

    Returns:
        Los proyectos, o una lista vacia y el motivo si no se pudo leer.
    """
    now = timezone.localtime()
    cached = cache.get(PORTFOLIO_CACHE_KEY)

    if isinstance(cached, tuple):
        return PortfolioLoad(projects=cached, error="", loaded_at=now)

    try:
        repository = build_sheet_repository()
        projects = build_project_views(
            repository,
            build_time_entry_provider(repository),
            now.replace(tzinfo=None),
        )
    except DashboardError as error:
        logger.warning("No se pudo cargar el portafolio: %s", error)

        return PortfolioLoad(
            projects=(),
            error=error.build_message(),
            loaded_at=now,
        )

    cache.set(PORTFOLIO_CACHE_KEY, projects, PORTFOLIO_CACHE_SECONDS)

    return PortfolioLoad(projects=projects, error="", loaded_at=now)
