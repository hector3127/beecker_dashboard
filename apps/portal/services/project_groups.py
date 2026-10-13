"""Proyectos en ejecucion y en tiempo agrupados por Delivery Manager."""

from collections.abc import Sequence

from apps.dashboard.constants import HEALTH_ON_TIME
from apps.portal.schemas import ProjectGroup, ProjectView
from apps.portal.services.manager_detail import (
    STATUS_ORDER,
    build_project_row,
    classify_status,
)
from apps.portal.services.portfolio_summary import (
    count_health,
    select_in_progress,
)
from apps.portal.services.slugs import build_slug

"""BKD.120.019 - Listas agrupadas por Delivery Manager
Arma las pantallas "Proyectos en ejecucion" y "Proyectos en tiempo": un
grupo por Delivery Manager (el de mas proyectos primero) con sus
proyectos ordenados de los que necesitan atencion a los que van bien.
"""


def select_on_time(projects: Sequence[ProjectView]) -> list[ProjectView]:
    """
    Proyectos en ejecucion que van en tiempo.

    Args:
        projects: Todos los proyectos.

    Returns:
        Solo los en ejecucion con salud "A tiempo".
    """
    return [
        item
        for item in select_in_progress(projects)
        if item.health == HEALTH_ON_TIME
    ]


def build_project_groups(
    projects: Sequence[ProjectView],
    only_on_time: bool,
) -> tuple[ProjectGroup, ...]:
    """
    Agrupa los proyectos en ejecucion por Delivery Manager.

    Args:
        projects: Todos los proyectos.
        only_on_time: True para dejar solo los que van en tiempo.

    Returns:
        Un grupo por Delivery Manager con al menos un proyecto.
    """
    selected = (
        select_on_time(projects)
        if only_on_time
        else select_in_progress(projects)
    )
    by_manager: dict[str, list[ProjectView]] = {}

    for item in selected:
        by_manager.setdefault(item.delivery_manager, []).append(item)

    names = sorted(by_manager, key=lambda name: (-len(by_manager[name]), name))

    return tuple(
        _build_group(name, by_manager[name], only_on_time) for name in names
    )


def _build_group(
    name: str,
    projects: Sequence[ProjectView],
    only_on_time: bool,
) -> ProjectGroup:
    """Arma el grupo de un Delivery Manager."""
    ordered = sorted(
        projects,
        key=lambda item: (
            STATUS_ORDER[classify_status(item)],
            item.client,
            item.name,
        ),
    )

    return ProjectGroup(
        name=name,
        slug=build_slug(name),
        summary=_describe(projects, only_on_time),
        rows=tuple(build_project_row(item) for item in ordered),
    )


def _describe(projects: Sequence[ProjectView], only_on_time: bool) -> str:
    """Resumen corto: "9 proyectos · 6 en tiempo · 2 en riesgo"."""
    total = len(projects)
    plural = "" if total == 1 else "s"

    if only_on_time:
        return f"{total} proyecto{plural} en tiempo"

    health = count_health(projects)
    parts = [f"{total} proyecto{plural}", f"{health.on_time} en tiempo"]

    if health.at_risk:
        parts.append(f"{health.at_risk} en riesgo")

    if health.critical:
        word = "crítico" if health.critical == 1 else "críticos"
        parts.append(f"{health.critical} {word}")

    return " · ".join(parts)
