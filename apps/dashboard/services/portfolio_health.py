"""Resumen de salud del portafolio."""

from collections.abc import Sequence

from apps.dashboard.constants import (
    HEALTH_AT_RISK,
    HEALTH_CRITICAL,
    HEALTH_ON_TIME,
    PORTFOLIO_CRITICAL_RATIO,
    PORTFOLIO_FAIR_RATIO,
    PORTFOLIO_HEALTH_CRITICAL,
    PORTFOLIO_HEALTH_FAIR,
    PORTFOLIO_HEALTH_GOOD,
)
from apps.dashboard.schemas.dashboard_models import (
    PortfolioHealth,
    ProjectMetrics,
)

"""BKD.010.013 - Salud del portafolio
Cuenta proyectos por salud y califica el portafolio: Critica si mas del
40% esta en estado critico, Regular si mas del 20%, Buena en otro caso.
"""


def summarize_portfolio_health(
    metrics: Sequence[ProjectMetrics],
) -> PortfolioHealth:
    """
    Calcula el resumen de salud del portafolio filtrado.

    Args:
        metrics: Indicadores de los proyectos filtrados.

    Returns:
        Conteos por salud y estado general.
    """
    on_time = sum(1 for metric in metrics if metric.health == HEALTH_ON_TIME)
    at_risk = sum(1 for metric in metrics if metric.health == HEALTH_AT_RISK)
    critical = sum(1 for metric in metrics if metric.health == HEALTH_CRITICAL)
    critical_ratio = critical / len(metrics) if metrics else 0.0

    overall_status = PORTFOLIO_HEALTH_GOOD

    if critical_ratio > PORTFOLIO_CRITICAL_RATIO:
        overall_status = PORTFOLIO_HEALTH_CRITICAL
    elif critical_ratio > PORTFOLIO_FAIR_RATIO:
        overall_status = PORTFOLIO_HEALTH_FAIR

    return PortfolioHealth(
        on_time=on_time,
        at_risk=at_risk,
        critical=critical,
        overall_status=overall_status,
    )
