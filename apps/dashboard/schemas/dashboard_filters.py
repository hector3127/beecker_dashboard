"""Filtros que envia el frontend al dashboard."""

from dataclasses import dataclass

from apps.dashboard.constants import ALL_CLIENTS_LABEL, ALL_PROJECTS_LABEL
from core.exceptions import InvalidRequestError
from core.utils.text import to_text

"""BKD.010.003 - Filtros del dashboard
Valida el objeto {proyecto, cliente} que manda js_main.html.
"""


@dataclass(frozen=True, slots=True)
class DashboardFilters:
    """Filtros por proyecto y cliente; cadena vacia significa todos."""

    project_id: str = ""
    client: str = ""

    @property
    def is_empty(self) -> bool:
        """Indica si se pidio la vista general sin filtros."""
        return not self.project_id and not self.client


def parse_dashboard_filters(payload: object) -> DashboardFilters:
    """
    Convierte el objeto de filtros del frontend.

    Args:
        payload: None o un objeto con las llaves proyecto y cliente.

    Returns:
        Los filtros normalizados.

    Raises:
        InvalidRequestError: Cuando el payload no es un objeto.
    """
    if payload is None:
        return DashboardFilters()

    if not isinstance(payload, dict):
        raise InvalidRequestError("Los filtros deben ser un objeto.")

    project_id = to_text(payload.get("proyecto"))
    client = to_text(payload.get("cliente"))

    return DashboardFilters(
        project_id="" if project_id == ALL_PROJECTS_LABEL else project_id,
        client="" if client == ALL_CLIENTS_LABEL else client,
    )
