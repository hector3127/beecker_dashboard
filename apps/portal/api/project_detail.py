"""Detalle: mismos servicios y alcance para sus lecturas iniciales."""

from typing import Any

from rest_framework.request import Request
from rest_framework.response import Response

from apps.aer import rpc as aer
from apps.aer.services import dashboard
from apps.azure_devops.rpc import get_project_raid
from apps.clockify import project_rpc
from apps.daily.ixs_rpc import build_store_sheets
from apps.daily.services.ixs_planning import read_resources
from apps.daily.services.ixs_store import run_safely
from apps.dashboard.rpc import get_available_filters
from apps.ejecutivo.rpc import get_executive_dashboard
from apps.portal.api.errors import error_response
from apps.portal.api.operations import OperationsScreen
from core.exceptions import DashboardError
from core.sheets.factory import build_sheet_repository


def aer_dashboard(project_id: str) -> dict[str, Any]:
    """Construye getDashboardAERTYMProyecto sin transporte RPC."""

    def load() -> dict[str, Any]:
        store = aer.build_store()
        return dashboard.build_dashboard(
            store, project_id, aer.build_hours(store)
        )

    return run_safely(load)


class ProjectRead(OperationsScreen):
    """Conserva el permiso y alcance total exigidos por estas lecturas RPC.

    Los datos ejecutivos todavía incluyen bloques de todo el portafolio.
    No se abre acceso limitado hasta poder recortarlos en sus servicios.
    """

    def load(self, project_id: str) -> dict[str, Any]:
        """Carga del servicio concreto, definida en cada endpoint."""
        raise NotImplementedError

    def get(self, request: Request, project_id: str = "") -> Response:
        """Contrato original en {data, meta}, con errores públicos estables."""
        try:
            return self.body(self.load(project_id))
        except DashboardError as error:
            return error_response(
                error.http_status, error.code, error.build_message()
            )


class ProjectFiltersView(ProjectRead):
    """Metadatos para reconocer el servicio del proyecto antes de cargarlo."""

    def load(self, project_id: str) -> dict[str, Any]:
        """Lee los mismos metadatos de servicio y cliente."""
        return get_available_filters()


class ProjectExecutiveView(ProjectRead):
    """Dashboard IXB, SaaS, RaaS y vista ejecutiva anterior."""

    def load(self, project_id: str) -> dict[str, Any]:
        """Invoca el servicio ejecutivo existente con el ID exacto."""
        return get_executive_dashboard(project_id)


class ProjectAerView(ProjectRead):
    """Dashboard AER/T&M, sin cambiar sus horas ni sus reglas de salud."""

    def load(self, project_id: str) -> dict[str, Any]:
        """Construye AER/T&M con las fuentes y manejo de errores existentes."""
        return aer_dashboard(project_id)


def tasks_dashboard(project_id: str) -> dict[str, Any]:
    """Mismo resumen de tasks, tags y rango de Clockify del RPC anterior."""
    return run_safely(
        lambda: project_rpc.tasks_summary(build_sheet_repository(), project_id)
    )


def stages_dashboard(project_id: str) -> dict[str, Any]:
    """Mismas fases históricas y suspensiones del proyecto."""
    return run_safely(
        lambda: project_rpc.project_stages(build_sheet_repository(), project_id)
    )


def resources_dashboard(project_id: str) -> dict[str, Any]:
    """Misma lectura de asignaciones y estados por proyecto."""
    return run_safely(lambda: read_resources(build_store_sheets(), project_id))


class ProjectRaidView(ProjectRead):
    """RAID diferido del ejecutivo, sin ampliar alcance respecto al RPC."""

    def load(self, project_id: str) -> dict[str, Any]:
        """Invoca el servicio de Azure y pendientes existente."""
        return get_project_raid(project_id)


class ProjectTasksView(ProjectRead):
    """Horas por task e inversión, sin otro recálculo de consumos."""

    def load(self, project_id: str) -> dict[str, Any]:
        """Entrega el mismo resumen de Clockify."""
        return tasks_dashboard(project_id)


def records_dashboard(project_id: str) -> dict[str, Any]:
    """Mismos registros detallados, rango y etiquetas del RPC de Clockify."""
    return run_safely(
        lambda: project_rpc.project_entries(
            build_sheet_repository(), project_id
        )
    )


class ProjectRecordsView(ProjectRead):
    """Registros del proyecto con el alcance total del transporte anterior."""

    def load(self, project_id: str) -> dict[str, Any]:
        """Invoca el servicio existente sin filtrar ni recalcular horas."""
        return records_dashboard(project_id)


class ProjectStagesView(ProjectRead):
    """Histórico diferido para completar la línea de tiempo."""

    def load(self, project_id: str) -> dict[str, Any]:
        """Entrega las etapas del ID exacto, incluidos CR y sprints."""
        return stages_dashboard(project_id)


class ProjectResourcesView(ProjectRead):
    """Estado de las asignaciones del proyecto, solo lectura."""

    def load(self, project_id: str) -> dict[str, Any]:
        """Entrega los mismos estados de recursos que ixsRecursosLeer."""
        return resources_dashboard(project_id)
