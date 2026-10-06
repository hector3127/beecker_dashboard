"""Funciones de Capacidad instalada expuestas al frontend por RPC."""

from datetime import date
from typing import Any

from django.utils import timezone

from apps.capacidad.azure_source import GatewayIterationSource
from apps.capacidad.services.daily_hours import ReportLoader
from apps.capacidad.services.orchestrator import (
    load_capacity_base,
    load_project_data,
)
from apps.clockify.constants import SHEET_PROJECT_LINKS
from apps.clockify.provider import build_clockify_loader
from apps.clockify.services.time_entry_loader import ProjectReport
from core.rpc.registry import register_rpc
from core.sheets import sheet_names
from core.sheets.factory import build_sheet_repository
from core.sheets.protocols import SheetReader

"""BKD.050.013 - RPC de Capacidad instalada
Registra capacidadInstaladaBase y capacidadInstaladaDatosProyecto con
los mismos nombres y respuestas que en Apps Script.
"""

JsonObject = dict[str, Any]

CLOCKIFY_SHEETS = (
    SHEET_PROJECT_LINKS,
    sheet_names.SHEET_SALARY_BANDS,
    sheet_names.SHEET_MASTER_RATES,
)


@register_rpc("capacidadInstaladaBase")
def get_capacity_base(month: object = None) -> JsonObject:
    """
    Devuelve las asignaciones y bandas del mes.

    Args:
        month: Mes YYYY-MM; vacio para el mes actual.

    Returns:
        {"ok", "mes", "actual", "filas", "personas", ...} o
        {"ok": False, "error"}.
    """
    return load_capacity_base(
        build_sheet_repository,
        month,
        timezone.localdate(),
    )


@register_rpc("capacidadInstaladaDatosProyecto")
def get_capacity_project_data(
    project_id: object = "",
    iteration_path: object = "",
    month: object = "",
    force_refresh: object = False,
) -> JsonObject:
    """
    Devuelve las horas reales del proyecto por persona y dia del mes.

    Args:
        project_id: ID interno (puede traer _S2 o _CR1).
        iteration_path: Iteration Path de Recursos.
        month: Mes YYYY-MM.
        force_refresh: Ignora la cache de Azure y Clockify.

    Returns:
        {"ok", "inicio", "fin", "daily", ...}, {"ok", "fueraMes"} o
        {"ok": False, "error"}.
    """
    return load_project_data(
        (project_id, iteration_path, month, force_refresh),
        build_sheet_repository,
        GatewayIterationSource,
        build_report_loader,
    )


def build_report_loader(reader: SheetReader) -> ReportLoader:
    """
    Crea la funcion que descarga el reporte estricto de Clockify.

    Args:
        reader: Repositorio de Sheets de la peticion.

    Returns:
        La funcion (ID base, rango, forzar) -> reporte.
    """

    def load_report(
        base_id: str,
        date_range: tuple[date, date],
        force_refresh: bool,
    ) -> ProjectReport:
        reader.prefetch(CLOCKIFY_SHEETS)

        return build_clockify_loader(reader).load_strict_project_report(
            base_id,
            date_range,
            force_refresh,
        )

    return load_report
