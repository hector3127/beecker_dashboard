"""Lecturas de capacidad diaria sin depender del adaptador RPC."""

import re

from rest_framework.exceptions import ParseError
from rest_framework.request import Request
from rest_framework.response import Response

from apps.capacidad.rpc import get_capacity_base, get_capacity_project_data
from apps.portal.api.operations import OperationsScreen


def _month(request: Request) -> str:
    """Exige un mes explicito y valido para ambas lecturas."""
    month = request.query_params.get("mes", "")
    if not re.fullmatch(r"[0-9]{4}-(0[1-9]|1[0-2])", month):
        raise ParseError("Selecciona un mes válido (AAAA-MM).")
    return month


class CapacityDailyView(OperationsScreen):
    """Asignaciones y bandas del mes; mismo servicio que el RPC anterior."""

    def get(self, request: Request) -> Response:
        """Entrega las filas sin recalcular horas ni cambiar sus reglas."""
        return self.body(get_capacity_base(_month(request)))


class CapacityDailyProjectView(OperationsScreen):
    """Fechas y horas diarias de una asignacion del mes."""

    def get(self, request: Request) -> Response:
        """Mantiene el rango estricto de proyecto y el forzado de cache."""
        month = _month(request)
        project = request.query_params.get("proyecto", "").strip()
        if not project:
            raise ParseError("Falta el proyecto.")
        return self.body(
            get_capacity_project_data(
                project,
                request.query_params.get("iteration", ""),
                month,
                request.query_params.get("actualizar") == "1",
            )
        )
