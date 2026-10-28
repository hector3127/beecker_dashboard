"""Históricos y consumos de EVA con los mismos servicios del portal."""

from typing import Any

from django.template.defaultfilters import floatformat
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect
from rest_framework.exceptions import ParseError
from rest_framework.request import Request
from rest_framework.response import Response

from apps.ejecutivo.rpc import get_aer_tym_consumption
from apps.portal import views
from apps.portal.api.operations import OperationsScreen
from apps.portal.api.plain import plain
from apps.portal.services.closed_aer_burn import fill_closed_burn


def _display(context: dict[str, Any]) -> dict[str, Any]:
    """Mismo formato de cifras que las plantillas, sin duplicarlo en JS."""
    projects = []
    for project in context["projects"]:
        item = plain(project)
        item["url"] = reverse(
            "portal:proyecto_detalle", args=[project.project_id]
        )
        item["display"] = {
            name: str(floatformat(getattr(project, name), precision))
            for name, precision in [
                ("budget", "-2g"),
                ("burn", "-2g"),
                ("etc", "-2g"),
                ("progress", "-1"),
            ]
        }
        item["closed_status"] = "".join(
            str(row.get("estadoHistorico", ""))
            for row in context.get("historic_rows", [])
            if row.get("idProyecto") == project.project_id
        )
        projects.append(item)
    return {"projects": projects, "error": context["error"]}


class Eva3ClosedView(OperationsScreen):
    """AER/T&M finalizados o cancelados en MPB en 2026."""

    def get(self, request: Request) -> Response:
        """Mantiene el año, filtros de estado y orden de la vista anterior."""
        return self.body(_display(views.eva3_closed_data()))


def _payload(request: Request) -> dict[str, Any]:
    if not isinstance(request.data, dict):
        raise ParseError("Se esperaba un objeto JSON.")
    return request.data


@method_decorator(csrf_protect, name="dispatch")
class Eva3ConsumptionView(OperationsScreen):
    """Mismo consumo diferido de hasta dos proyectos AER/T&M."""

    def post(self, request: Request) -> Response:
        """Valida IDs y delega en el servicio original sin recalcular horas."""
        projects = _payload(request).get("proyectos")
        if not isinstance(projects, list) or not 1 <= len(projects) <= 2:
            raise ParseError("Selecciona uno o dos proyectos.")
        if any(not isinstance(p, str) or not p.strip() for p in projects):
            raise ParseError("Los IDs de proyecto deben ser texto no vacío.")
        return self.body(get_aer_tym_consumption(projects))


@method_decorator(csrf_protect, name="dispatch")
class Eva3ClosedBurnView(OperationsScreen):
    """Consulta y guarda el Burn pendiente de un proyecto cerrado."""

    def post(self, request: Request) -> Response:
        """Conserva la escritura en MPB y el error del servicio anterior."""
        project = _payload(request).get("id")
        if not isinstance(project, str) or not project.strip():
            raise ParseError("Falta ID")
        try:
            return self.body(fill_closed_burn(project))
        except Exception as error:  # noqa: BLE001
            return Response(
                {"error": {"code": "closed_burn", "message": str(error)}},
                status=502,
            )
