"""Coordinacion del detalle y del dashboard ejecutivo de un proyecto."""

import logging
from collections.abc import Callable
from datetime import datetime
from typing import Any

from apps.ejecutivo.services.project_dashboard import (
    ExecutiveSources,
    build_executive_dashboard,
)
from apps.ejecutivo.services.project_detail import (
    ProjectDetailSources,
    build_error_detail,
    build_project_detail,
    find_project_row,
)
from apps.ejecutivo.services.project_hours import (
    ProjectEntriesLoader,
    load_hierarchy_entries,
)
from core.exceptions import (
    DashboardError,
    InvalidRequestError,
    SheetsError,
    describe_error,
)
from core.sheets import sheet_names
from core.sheets.protocols import SheetReader
from core.time_entries.models import TimeEntry
from core.time_entries.resource_rates import load_band_info_by_resource
from core.utils.cell_types import SheetRow

"""BKD.040.014 - Orquestador del proyecto
Equivale a getDetalleProyectoCompleto(id) y a
getDashboardEjecutivoProyecto(id): lee las hojas, obtiene las horas y
regresa la respuesta o el error con la forma del original.
"""

logger = logging.getLogger(__name__)

JsonObject = dict[str, Any]

PortfolioLoader = Callable[[], tuple[TimeEntry, ...]]


def load_project_detail(
    reader: SheetReader,
    project_id: str,
    load_project_entries: ProjectEntriesLoader,
    now: datetime,
) -> JsonObject:
    """
    Calcula el detalle por recurso del proyecto.

    Args:
        reader: Repositorio de lectura de Sheets.
        project_id: ID interno del proyecto.
        load_project_entries: Descarga los registros de un proyecto.
        now: Fecha y hora local actual.

    Returns:
        El detalle, o la respuesta vacia con errorServidor.
    """
    try:
        project_rows = reader.read_as_objects(sheet_names.SHEET_PROJECTS)

        if not reader.sheet_exists(sheet_names.SHEET_RESOURCES):
            raise InvalidRequestError(
                'No existe una hoja llamada "Recursos" en el spreadsheet.',
            )

        sources = ProjectDetailSources(
            project_rows=project_rows,
            resource_rows=reader.read_as_objects(sheet_names.SHEET_RESOURCES),
            entries=load_hierarchy_entries(
                project_id,
                project_rows,
                load_project_entries,
            ),
            band_info=load_band_info_by_resource(reader),
        )

        return build_project_detail(project_id, sources, now)
    except DashboardError as error:
        logger.warning("Detalle de %s no disponible: %s", project_id, error)
        return build_error_detail(project_id, describe_error(error))


def load_executive_dashboard(
    reader: SheetReader,
    project_id: str,
    loaders: tuple[ProjectEntriesLoader, PortfolioLoader],
    now: datetime,
) -> JsonObject:
    """
    Calcula el dashboard ejecutivo del proyecto.

    Args:
        reader: Repositorio de lectura de Sheets.
        project_id: ID exacto del proyecto.
        loaders: Horas de un proyecto y horas de todo el portafolio.
        now: Fecha y hora local actual.

    Returns:
        El dashboard, o {"errorServidor", "proyecto": None}.
    """
    load_project_entries, load_portfolio_entries = loaders

    try:
        project_rows = reader.read_as_objects(sheet_names.SHEET_PROJECTS)

        if find_project_row(project_rows, project_id) is None:
            raise InvalidRequestError(
                f'No se encontro el proyecto "{project_id}" en la hoja '
                "Proyectos.",
            )

        portfolio_entries = load_portfolio_entries()
        sources = ExecutiveSources(
            project_rows=project_rows,
            project_values=reader.read_values(sheet_names.SHEET_PROJECTS),
            history_rows=read_optional_rows(
                reader,
                sheet_names.SHEET_PROJECTS_HISTORY,
            ),
            history_values=(
                reader.read_values(sheet_names.SHEET_PROJECTS_HISTORY)
                if reader.sheet_exists(sheet_names.SHEET_PROJECTS_HISTORY)
                else []
            ),
            portfolio_entries=portfolio_entries,
            detail=load_project_detail(
                reader,
                project_id,
                load_project_entries,
                now,
            ),
            risk_rows=reader.read_as_objects(sheet_names.SHEET_RISKS),
            pending_rows=read_optional_rows(
                reader,
                sheet_names.SHEET_MINUTES_PENDING,
            ),
        )

        return build_executive_dashboard(project_id, sources, now)
    except DashboardError as error:
        logger.warning("Ejecutivo de %s no disponible: %s", project_id, error)
        return {"errorServidor": describe_error(error), "proyecto": None}


def read_optional_rows(reader: SheetReader, sheet_name: str) -> list[SheetRow]:
    """
    Lee una hoja que puede no existir o fallar.

    Args:
        reader: Repositorio de lectura de Sheets.
        sheet_name: Nombre de la hoja.

    Returns:
        Las filas, o lista vacia si no se pudo leer.
    """
    try:
        return reader.read_as_objects(sheet_name)
    except SheetsError as error:
        logger.info("Hoja %s omitida: %s", sheet_name, error.detail)
        return []
