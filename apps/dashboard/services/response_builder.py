"""Construccion del JSON que espera js_main.html."""

from collections.abc import Sequence
from datetime import UTC, datetime

from apps.dashboard.constants import (
    COLOR_BLUE,
    COLOR_GRAY,
    COLOR_GREEN,
    COLOR_YELLOW,
    TOP_PROGRESS_LIMIT,
)
from apps.dashboard.schemas.dashboard_models import (
    DashboardAlert,
    KpiDelta,
    PortfolioHealth,
    PortfolioKpis,
    ProjectMetrics,
    WeeklyHours,
)
from core.utils.cell_types import CellValue
from core.utils.numbers import round_half_up

"""BKD.010.017 - Contrato JSON del dashboard
Arma la respuesta con las mismas llaves que regresaba getDashboardData()
para que el frontend original funcione sin cambios.
"""

JsonObject = dict[str, object]


def build_dashboard_response(
    metrics: Sequence[ProjectMetrics],
    kpis: PortfolioKpis,
    delta: KpiDelta,
    alerts: Sequence[DashboardAlert],
    health: PortfolioHealth,
    top_risks: list[dict[str, CellValue]],
    weekly_hours: WeeklyHours,
    delivery_managers: dict[str, str],
    is_backup_data: bool,
) -> JsonObject:
    """
    Construye la respuesta completa del dashboard.

    Args:
        metrics: Indicadores de los proyectos filtrados.
        kpis: KPIs del portafolio.
        delta: Variacion contra la semana anterior.
        alerts: Alertas automaticas.
        health: Resumen de salud del portafolio.
        top_risks: Riesgos principales.
        weekly_hours: Horas de la ultima semana.
        delivery_managers: Delivery Manager por proyecto.
        is_backup_data: Indica si las horas vienen de un respaldo.

    Returns:
        El diccionario listo para serializar a JSON.
    """
    return {
        "kpis": build_kpis_json(kpis, delta),
        "estadoDona": build_status_donut_json(kpis),
        "avancePorProyecto": build_progress_json(metrics),
        "alertas": [
            {"tipo": alert.alert_type, "texto": alert.text} for alert in alerts
        ],
        "saludPortafolio": {
            "aTiempo": health.on_time,
            "enRiesgo": health.at_risk,
            "critica": health.critical,
            "estadoGeneral": health.overall_status,
        },
        "rentabilidad": build_profitability_json(metrics),
        "topRiesgos": top_risks,
        "tabla": [
            build_table_row_json(metric, weekly_hours, delivery_managers)
            for metric in metrics
        ],
        "ultimaActualizacion": build_utc_timestamp(),
        "clockifyDatosDeRespaldo": is_backup_data,
    }


def build_kpis_json(kpis: PortfolioKpis, delta: KpiDelta) -> JsonObject:
    """
    Construye el bloque kpis con sus llaves originales.

    Args:
        kpis: KPIs del portafolio.
        delta: Variacion contra la semana anterior.

    Returns:
        El bloque kpis del JSON.
    """
    return {
        "totalProyectos": kpis.total_projects,
        "activos": kpis.active_projects,
        "enPausa": kpis.paused_projects,
        "planificacion": kpis.planning_projects,
        "cerrados": kpis.closed_projects,
        "riesgosAltos": kpis.high_risks,
        "budgetTotal": kpis.budget_total,
        "burnTotal": kpis.burn_total,
        "etcTotal": kpis.etc_total,
        "velocityPromedio": kpis.average_velocity,
        "avancePromedio": kpis.average_progress,
        "horasSemanaReal": kpis.weekly_hours,
        "focoRojoSemana": kpis.weekly_red_flags,
        "margenPromedio": kpis.average_margin,
        "burnPct": kpis.burn_percent,
        "etcPct": kpis.etc_percent,
        "delta": build_delta_json(delta),
    }


def build_delta_json(delta: KpiDelta) -> JsonObject:
    """
    Construye el bloque delta; queda vacio si no hay snapshot.

    Args:
        delta: Variacion contra la semana anterior.

    Returns:
        El bloque delta del JSON.
    """
    delta_json: JsonObject = {
        "activos": delta.active_projects,
        "avancePromedio": delta.average_progress,
        "horasSemanaReal": delta.weekly_hours,
        "riesgosAltos": delta.high_risks,
        "focoRojoSemana": delta.weekly_red_flags,
        "margenPromedio": delta.average_margin,
    }

    if all(value is None for value in delta_json.values()):
        return {}

    return delta_json


def build_status_donut_json(kpis: PortfolioKpis) -> list[JsonObject]:
    """
    Construye los segmentos de la grafica de dona por estado.

    Args:
        kpis: KPIs del portafolio.

    Returns:
        Los segmentos con etiqueta, valor y color.
    """
    return [
        {
            "label": "Activos",
            "value": kpis.active_projects,
            "color": COLOR_GREEN,
        },
        {
            "label": "En Pausa",
            "value": kpis.paused_projects,
            "color": COLOR_YELLOW,
        },
        {
            "label": "Planificación",
            "value": kpis.planning_projects,
            "color": COLOR_BLUE,
        },
        {
            "label": "Cerrados",
            "value": kpis.closed_projects,
            "color": COLOR_GRAY,
        },
    ]


def build_progress_json(
    metrics: Sequence[ProjectMetrics],
) -> list[JsonObject]:
    """
    Construye el top 6 de proyectos con mayor avance.

    Args:
        metrics: Indicadores de los proyectos filtrados.

    Returns:
        Proyectos con nombre, avance y riesgo.
    """
    sorted_metrics = sorted(
        metrics,
        key=lambda metric: metric.progress_percent,
        reverse=True,
    )

    return [
        {
            "nombre": metric.project.display_name,
            "avance": metric.progress_percent,
            "riesgo": metric.risk_level,
        }
        for metric in sorted_metrics[:TOP_PROGRESS_LIMIT]
    ]


def build_profitability_json(
    metrics: Sequence[ProjectMetrics],
) -> list[JsonObject]:
    """
    Construye los puntos de la grafica de rentabilidad.

    Args:
        metrics: Indicadores de los proyectos filtrados.

    Returns:
        Proyectos con margen conocido.
    """
    return [
        {
            "nombre": metric.project.display_name,
            "margen": metric.margin_percent,
            "avance": metric.progress_percent,
            "budget": metric.budget_hours,
            "riesgo": metric.risk_level,
        }
        for metric in metrics
        if metric.margin_percent is not None
    ]


def build_table_row_json(
    metric: ProjectMetrics,
    weekly_hours: WeeklyHours,
    delivery_managers: dict[str, str],
) -> JsonObject:
    """
    Construye una fila de la tabla de proyectos.

    Args:
        metric: Indicadores del proyecto.
        weekly_hours: Horas de la ultima semana.
        delivery_managers: Delivery Manager por proyecto.

    Returns:
        La fila con las llaves originales.
    """
    project_id = metric.project.project_id

    return {
        "idProyecto": project_id,
        "proyecto": metric.project.display_name,
        "cliente": metric.project.client,
        "estado": metric.project.status,
        "riesgo": metric.risk_level,
        "avance": metric.progress_percent,
        "budget": metric.budget_hours,
        "burn": metric.burn_hours,
        "etc": metric.etc_hours,
        "desviacion": metric.delay_days,
        "deliveryManager": delivery_managers.get(project_id, ""),
        "horasSemana": round_half_up(
            weekly_hours.hours_by_project.get(project_id, 0.0),
            2,
        ),
        "margen": metric.margin_percent,
        "tendencia": metric.trend,
    }


def build_utc_timestamp() -> str:
    """
    Genera la fecha actual como Date.toISOString() de JavaScript.

    Returns:
        Fecha UTC con milisegundos y sufijo Z.
    """
    utc_now = datetime.now(UTC)

    return utc_now.isoformat(timespec="milliseconds").replace("+00:00", "Z")
