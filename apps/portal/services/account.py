"""Detalle de una cuenta (cliente) con sus proyectos."""

from collections.abc import Sequence

from apps.dashboard.constants import CATEGORY_PAUSED
from apps.portal.schemas import AccountDetail, AccountRow, ProjectView
from apps.portal.services.manager_detail import (
    ROW_CLASSES,
    STATUS_LABELS,
    STATUS_ORDER,
    build_shares,
    build_status_detail,
    classify_status,
)
from apps.portal.services.portfolio_summary import (
    count_health,
    select_in_progress,
)
from apps.portal.services.slugs import build_slug

"""BKD.120.014 - Detalle de cuenta
Arma la pantalla de una cuenta: cuantos de sus proyectos estan en
ejecucion o suspendidos, como van y el avance en horas de cada uno.
Revenue, margen y cobranza no existen en Sheets y se muestran pendientes.
"""


def find_account(
    projects: Sequence[ProjectView],
    slug: str,
) -> tuple[str, list[ProjectView]] | None:
    """
    Busca una cuenta por su slug.

    Args:
        projects: Todos los proyectos.
        slug: Identificador de la URL.

    Returns:
        El nombre de la cuenta y sus proyectos, o None si no existe.
    """
    for name in sorted({item.client for item in projects if item.client}):
        if build_slug(name) == slug:
            return name, [item for item in projects if item.client == name]

    return None


def build_account_row(project: ProjectView) -> AccountRow:
    """
    Convierte un proyecto en un renglon de la tabla de la cuenta.

    Args:
        project: Proyecto a mostrar.

    Returns:
        El renglon con Delivery Manager, estado y avance.
    """
    status_code = classify_status(project)

    return AccountRow(
        project_id=project.project_id,
        name=project.name,
        delivery_manager=project.delivery_manager,
        status_label=STATUS_LABELS[status_code],
        status_code=status_code,
        detail=build_status_detail(project, status_code),
        progress_percent=project.progress_percent,
        row_class=ROW_CLASSES.get(status_code, ""),
    )


def build_account_detail(
    name: str,
    projects: Sequence[ProjectView],
) -> AccountDetail:
    """
    Arma el detalle de una cuenta.

    Args:
        name: Nombre de la cuenta.
        projects: Proyectos de esa cuenta.

    Returns:
        Totales, tabla de proyectos y reparto por estado.
    """
    in_progress = select_in_progress(projects)
    paused = [
        item for item in projects if item.status_category == CATEGORY_PAUSED
    ]
    listed = sorted(
        [*in_progress, *paused],
        key=lambda item: (
            STATUS_ORDER[classify_status(item)],
            -item.delay_days,
            item.name,
        ),
    )
    health = count_health(in_progress)

    return AccountDetail(
        name=name,
        total=len(listed),
        in_progress=len(in_progress),
        paused=len(paused),
        health=health,
        rows=tuple(build_account_row(item) for item in listed),
        shares=build_shares(health.on_time, health.at_risk, health.critical),
    )
