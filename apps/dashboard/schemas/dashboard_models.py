"""Resultados intermedios del calculo del dashboard."""

from dataclasses import dataclass

from apps.dashboard.schemas.records import ProjectRecord

"""BKD.010.004 - Modelos del dashboard
Estructuras que se pasan entre servicios antes de armar el JSON.
"""


@dataclass(frozen=True, slots=True)
class ProjectMetrics:
    """Indicadores calculados de un proyecto (campos _xxx del original)."""

    project: ProjectRecord
    budget_hours: float
    burn_hours: float
    etc_hours: float
    progress_percent: int
    delay_days: int
    status_category: str
    risk_level: str
    margin_percent: float | None
    trend: str
    health: str


@dataclass(frozen=True, slots=True)
class PortfolioCosts:
    """Costo estimado y real por proyecto."""

    estimated_cost_by_project: dict[str, float]
    actual_cost_by_project: dict[str, float]


@dataclass(frozen=True, slots=True)
class WeeklyHours:
    """Horas FACT y registros foco rojo de los ultimos 7 dias."""

    hours_by_project: dict[str, float]
    total_hours: float
    red_flag_count: int


@dataclass(frozen=True, slots=True)
class PortfolioKpis:
    """KPIs del portafolio filtrado."""

    total_projects: int
    active_projects: int
    paused_projects: int
    planning_projects: int
    closed_projects: int
    high_risks: int
    budget_total: float
    burn_total: float
    etc_total: float
    average_velocity: int
    average_progress: int
    weekly_hours: float
    weekly_red_flags: int
    average_margin: float | None
    burn_percent: int
    etc_percent: int


@dataclass(frozen=True, slots=True)
class KpiDelta:
    """Diferencia de cada KPI contra el snapshot de la semana pasada."""

    active_projects: float | None
    average_progress: float | None
    weekly_hours: float | None
    high_risks: float | None
    weekly_red_flags: float | None
    average_margin: float | None


@dataclass(frozen=True, slots=True)
class DashboardAlert:
    """Alerta automatica del dashboard."""

    alert_type: str
    text: str


@dataclass(frozen=True, slots=True)
class PortfolioHealth:
    """Conteo de proyectos por salud y estado general."""

    on_time: int
    at_risk: int
    critical: int
    overall_status: str
