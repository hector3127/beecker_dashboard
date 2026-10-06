"""Orquestador que arma el dashboard ejecutivo completo."""

from dataclasses import dataclass
from datetime import datetime

from apps.dashboard.schemas.dashboard_filters import DashboardFilters
from apps.dashboard.services.alerts import build_alerts
from apps.dashboard.services.delivery_managers import load_delivery_managers
from apps.dashboard.services.filters import apply_filters
from apps.dashboard.services.kpi_calculator import calculate_portfolio_kpis
from apps.dashboard.services.kpi_history import KpiHistoryService
from apps.dashboard.services.portfolio_costs import calculate_portfolio_costs
from apps.dashboard.services.portfolio_health import (
    summarize_portfolio_health,
)
from apps.dashboard.services.project_metrics import (
    build_project_metrics,
    calculate_burn_by_project,
)
from apps.dashboard.services.record_reader import (
    read_project_records,
    read_risk_records,
    read_sprint_records,
)
from apps.dashboard.services.response_builder import (
    JsonObject,
    build_dashboard_response,
)
from apps.dashboard.services.top_risks import build_top_risks
from apps.dashboard.services.weekly_hours import calculate_weekly_hours
from core.sheets import sheet_names
from core.sheets.protocols import SheetReader, SheetWriter
from core.time_entries.protocols import TimeEntryProvider
from core.time_entries.resource_rates import (
    load_costing_rate_by_resource,
)

"""BKD.010.018 - Orquestador del dashboard
Equivale a getDashboardData() de ProyectosService.gs: lee las hojas una
sola vez, calcula los indicadores y arma la respuesta.
"""

DASHBOARD_SHEETS = (
    sheet_names.SHEET_PROJECTS,
    sheet_names.SHEET_RISKS,
    sheet_names.SHEET_RESOURCES,
    sheet_names.SHEET_SPRINTS,
    sheet_names.SHEET_SALARY_BANDS,
    sheet_names.SHEET_MASTER_RATES,
    sheet_names.SHEET_PROJECTS_HISTORY,
    sheet_names.SHEET_DASHBOARD_KPI_HISTORY,
)


@dataclass(frozen=True, slots=True)
class DashboardResult:
    """Respuesta del dashboard y si se puede guardar en cache."""

    payload: JsonObject
    is_cacheable: bool


class DashboardOrchestrator:
    """Coordina los servicios que calculan el dashboard."""

    def __init__(
        self,
        reader: SheetReader,
        writer: SheetWriter,
        time_entry_provider: TimeEntryProvider,
    ) -> None:
        self._reader = reader
        self._time_entry_provider = time_entry_provider
        self._history_service = KpiHistoryService(reader, writer)

    def build_dashboard(
        self,
        filters: DashboardFilters,
        now: datetime,
    ) -> DashboardResult:
        """
        Calcula todos los KPIs y datasets del dashboard.

        Args:
            filters: Filtros por proyecto y cliente.
            now: Fecha y hora local actual.

        Returns:
            La respuesta del dashboard.
        """
        self._reader.prefetch(DASHBOARD_SHEETS)

        projects = read_project_records(self._reader)
        risks = read_risk_records(self._reader)
        time_entry_batch = self._time_entry_provider.load_time_entries()
        time_entries = time_entry_batch.entries

        costs = calculate_portfolio_costs(
            self._reader.read_as_objects(sheet_names.SHEET_RESOURCES),
            load_costing_rate_by_resource(self._reader),
            time_entries,
        )
        burn_by_project = calculate_burn_by_project(time_entries)

        metrics = [
            build_project_metrics(
                project,
                burn_by_project,
                risks,
                costs,
                now,
            )
            for project in apply_filters(projects, filters)
        ]
        project_ids = {metric.project.project_id for metric in metrics}
        weekly_hours = calculate_weekly_hours(project_ids, time_entries, now)

        kpis = calculate_portfolio_kpis(
            metrics,
            risks,
            read_sprint_records(self._reader),
            weekly_hours,
        )

        # El comparativo se calcula antes de guardar el snapshot de hoy
        # para no compararse contra si mismo. Solo la vista general sin
        # filtros alimenta el historico.
        delta = self._history_service.calculate_weekly_delta(kpis, now)
        is_cacheable = filters.is_empty and not time_entry_batch.is_backup

        if is_cacheable:
            self._history_service.save_snapshot(kpis, now)

        payload = build_dashboard_response(
            metrics=metrics,
            kpis=kpis,
            delta=delta,
            alerts=build_alerts(metrics, risks, time_entry_batch),
            health=summarize_portfolio_health(metrics),
            top_risks=build_top_risks(risks, projects, project_ids),
            weekly_hours=weekly_hours,
            delivery_managers=load_delivery_managers(self._reader),
            is_backup_data=time_entry_batch.is_backup,
        )

        return DashboardResult(payload=payload, is_cacheable=is_cacheable)
