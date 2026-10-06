"""Alertas automaticas del dashboard."""

from collections.abc import Sequence

from apps.dashboard.constants import (
    ALERT_ERROR,
    ALERT_WARNING,
    CRITICAL_DELAY_DAYS,
    RISK_HIGH,
    RISK_STATUS_OPEN,
)
from apps.dashboard.schemas.dashboard_models import (
    DashboardAlert,
    ProjectMetrics,
)
from apps.dashboard.schemas.records import RiskRecord
from core.time_entries.models import TimeEntryBatch

"""BKD.010.012 - Alertas automaticas
Equivale a construirAlertas() y a la alerta de datos de respaldo de
Clockify en getDashboardData().
"""


def build_alerts(
    metrics: Sequence[ProjectMetrics],
    risks: Sequence[RiskRecord],
    time_entry_batch: TimeEntryBatch,
) -> list[DashboardAlert]:
    """
    Construye las alertas del portafolio.

    Args:
        metrics: Indicadores de los proyectos filtrados.
        risks: Todos los riesgos (no solo los filtrados).
        time_entry_batch: Registros de tiempo y su procedencia.

    Returns:
        Las alertas en el orden que muestra el panel.
    """
    alerts: list[DashboardAlert] = []

    if time_entry_batch.is_backup:
        alerts.append(build_backup_alert(time_entry_batch))

    delayed_count = sum(
        1 for metric in metrics if metric.delay_days > CRITICAL_DELAY_DAYS
    )

    if delayed_count:
        alerts.append(
            DashboardAlert(
                alert_type=ALERT_ERROR,
                text=(
                    f"{delayed_count} proyectos con más de "
                    f"{CRITICAL_DELAY_DAYS} días de retraso"
                ),
            ),
        )

    over_budget_count = sum(1 for metric in metrics if metric.etc_hours < 0)

    if over_budget_count:
        alerts.append(
            DashboardAlert(
                alert_type=ALERT_ERROR,
                text=(
                    f"{over_budget_count} proyectos ya sobrepasaron su "
                    "presupuesto de horas"
                ),
            ),
        )

    high_risk_count = sum(
        1
        for risk in risks
        if risk.impact == RISK_HIGH and risk.status == RISK_STATUS_OPEN
    )

    if high_risk_count:
        alerts.append(
            DashboardAlert(
                alert_type=ALERT_WARNING,
                text=f"{high_risk_count} riesgos en nivel ALTO",
            ),
        )

    return alerts


def build_backup_alert(time_entry_batch: TimeEntryBatch) -> DashboardAlert:
    """
    Construye la alerta de horas tomadas del ultimo corte completo.

    Args:
        time_entry_batch: Registros marcados como respaldo.

    Returns:
        La alerta de advertencia.
    """
    backup_date = time_entry_batch.backup_date or "fecha no disponible"

    return DashboardAlert(
        alert_type=ALERT_WARNING,
        text=(
            "Clockify no pudo actualizarse. Se muestran datos del último "
            f"corte completo: {backup_date}. "
            f"{time_entry_batch.backup_error}"
        ),
    )
