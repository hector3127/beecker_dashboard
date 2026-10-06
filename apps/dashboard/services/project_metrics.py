"""Indicadores calculados por proyecto: burn, ETC, avance y salud."""

from collections.abc import Sequence
from datetime import datetime

from apps.dashboard.constants import (
    CATEGORY_CLOSED,
    CRITICAL_DELAY_DAYS,
    HEALTH_AT_RISK,
    HEALTH_CRITICAL,
    HEALTH_ON_TIME,
    MAX_PROGRESS_PERCENT,
    RISK_HIGH,
    TREND_DOWN,
    TREND_UP,
)
from apps.dashboard.schemas.dashboard_models import (
    PortfolioCosts,
    ProjectMetrics,
)
from apps.dashboard.schemas.records import ProjectRecord, RiskRecord
from apps.dashboard.services.portfolio_costs import calculate_project_margin
from apps.dashboard.services.project_status import (
    calculate_project_risk_level,
    categorize_project_status,
)
from core.time_entries.models import TimeEntry
from core.utils.dates import days_between
from core.utils.numbers import round_half_up, round_half_up_int

"""BKD.010.009 - Indicadores por proyecto
Calcula los campos que no existen en la hoja Proyectos:
- Burn: horas FACT (Billable) registradas en el proyecto.
- ETC: Budget - Burn; es negativo si se paso del presupuesto.
- Avance: Burn / Budget * 100, acotado a 100.
- Desviacion: dias de retraso contra la fecha fin estimada.
"""


def calculate_burn_by_project(
    time_entries: Sequence[TimeEntry],
) -> dict[str, float]:
    """
    Suma las horas facturables de cada proyecto.

    Args:
        time_entries: Registros de tiempo del portafolio.

    Returns:
        ID de proyecto -> horas FACT.
    """
    burn_by_project: dict[str, float] = {}

    for time_entry in time_entries:
        if not time_entry.is_billable:
            continue

        burn_by_project[time_entry.project_id] = (
            burn_by_project.get(time_entry.project_id, 0.0)
            + time_entry.duration_hours
        )

    return burn_by_project


def build_project_metrics(
    project: ProjectRecord,
    burn_by_project: dict[str, float],
    risks: Sequence[RiskRecord],
    costs: PortfolioCosts,
    now: datetime,
) -> ProjectMetrics:
    """
    Calcula todos los indicadores de un proyecto.

    Args:
        project: Registro del proyecto.
        burn_by_project: Horas FACT por proyecto.
        risks: Riesgos de la hoja Riesgos.
        costs: Costos del portafolio.
        now: Fecha y hora actual.

    Returns:
        Los indicadores del proyecto.
    """
    budget_hours = project.budget_hours
    burn_hours = round_half_up(
        burn_by_project.get(project.project_id, 0.0),
        2,
    )
    etc_hours = round_half_up(budget_hours - burn_hours, 2)
    progress_percent = calculate_progress_percent(budget_hours, burn_hours)
    status_category = categorize_project_status(project.status)
    delay_days = calculate_delay_days(project, status_category, now)
    trend = calculate_trend(
        progress_percent,
        calculate_elapsed_time_percent(project, now),
    )
    risk_level = calculate_project_risk_level(project.project_id, risks)

    return ProjectMetrics(
        project=project,
        budget_hours=budget_hours,
        burn_hours=burn_hours,
        etc_hours=etc_hours,
        progress_percent=progress_percent,
        delay_days=delay_days,
        status_category=status_category,
        risk_level=risk_level,
        margin_percent=calculate_project_margin(project.project_id, costs),
        trend=trend,
        health=calculate_project_health(
            delay_days,
            etc_hours,
            risk_level,
            trend,
        ),
    )


def calculate_progress_percent(budget_hours: float, burn_hours: float) -> int:
    """
    Calcula el avance como horas consumidas sobre presupuesto.

    Args:
        budget_hours: Horas presupuestadas.
        burn_hours: Horas FACT consumidas.

    Returns:
        El avance en porcentaje entero, maximo 100.
    """
    if not budget_hours:
        return 0

    return min(
        MAX_PROGRESS_PERCENT,
        round_half_up_int(burn_hours / budget_hours * 100),
    )


def calculate_delay_days(
    project: ProjectRecord,
    status_category: str,
    now: datetime,
) -> int:
    """
    Calcula los dias de retraso contra la fecha fin estimada.

    Args:
        project: Registro del proyecto.
        status_category: Categoria del estado del proyecto.
        now: Fecha y hora actual.

    Returns:
        Dias de retraso; 0 si no ha vencido o el proyecto esta cerrado.
    """
    end_date = project.end_date

    if end_date is None or now <= end_date:
        return 0

    if status_category == CATEGORY_CLOSED:
        return 0

    return round_half_up_int(days_between(end_date, now))


def calculate_elapsed_time_percent(
    project: ProjectRecord,
    now: datetime,
) -> int | None:
    """
    Calcula el porcentaje de tiempo transcurrido del proyecto.

    Args:
        project: Registro del proyecto.
        now: Fecha y hora actual.

    Returns:
        El porcentaje entre 0 y 100, o None sin fechas validas.
    """
    start_date = project.start_date
    end_date = project.end_date

    if start_date is None or end_date is None or end_date <= start_date:
        return None

    total_seconds = (end_date - start_date).total_seconds()
    elapsed_seconds = min(
        max((now - start_date).total_seconds(), 0.0),
        total_seconds,
    )

    return round_half_up_int(elapsed_seconds / total_seconds * 100)


def calculate_trend(
    progress_percent: int,
    elapsed_time_percent: int | None,
) -> str:
    """
    Indica si el avance va acorde al tiempo transcurrido.

    Args:
        progress_percent: Avance del proyecto.
        elapsed_time_percent: Tiempo transcurrido, si se conoce.

    Returns:
        up si el avance alcanza al tiempo; down si va rezagado.
    """
    if elapsed_time_percent is None:
        return TREND_UP

    if progress_percent >= elapsed_time_percent:
        return TREND_UP

    return TREND_DOWN


def calculate_project_health(
    delay_days: int,
    etc_hours: float,
    risk_level: str,
    trend: str,
) -> str:
    """
    Clasifica la salud del proyecto.

    Un riesgo Medio por si solo no baja a En Riesgo; lo que importa es
    si el proyecto va atrasado respecto al tiempo transcurrido.

    Args:
        delay_days: Dias de retraso.
        etc_hours: Horas restantes del presupuesto.
        risk_level: Nivel de riesgo del proyecto.
        trend: Tendencia del avance.

    Returns:
        Critica, En Riesgo o A tiempo.
    """
    is_critical = (
        delay_days > CRITICAL_DELAY_DAYS
        or etc_hours < 0
        or risk_level == RISK_HIGH
    )

    if is_critical:
        return HEALTH_CRITICAL

    if trend == TREND_DOWN:
        return HEALTH_AT_RISK

    return HEALTH_ON_TIME
