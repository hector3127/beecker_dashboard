"""KPIs de Delivery Managers con el corte actual del portafolio."""

from collections.abc import Sequence

from apps.portal.constants import NO_DELIVERY_MANAGER
from apps.portal.schemas import KpiManagerRow, KpiView, ProjectView
from apps.portal.services.portfolio_summary import (
    count_health,
    percent_of,
    select_in_progress,
    summarize_delivery_managers,
)
from apps.portal.services.time_cost import summarize_time_cost

"""BKD.120.022 - KPIs de Delivery Managers
Por cada Delivery Manager: total de proyectos en ejecucion (TP), T
(desviacion promedio en dias), C (avance promedio) y su salud. El mejor
y el peor se eligen por el porcentaje de proyectos en tiempo, sin contar
los proyectos sin Delivery Manager. El
historico por trimestre y por mes necesita guardar un corte cada mes.
"""

TOTAL_LABEL = "Total"


def build_kpi_view(projects: Sequence[ProjectView]) -> KpiView:
    """
    Arma la tabla de KPIs por Delivery Manager.

    Args:
        projects: Todos los proyectos.

    Returns:
        Las filas, el total y el mejor y peor Delivery Manager.
    """
    rows = tuple(
        KpiManagerRow(
            name=card.name,
            slug=card.slug,
            total=card.in_progress,
            health=card.health,
            on_time_percent=percent_of(card.health.on_time, card.in_progress),
            time_cost=card.time_cost,
        )
        for card in summarize_delivery_managers(projects)
        if card.in_progress > 0
    )
    in_progress = select_in_progress(projects)
    health = count_health(in_progress)
    totals = KpiManagerRow(
        name=TOTAL_LABEL,
        slug="",
        total=len(in_progress),
        health=health,
        on_time_percent=percent_of(health.on_time, len(in_progress)),
        time_cost=summarize_time_cost(in_progress),
    )
    ranked = sorted(
        (row for row in rows if row.name != NO_DELIVERY_MANAGER),
        key=lambda row: (-row.on_time_percent, -row.total, row.name),
    )

    return KpiView(
        rows=rows,
        totals=totals,
        best=ranked[0] if ranked else None,
        worst=ranked[-1] if len(ranked) > 1 else None,
    )
