"""Capacidad instalada del equipo: una lectura del mes completo."""

import re

from rest_framework.exceptions import ParseError
from rest_framework.request import Request
from rest_framework.response import Response

from apps.capacidad.services.team_capacity import (
    DEFAULT_WORKDAY,
    build_team_capacity,
)
from apps.portal.api.operations import OperationsScreen
from core.exceptions import DashboardError, describe_error
from core.sheets.factory import build_sheet_repository


def _month(request: Request) -> str:
    """Exige un mes explicito y valido."""
    month = request.query_params.get("mes", "")
    if not re.fullmatch(r"[0-9]{4}-(0[1-9]|1[0-2])", month):
        raise ParseError("Selecciona un mes válido (AAAA-MM).")
    return month


def _workday(request: Request) -> float:
    """Jornada diaria; entre 1 y 24 horas, 8 si falta."""
    text = request.query_params.get("jornada", "")
    try:
        hours = float(text) if text else DEFAULT_WORKDAY
    except ValueError:
        raise ParseError("La jornada debe ser un número.") from None
    if not 1 <= hours <= 24:
        raise ParseError("La jornada debe estar entre 1 y 24 horas.")
    return hours


class CapacityDailyView(OperationsScreen):
    """Personas vigentes, horas de Clockify por proyecto y dia, indicadores."""

    def get(self, request: Request) -> Response:
        """Entrega la matriz del mes; sin Sheets responde ok False."""
        month, workday = _month(request), _workday(request)
        try:
            data = build_team_capacity(build_sheet_repository(), month, workday)
        except DashboardError as error:
            return self.body({"ok": False, "error": describe_error(error)})
        return self.body(data)
