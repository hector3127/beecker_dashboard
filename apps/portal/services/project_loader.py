"""Carga del dashboard ejecutivo de un proyecto (solo lectura)."""

import logging
from dataclasses import dataclass, field
from typing import Any

from django.core.cache import cache

from apps.ejecutivo.rpc import get_executive_dashboard
from apps.portal.constants import (
    PROJECT_CACHE_PREFIX,
    PROJECT_CACHE_SECONDS,
)
from core.exceptions import DashboardError, describe_error

"""BKD.120.018 - Cargador del proyecto
Lee getDashboardEjecutivoProyecto(id): hojas de Sheets y horas de Clockify,
solo lectura. Es lento en la primera carga, por eso se guarda 10 minutos.
"""

logger = logging.getLogger(__name__)

DEFAULT_ERROR = "No se pudo leer el detalle del proyecto."


@dataclass(frozen=True, slots=True)
class ProjectDashboardLoad:
    """Dashboard del proyecto y el motivo si no se pudo leer."""

    data: dict[str, Any] = field(default_factory=dict)
    error: str = ""


def load_project_dashboard(project_id: str) -> ProjectDashboardLoad:
    """
    Carga el dashboard ejecutivo de un proyecto.

    Args:
        project_id: ID exacto del proyecto en la hoja Proyectos.

    Returns:
        Los datos, o vacios con el motivo si no se pudo leer.
    """
    key = f"{PROJECT_CACHE_PREFIX}{project_id}"
    data = cache.get(key)

    if not isinstance(data, dict):
        try:
            data = get_executive_dashboard(project_id)
        except DashboardError as error:
            return ProjectDashboardLoad(error=describe_error(error))

        if data.get("proyecto") and not data.get("errorServidor"):
            cache.set(key, data, PROJECT_CACHE_SECONDS)

    if not data.get("proyecto"):
        error_text = str(data.get("errorServidor") or DEFAULT_ERROR)
        logger.warning("Proyecto %s sin detalle: %s", project_id, error_text)

        return ProjectDashboardLoad(error=error_text)

    return ProjectDashboardLoad(data=data)
