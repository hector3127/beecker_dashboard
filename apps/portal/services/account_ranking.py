"""Ranking de cuentas por la salud de sus proyectos en ejecucion."""

from collections.abc import Sequence

from apps.portal.constants import TOP_ACCOUNTS
from apps.portal.schemas import AccountRank, ProjectView
from apps.portal.services.portfolio_summary import (
    count_health,
    percent_of,
    select_in_progress,
)
from apps.portal.services.slugs import build_slug

"""BKD.120.021 - Top cuentas
Mientras no exista la fuente de ingresos y margen, las cuentas se ordenan
por la salud de sus proyectos en ejecucion:
- Sanas: todos sus proyectos en tiempo; primero las de mas proyectos.
- No sanas: con proyectos criticos o en riesgo; primero las de mas
  criticos.
"""


def rank_accounts(
    projects: Sequence[ProjectView],
) -> tuple[tuple[AccountRank, ...], tuple[AccountRank, ...]]:
    """
    Arma el top de cuentas sanas y no sanas.

    Args:
        projects: Todos los proyectos.

    Returns:
        (sanas, no sanas), cada una con hasta TOP_ACCOUNTS cuentas.
    """
    by_client: dict[str, list[ProjectView]] = {}

    for item in select_in_progress(projects):
        if item.client:
            by_client.setdefault(item.client, []).append(item)

    ranks = [_build_rank(name, items) for name, items in by_client.items()]
    healthy = sorted(
        (
            rank
            for rank in ranks
            if rank.health.critical == 0 and rank.health.at_risk == 0
        ),
        key=lambda rank: (-rank.in_progress, rank.name),
    )
    unhealthy = sorted(
        (
            rank
            for rank in ranks
            if rank.health.critical > 0 or rank.health.at_risk > 0
        ),
        key=lambda rank: (
            -rank.health.critical,
            -rank.health.at_risk,
            rank.on_time_percent,
            rank.name,
        ),
    )

    return tuple(healthy[:TOP_ACCOUNTS]), tuple(unhealthy[:TOP_ACCOUNTS])


def _build_rank(name: str, projects: Sequence[ProjectView]) -> AccountRank:
    """Resume una cuenta."""
    health = count_health(projects)

    return AccountRank(
        name=name,
        slug=build_slug(name),
        in_progress=len(projects),
        health=health,
        on_time_percent=percent_of(health.on_time, health.total),
    )
