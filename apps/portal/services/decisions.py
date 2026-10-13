"""Proyectos que requieren una decision de la direccion."""

from collections.abc import Sequence

from apps.dashboard.constants import HEALTH_AT_RISK, HEALTH_CRITICAL, RISK_HIGH
from apps.portal.constants import DECISION_DELAY_DAYS, DECISION_LIMIT
from apps.portal.schemas import DecisionItem, ProjectView
from apps.portal.services.portfolio_summary import select_in_progress
from core.utils.numbers import round_half_up_int

"""BKD.120.006 - Requieren decision
Toma los proyectos en ejecucion criticos o en riesgo, primero los
criticos y con mas retraso, y explica por que con los datos reales.
"""

ACTION_BUDGET = "Decidir si se aprueba un ajuste de presupuesto"
ACTION_DELAY = "Revisar el plan de recuperación"
ACTION_RISK = "Revisar los riesgos abiertos y definir responsables"


def build_decisions(projects: Sequence[ProjectView]) -> list[DecisionItem]:
    """
    Arma la lista de proyectos que requieren decision.

    Args:
        projects: Todos los proyectos.

    Returns:
        Hasta DECISION_LIMIT proyectos, los mas urgentes primero.
    """
    candidates = [
        item
        for item in select_in_progress(projects)
        if item.health in (HEALTH_CRITICAL, HEALTH_AT_RISK)
    ]
    candidates.sort(
        key=lambda item: (
            item.health != HEALTH_CRITICAL,
            -item.delay_days,
            -_budget_used_percent(item),
            item.name,
        ),
    )

    return [_to_decision(item) for item in candidates[:DECISION_LIMIT]]


def _budget_used_percent(project: ProjectView) -> int:
    """Porcentaje del presupuesto en horas que ya se uso."""
    if project.budget_hours <= 0:
        return 0

    return round_half_up_int(project.burn_hours * 100 / project.budget_hours)


def _to_decision(project: ProjectView) -> DecisionItem:
    """Convierte un proyecto en su renglon de decision."""
    used = _budget_used_percent(project)

    if used > 100:
        reason = f"Ya usó {used}% de su presupuesto: excede en {used - 100}%."
        action = ACTION_BUDGET
    elif project.delay_days >= DECISION_DELAY_DAYS:
        reason = (
            f"Va {project.delay_days} días atrasado frente a su plan "
            f"y lleva {project.progress_percent}% de avance."
        )
        action = ACTION_DELAY
    elif project.risk_level == RISK_HIGH:
        reason = "Tiene un riesgo alto abierto sin resolver."
        action = ACTION_RISK
    else:
        reason = (
            f"Su salud está en riesgo con {project.progress_percent}% "
            "de avance."
        )
        action = ACTION_DELAY

    return DecisionItem(
        project_id=project.project_id,
        name=project.name,
        delivery_manager=project.delivery_manager,
        client=project.client,
        is_critical=project.health == HEALTH_CRITICAL,
        reason=reason,
        action=action,
    )
