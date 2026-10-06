"""KPIs agregados del portafolio filtrado."""

from collections.abc import Collection, Sequence

from apps.dashboard.constants import (
    CATEGORY_ACTIVE,
    CATEGORY_CLOSED,
    CATEGORY_PAUSED,
    CATEGORY_PLANNING,
    RISK_HIGH,
    RISK_STATUS_OPEN,
    SPRINT_STATUS_IN_PROGRESS,
)
from apps.dashboard.schemas.dashboard_models import (
    PortfolioKpis,
    ProjectMetrics,
    WeeklyHours,
)
from apps.dashboard.schemas.records import RiskRecord, SprintRecord
from core.utils.numbers import round_half_up, round_half_up_int

"""BKD.010.010 - KPIs del portafolio
Calcula las tarjetas de KPI de getDashboardData().
"""


def calculate_portfolio_kpis(
    metrics: Sequence[ProjectMetrics],
    risks: Sequence[RiskRecord],
    sprints: Sequence[SprintRecord],
    weekly_hours: WeeklyHours,
) -> PortfolioKpis:
    """
    Calcula los KPIs del portafolio filtrado.

    Args:
        metrics: Indicadores de los proyectos filtrados.
        risks: Riesgos de la hoja Riesgos.
        sprints: Sprints de la hoja Sprints.
        weekly_hours: Horas y focos rojos de la semana.

    Returns:
        Los KPIs del portafolio.
    """
    project_ids = {metric.project.project_id for metric in metrics}
    budget_total = round_half_up(
        sum(metric.budget_hours for metric in metrics),
        2,
    )
    burn_total = round_half_up(
        sum(metric.burn_hours for metric in metrics),
        2,
    )
    etc_total = round_half_up(
        sum(metric.etc_hours for metric in metrics),
        2,
    )

    return PortfolioKpis(
        total_projects=len(metrics),
        active_projects=count_category(metrics, CATEGORY_ACTIVE),
        paused_projects=count_category(metrics, CATEGORY_PAUSED),
        planning_projects=count_category(metrics, CATEGORY_PLANNING),
        closed_projects=count_category(metrics, CATEGORY_CLOSED),
        high_risks=count_open_high_risks(risks, project_ids),
        budget_total=budget_total,
        burn_total=burn_total,
        etc_total=etc_total,
        average_velocity=calculate_average_velocity(sprints, project_ids),
        average_progress=calculate_average_progress(metrics),
        weekly_hours=weekly_hours.total_hours,
        weekly_red_flags=weekly_hours.red_flag_count,
        average_margin=calculate_average_margin(metrics),
        burn_percent=calculate_percent(burn_total, budget_total),
        etc_percent=calculate_percent(etc_total, budget_total),
    )


def count_category(metrics: Sequence[ProjectMetrics], category: str) -> int:
    """
    Cuenta los proyectos de una categoria de estado.

    Args:
        metrics: Indicadores de los proyectos.
        category: Categoria a contar.

    Returns:
        La cantidad de proyectos en la categoria.
    """
    return sum(1 for metric in metrics if metric.status_category == category)


def count_open_high_risks(
    risks: Sequence[RiskRecord],
    project_ids: Collection[str],
) -> int:
    """
    Cuenta los riesgos Altos y Abiertos de los proyectos filtrados.

    Args:
        risks: Riesgos de la hoja Riesgos.
        project_ids: IDs de los proyectos filtrados.

    Returns:
        La cantidad de riesgos altos abiertos.
    """
    return sum(
        1
        for risk in risks
        if risk.impact == RISK_HIGH
        and risk.status == RISK_STATUS_OPEN
        and risk.project_id in project_ids
    )


def calculate_average_velocity(
    sprints: Sequence[SprintRecord],
    project_ids: Collection[str],
) -> int:
    """
    Promedia la velocity de los sprints En curso, como promedioVelocity().

    Args:
        sprints: Sprints de la hoja Sprints.
        project_ids: IDs de los proyectos filtrados.

    Returns:
        La velocity promedio redondeada, o 0 sin sprints en curso.
    """
    velocities = [
        sprint.velocity
        for sprint in sprints
        if sprint.project_id in project_ids
        and sprint.status == SPRINT_STATUS_IN_PROGRESS
    ]

    if not velocities:
        return 0

    return round_half_up_int(sum(velocities) / len(velocities))


def calculate_average_progress(metrics: Sequence[ProjectMetrics]) -> int:
    """
    Promedia el avance de los proyectos filtrados.

    Args:
        metrics: Indicadores de los proyectos.

    Returns:
        El avance promedio redondeado, o 0 sin proyectos.
    """
    if not metrics:
        return 0

    total_progress = sum(metric.progress_percent for metric in metrics)

    return round_half_up_int(total_progress / len(metrics))


def calculate_average_margin(
    metrics: Sequence[ProjectMetrics],
) -> float | None:
    """
    Promedia los margenes conocidos con un decimal.

    Args:
        metrics: Indicadores de los proyectos.

    Returns:
        El margen promedio, o None si ningun proyecto tiene margen.
    """
    margins = [
        metric.margin_percent
        for metric in metrics
        if metric.margin_percent is not None
    ]

    if not margins:
        return None

    return round_half_up(sum(margins) / len(margins), 1)


def calculate_percent(part: float, total: float) -> int:
    """
    Calcula el porcentaje entero de una parte sobre el total.

    Args:
        part: Valor parcial.
        total: Valor total.

    Returns:
        El porcentaje redondeado, o 0 cuando el total es cero.
    """
    if not total:
        return 0

    return round_half_up_int(part / total * 100)
