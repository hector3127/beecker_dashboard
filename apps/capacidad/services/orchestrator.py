"""Coordinacion de las dos consultas de Capacidad instalada."""

import logging
from collections.abc import Callable
from datetime import date
from typing import Any

from apps.capacidad.constants import SHEET_BANDS, SHEET_MPB, SHEET_RESOURCES
from apps.capacidad.services.capacity_base import (
    CapacitySources,
    build_capacity_base,
    parse_month,
    read_optional_projects,
    to_argument_text,
)
from apps.capacidad.services.daily_hours import (
    ReportLoader,
    build_project_daily_hours,
    is_valid_month,
)
from apps.capacidad.services.mpb_projects import load_mpb_projects
from apps.capacidad.services.project_range import (
    AzureIterationSource,
    resolve_project_range,
)
from apps.capacidad.services.sheet_table import read_sheet_table
from apps.dashboard.services.delivery_managers import load_delivery_managers
from core.exceptions import DashboardError, describe_error
from core.sheets import sheet_names
from core.sheets.protocols import SheetReader

"""BKD.050.014 - Orquestador de Capacidad instalada
Equivale a capacidadInstaladaBase(mes) y a
capacidadInstaladaDatosProyecto(id, iteration, mes, forzar).
"""

logger = logging.getLogger(__name__)

JsonObject = dict[str, Any]

BAND_HEADERS = [["nombre", "recurso"], ["rol"]]
RESOURCE_HEADERS = [
    ["proyecto", "id proyecto", "id proyecto azure"],
    ["nombre del recurso", "recurso", "nombre"],
]


def load_capacity_base(
    build_reader: Callable[[], SheetReader],
    month: object,
    today: date,
) -> JsonObject:
    """
    Lee las hojas y arma las asignaciones del mes.

    Args:
        build_reader: Crea el repositorio de Sheets.
        month: Mes YYYY-MM; vacio para el mes actual.
        today: Fecha local de hoy.

    Returns:
        El resultado de capacidadInstaladaBase() o {"ok": False, "error"}.
    """
    try:
        month_text = parse_month(month, today)
        reader = build_reader()
        reader.prefetch(
            [
                SHEET_BANDS,
                SHEET_RESOURCES,
                sheet_names.SHEET_PROJECTS,
                sheet_names.SHEET_PROJECTS_HISTORY,
                SHEET_MPB,
            ],
        )
        sources = CapacitySources(
            bands=read_sheet_table(reader, SHEET_BANDS, BAND_HEADERS),
            resources=read_sheet_table(
                reader,
                SHEET_RESOURCES,
                RESOURCE_HEADERS,
            ),
            projects=read_optional_projects(reader),
            delivery_managers=load_delivery_managers(reader),
            mpb_projects=load_mpb_projects(reader),
        )

        return build_capacity_base(
            sources,
            month_text,
            today.strftime("%Y-%m"),
        )
    except DashboardError as error:
        logger.warning("Capacidad instalada no disponible: %s", error.detail)
        return {"ok": False, "error": describe_error(error)}


def load_project_data(
    request: tuple[object, object, object, object],
    build_reader: Callable[[], SheetReader],
    build_azure_source: Callable[[], AzureIterationSource],
    build_report_loader: Callable[[SheetReader], ReportLoader],
) -> JsonObject:
    """
    Calcula las horas reales de un proyecto en el mes.

    Args:
        request: ID, Iteration Path, mes y forzar, tal como llegan del
            frontend.
        build_reader: Crea el repositorio de Sheets.
        build_azure_source: Crea el acceso a Azure DevOps.
        build_report_loader: Crea el lector de reportes de Clockify.

    Returns:
        El resultado de capacidadInstaladaDatosProyecto().
    """
    project_id, iteration_path, month, force_refresh = request
    month_text = to_argument_text(month)

    if not is_valid_month(month_text):
        return {"ok": False, "error": "Mes inválido"}

    project_text = to_argument_text(project_id)
    should_refresh = bool(force_refresh)

    try:
        reader = build_reader()
    except DashboardError as error:
        return {"ok": False, "error": describe_error(error)}

    project_range = resolve_project_range(
        project_text,
        to_argument_text(iteration_path),
        should_refresh,
        lambda: load_mpb_projects(reader),
        build_azure_source,
    )

    return build_project_daily_hours(
        project_text,
        month_text,
        should_refresh,
        project_range,
        build_report_loader(reader),
    )
