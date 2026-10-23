"""Detalle: mismos servicios y alcance para sus lecturas iniciales."""

from typing import Any

from rest_framework.request import Request
from rest_framework.response import Response

from apps.aer import rpc as aer
from apps.aer.services import dashboard
from apps.daily.services.ixs_store import run_safely
from apps.dashboard.rpc import get_available_filters
from apps.ejecutivo.rpc import get_executive_dashboard
from apps.portal.api.errors import error_response
from apps.portal.api.operations import OperationsScreen
from core.exceptions import DashboardError


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
