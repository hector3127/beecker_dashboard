"""Funciones del resumen ejecutivo expuestas al frontend por RPC."""

import logging
from datetime import date

from django.core.cache import cache
from django.utils import timezone

from apps.azure_devops.exceptions import AzureDevOpsConfigurationError
from apps.azure_devops.gateway import AzureDevOpsGateway
from apps.clockify.provider import build_clockify_loader
from apps.clockify.services.time_entry_loader import ClockifyTimeEntryLoader
from apps.ejecutivo.constants import (
    MPB_COLUMN_COUNT,
    SHEET_MPB,
    SUMMARY_CACHE_SECONDS,
)
from apps.ejecutivo.services.aer_tym_consumption import (
    JsonObject,
    build_consumption_items,
)
from apps.ejecutivo.services.aer_tym_summary import build_aer_tym_summary
from apps.ejecutivo.services.ixb_rules import read_project_id
from apps.ejecutivo.services.ixb_summary import (
    IxbSources,
    build_ixb_summary,
    group_by_base,
)
from apps.ejecutivo.services.project_dashboard import (
    build_history_block_rows,
)
from apps.ejecutivo.services.project_detail import build_error_detail
from apps.ejecutivo.services.project_orchestrator import (
    load_executive_dashboard,
    load_project_detail,
)
from core.exceptions import DashboardError, describe_error
from core.rpc.registry import register_rpc
from core.sheets import sheet_names
from core.sheets.factory import build_sheet_repository
from core.sheets.protocols import SheetReader
from core.time_entries.factory import build_time_entry_provider
from core.time_entries.models import TimeEntry
from core.utils.text import to_text

"""BKD.040.006 - RPC del resumen ejecutivo
Registra obtenerResumenAERTYMMPB, obtenerConsumosResumenAERTYMMPB y
obtenerResumenIXBRaaS con los mismos nombres y respuestas que en Apps
Script.
"""

logger = logging.getLogger(__name__)

SUMMARY_CACHE_KEY = "ejecutivo:aer_tym:v1"

DETAIL_SHEETS = [
    sheet_names.SHEET_PROJECTS,
    sheet_names.SHEET_RESOURCES,
    sheet_names.SHEET_SALARY_BANDS,
    sheet_names.SHEET_MASTER_RATES,
]


@register_rpc("obtenerResumenAERTYMMPB")
def get_aer_tym_summary() -> JsonObject:
    """
    Devuelve los proyectos AER/T&M en progreso de la hoja MPB.

    Returns:
        {"ok", "filas", "fuente"} o {"ok": False, "error"}.
    """
    try:
        return load_aer_tym_summary(build_sheet_repository())
    except DashboardError as error:
        logger.warning("Resumen AER/T&M no disponible: %s", error.detail)
        return {"ok": False, "error": error.build_message()}


@register_rpc("obtenerConsumosResumenAERTYMMPB")
def get_aer_tym_consumption(project_ids: object = None) -> JsonObject:
    """
    Calcula en Clockify las horas consumidas de hasta dos proyectos.

    Args:
        project_ids: Lista de IDs de proyecto.

    Returns:
        {"ok": True, "items": [...]} o {"ok": False, "error"}.
    """
    try:
        repository = build_sheet_repository()
        summary = load_aer_tym_summary(repository)
        loader = build_clockify_loader(repository)
    except DashboardError as error:
        return {"ok": False, "error": error.build_message()}

    def load_entries(
        project_id: str,
        date_range: tuple[date, date],
    ) -> list[TimeEntry]:
        return loader.load_project(project_id, date_range)

    requested_ids = project_ids if isinstance(project_ids, list) else []

    return {
        "ok": True,
        "items": build_consumption_items(
            requested_ids,
            summary["filas"],
            load_entries,
            timezone.localdate(),
        ),
    }


def load_aer_tym_summary(reader: SheetReader) -> JsonObject:
    """
    Lee el resumen AER/T&M, con cache de 90 segundos.

    Args:
        reader: Repositorio de lectura de Sheets.

    Returns:
        El resumen AER/T&M.
    """
    cached_summary = cache.get(SUMMARY_CACHE_KEY)

    if isinstance(cached_summary, dict):
        return cached_summary

    if not reader.sheet_exists(SHEET_MPB):
        return {"ok": True, "filas": [], "fuente": "MPB"}

    mpb_values = [
        list(row[:MPB_COLUMN_COUNT]) for row in reader.read_values(SHEET_MPB)
    ]
    summary = build_aer_tym_summary(mpb_values, timezone.localdate())
    cache.set(SUMMARY_CACHE_KEY, summary, SUMMARY_CACHE_SECONDS)

    return summary


@register_rpc("obtenerResumenIXBRaaS")
def get_ixb_raas_summary() -> JsonObject:
    """
    Devuelve la tabla IXB/RaaS con sus pivotes por Delivery Manager.

    Returns:
        {"ok", "filas", "pivoteServicio", "pivoteStatus"} o el error.
    """
    try:
        repository = build_sheet_repository()
        history_rows = (
            build_history_block_rows(
                repository.read_values(sheet_names.SHEET_PROJECTS_HISTORY),
                [],
            )
            if repository.sheet_exists(sheet_names.SHEET_PROJECTS_HISTORY)
            else []
        )
        project_rows = repository.read_as_objects(sheet_names.SHEET_PROJECTS)
        project_entries = LazyProjectEntries(repository)
        project_entries.prefetch(
            [
                read_project_id(row)
                for group_rows in group_by_base(project_rows).values()
                for row in group_rows
            ],
        )
        sources = IxbSources(
            project_rows=project_rows,
            history_rows=history_rows,
            load_project_entries=project_entries,
            azure=build_optional_azure_gateway(),
        )

        return build_ixb_summary(
            sources,
            timezone.localtime().replace(tzinfo=None),
        )
    except DashboardError as error:
        logger.warning("Resumen IXB/RaaS no disponible: %s", error.detail)
        return {
            "ok": False,
            "error": error.build_message(),
            "filas": [],
            "pivoteServicio": [],
            "pivoteStatus": [],
        }


@register_rpc("getDetalleProyectoCompleto")
def get_project_detail(project_id: object = "") -> JsonObject:
    """
    Devuelve el detalle por recurso de un proyecto.

    Args:
        project_id: ID interno del proyecto.

    Returns:
        El mismo objeto que getDetalleProyectoCompleto().
    """
    clean_id = read_argument_id(project_id)

    try:
        repository = build_sheet_repository()
    except DashboardError as error:
        return build_error_detail(clean_id, describe_error(error))

    repository.prefetch(DETAIL_SHEETS)

    return load_project_detail(
        repository,
        clean_id,
        LazyProjectEntries(repository),
        timezone.localtime().replace(tzinfo=None),
    )


@register_rpc("getDashboardEjecutivoProyecto")
def get_executive_dashboard(project_id: object = "") -> JsonObject:
    """
    Devuelve el dashboard ejecutivo de un proyecto.

    Args:
        project_id: ID exacto del proyecto en la hoja Proyectos.

    Returns:
        El mismo objeto que getDashboardEjecutivoProyecto().
    """
    clean_id = read_argument_id(project_id)

    try:
        repository = build_sheet_repository()
    except DashboardError as error:
        return {"errorServidor": describe_error(error), "proyecto": None}

    repository.prefetch(
        [
            *DETAIL_SHEETS,
            sheet_names.SHEET_PROJECTS_HISTORY,
            sheet_names.SHEET_RISKS,
            sheet_names.SHEET_MINUTES_PENDING,
        ],
    )

    def load_portfolio_entries() -> tuple[TimeEntry, ...]:
        return build_time_entry_provider(repository).load_time_entries().entries

    return load_executive_dashboard(
        repository,
        clean_id,
        (LazyProjectEntries(repository), load_portfolio_entries),
        timezone.localtime().replace(tzinfo=None),
        build_optional_azure_gateway(),
    )


def read_argument_id(project_id: object) -> str:
    """
    Convierte el ID recibido del frontend a texto.

    Args:
        project_id: Valor enviado por el panel.

    Returns:
        El ID como texto (vacio si no llego).
    """
    if isinstance(project_id, str | int | float | bool) or project_id is None:
        return to_text(project_id)

    return str(project_id)


class LazyProjectEntries:
    """Crea el cargador de Clockify solo cuando se necesita."""

    def __init__(self, reader: SheetReader) -> None:
        self._reader = reader
        self._loader: ClockifyTimeEntryLoader | None = None

    def prefetch(self, project_ids: list[str]) -> None:
        """
        Descarga en paralelo las horas de varios proyectos.

        Sin Clockify configurado no hace nada: cada proyecto reportara el
        error al consultarse.

        Args:
            project_ids: IDs internos a precargar.
        """
        try:
            self._get_loader().prefetch_projects(project_ids)
        except DashboardError as error:
            logger.info("Precarga de Clockify omitida: %s", error.detail)

    def __call__(self, project_id: str) -> list[TimeEntry]:
        """
        Lee las horas de un proyecto con su rango de MPB o historico.

        Args:
            project_id: ID interno del proyecto.

        Returns:
            Los registros de Clockify del proyecto.
        """
        return self._get_loader().load_project(project_id)

    def _get_loader(self) -> ClockifyTimeEntryLoader:
        """Crea el cargador de Clockify la primera vez que se usa."""
        if self._loader is None:
            self._loader = build_clockify_loader(self._reader)

        return self._loader


def build_optional_azure_gateway() -> AzureDevOpsGateway | None:
    """
    Crea el acceso a Azure; sin configuracion el resumen sigue sin Azure.

    Returns:
        El acceso a Azure DevOps, o None si no esta configurado.
    """
    try:
        return AzureDevOpsGateway()
    except AzureDevOpsConfigurationError as error:
        logger.info("Resumen IXB/RaaS sin Azure: %s", error.detail)
        return None
