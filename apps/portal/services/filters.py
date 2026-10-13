"""Filtros de Servicio y Cuenta (solo en Operativa)."""

from collections.abc import Sequence

from apps.portal.schemas import ProjectView

"""BKD.120.008 - Filtros de Operativa
Decision de la reunion: Servicio y Cuenta filtran solo en Operativa.
Ejecutiva y Comercial siempre muestran todo el portafolio.
"""


def filter_projects(
    projects: Sequence[ProjectView],
    service: str,
    client: str,
) -> list[ProjectView]:
    """
    Filtra por servicio y cuenta; un valor vacio no filtra.

    Args:
        projects: Todos los proyectos.
        service: Servicio elegido, o vacio para todos.
        client: Cuenta elegida, o vacio para todas.

    Returns:
        Los proyectos que cumplen ambos filtros.
    """
    return [
        item
        for item in projects
        if (not service or item.service == service)
        and (not client or item.client == client)
    ]


def list_services(projects: Sequence[ProjectView]) -> list[str]:
    """
    Lista los servicios que existen, ordenados.

    Args:
        projects: Todos los proyectos.

    Returns:
        Servicios distintos y no vacios.
    """
    return sorted({item.service for item in projects if item.service})


def list_clients(projects: Sequence[ProjectView]) -> list[str]:
    """
    Lista las cuentas que existen, ordenadas.

    Args:
        projects: Todos los proyectos.

    Returns:
        Cuentas distintas y no vacias.
    """
    return sorted({item.client for item in projects if item.client})
