"""Funciones del panel Daily expuestas al frontend por RPC."""

import logging
import time
from collections.abc import Callable
from typing import Any

from django.conf import settings
from django.core.cache import cache
from django.utils import timezone

from apps.daily.constants import (
    OPPORTUNITY_TYPE,
    RISK_TYPE,
    SHEET_UAT_ADJUSTMENTS,
    SHEET_WARRANTY_ADJUSTMENTS,
)
from apps.daily.services import (
    azure_config,
    daily_sheets,
    risk_form,
    work_items,
)
from apps.daily.services.azure_connection import ConnectionStore
from apps.daily.services.daily_azure_client import DailyAzureClient
from apps.daily.services.daily_sheets import DailySheets
from apps.daily.services.project_links import (
    list_project_sprints,
    resolve_internal_project,
)
from apps.ejecutivo.rpc import get_executive_dashboard
from core.exceptions import DashboardError, describe_error
from core.rpc.registry import register_rpc
from core.sheets import sheet_names
from core.sheets.factory import build_sheet_repository

"""BKD.070.010 - RPC del Daily
Registra las funciones del panel Daily con los mismos nombres y
respuestas que DailyPanelService.gs.
"""

logger = logging.getLogger(__name__)

JsonObject = dict[str, Any]


def build_store() -> ConnectionStore:
    """Configuracion de Azure desde el .env y la cache de Django."""
    return ConnectionStore(
        cache,
        settings.AZURE_DEVOPS_ORGANIZATION,
        settings.AZURE_DEVOPS_PAT,
        settings.AZURE_DEVOPS_PROJECT,
    )


def build_daily_azure() -> work_items.DailyAzure:
    """Conexion, cliente y cache del panel."""
    connection = build_store().load()

    return work_items.DailyAzure(
        connection=connection,
        build_client=lambda: DailyAzureClient(
            connection.organization,
            connection.personal_access_token,
        ),
        cache=cache,
    )


def build_sheets() -> DailySheets:
    """Hojas del panel con la hora local actual."""
    repository = build_sheet_repository()

    return DailySheets(
        reader=repository,
        writer=repository,
        now=timezone.localtime().replace(tzinfo=None),
        timestamp_ms=time.time_ns() // 10**6,
    )


def run_sheet_action(
    action: Callable[[DailySheets], JsonObject],
    failure: JsonObject,
) -> JsonObject:
    """
    Ejecuta una accion sobre las hojas y arma el error del original.

    Args:
        action: Accion a ejecutar.
        failure: Llaves extra de la respuesta con error.

    Returns:
        La respuesta de la accion, o {"ok": False, "error", ...}.
    """
    try:
        return action(build_sheets())
    except DashboardError as error:
        logger.warning("Accion del Daily fallida: %s", error.detail)
        return {"ok": False, **failure, "error": describe_error(error)}


# --- Configuracion de Azure DevOps -------------------------------------


@register_rpc("guardarConfigAzureDevOps")
def save_azure_config(
    organization: object = "",
    project: object = "",
    token: object = "",
) -> JsonObject:
    """Guarda el proyecto activo (organizacion y PAT del .env)."""
    return azure_config.save_azure_config(
        build_store(),
        cache,
        (organization, project, token),
    )


@register_rpc("obtenerConfigAzureDevOps")
def get_azure_config() -> JsonObject:
    """Configuracion actual sin exponer el PAT."""
    return azure_config.read_azure_config(build_store())


@register_rpc("desconectarAzureDevOps")
def disconnect_azure() -> JsonObject:
    """Vuelve al proyecto del .env."""
    return azure_config.disconnect_azure(build_store(), cache)


@register_rpc("listarProyectosGuardadosAzureDevOps")
def list_saved_projects() -> JsonObject:
    """Proyectos visibles con la configuracion del .env."""
    return azure_config.list_saved_projects(build_store())


@register_rpc("cambiarProyectoActivoAzureDevOps")
def change_active_project(new_project: object = "") -> JsonObject:
    """Cambia el proyecto activo del panel."""
    return azure_config.change_active_project(build_store(), cache, new_project)


@register_rpc("listarProyectosAzureDevOps")
def list_projects(organization: object = "", token: object = "") -> JsonObject:
    """Proyectos visibles para la organizacion y el PAT del modal."""
    return azure_config.list_azure_projects(organization, token, build_store())


@register_rpc("probarConexionAzureDevOps")
def test_connection() -> JsonObject:
    """Prueba la conexion con el proyecto activo."""
    return azure_config.test_azure_connection(build_store())


# --- Work items ----------------------------------------------------------


@register_rpc("obtenerWorkItemsPendientes")
def get_pending_work_items(force_refresh: object = False) -> JsonObject:
    """Work items abiertos del proyecto activo."""
    return work_items.load_pending_work_items(
        build_daily_azure(), force_refresh
    )


@register_rpc("obtenerWorkItemsPorTipo")
def get_work_items_by_type(
    work_item_type: object = "",
    force_refresh: object = False,
) -> JsonObject:
    """Work items abiertos de un tipo."""
    return work_items.load_work_items_by_type(
        build_daily_azure(),
        str(work_item_type),
        force_refresh,
    )


@register_rpc("obtenerRiesgosAzureDevOps")
def get_risks(force_refresh: object = False) -> JsonObject:
    """Riesgos abiertos (tipo Risk)."""
    return work_items.load_work_items_by_type(
        build_daily_azure(),
        RISK_TYPE,
        force_refresh,
    )


@register_rpc("obtenerOportunidadesAzureDevOps")
def get_opportunities(force_refresh: object = False) -> JsonObject:
    """Oportunidades abiertas (tipo Opportunity)."""
    return work_items.load_work_items_by_type(
        build_daily_azure(),
        OPPORTUNITY_TYPE,
        force_refresh,
    )


@register_rpc("obtenerWorkItemsToBeYCR")
def get_tobe_work_items(force_refresh: object = False) -> JsonObject:
    """Work items To Be y Change Request con su avance."""

    def load_progress() -> dict[str, JsonObject]:
        try:
            return daily_sheets.load_progress_map(build_sheets())
        except DashboardError as error:
            logger.warning("Avance de work items omitido: %s", error.detail)
            return {}

    return work_items.load_tobe_work_items(
        build_daily_azure(),
        force_refresh,
        load_progress,
    )


@register_rpc("obtenerWorkItemsSinSeguimiento")
def get_stale_work_items(threshold_days: object = None) -> JsonObject:
    """Work items abiertos sin cambios recientes."""
    return work_items.load_stale_work_items(
        build_daily_azure(),
        threshold_days,
        timezone.now(),
    )


@register_rpc("inspeccionarCamposWorkItem")
def inspect_fields(work_item_type: object = "") -> JsonObject:
    """Campos del work item mas reciente de un tipo."""
    return work_items.inspect_work_item_fields(
        build_daily_azure(),
        str(work_item_type),
    )


@register_rpc("guardarCampoAvanceWorkItem")
def save_work_item_progress(
    work_item_id: object = "",
    field_name: object = "",
    value: object = None,
) -> JsonObject:
    """Guarda un campo de avance del work item en WorkItems_Avance."""
    active_project = build_store().active_project()

    return run_sheet_action(
        lambda sheets: daily_sheets.save_work_item_progress(
            sheets,
            (work_item_id, field_name, value),
            active_project,
        ),
        {},
    )


# --- Proyectos internos ---------------------------------------------------


@register_rpc("listarSprintsProyecto")
def list_sprints(azure_project: object = "") -> JsonObject:
    """IDs internos con el mismo ID base que el proyecto de Azure."""
    try:
        project_rows = build_sheet_repository().read_as_objects(
            sheet_names.SHEET_PROJECTS,
        )
    except DashboardError as error:
        return {"ok": False, "error": describe_error(error), "sprints": []}

    return list_project_sprints(azure_project, project_rows)


@register_rpc("obtenerResumenEjecutivoParaDaily")
def get_executive_summary(
    azure_project: object = "",
    forced_internal_id: object = "",
) -> JsonObject:
    """Dashboard ejecutivo del proyecto interno ligado al de Azure."""
    try:
        project_id = (
            str(forced_internal_id).strip() if forced_internal_id else ""
        ) or resolve_internal_project(
            azure_project,
            build_sheet_repository().read_as_objects(
                sheet_names.SHEET_PROJECTS
            ),
        )
    except DashboardError as error:
        return {"ok": False, "error": describe_error(error)}

    if not project_id:
        return {
            "ok": False,
            "error": "No se encontró un proyecto interno vinculado a "
            f'"{azure_project}". Revisa que exista en la hoja Proyectos '
            "(con o sin sufijo _CR/_S1/_S2).",
        }

    data = get_executive_dashboard(project_id)

    if data.get("errorServidor"):
        return {"ok": False, "error": data["errorServidor"]}

    return {"ok": True, "idProyectoInterno": project_id, "data": data}


# --- Pendientes y ajustes --------------------------------------------------


@register_rpc("obtenerPendientesDaily")
def get_daily_pending(project_filter: object = None) -> JsonObject:
    """Pendientes abiertos del Daily."""
    return run_sheet_action(
        lambda sheets: daily_sheets.list_daily_pending(sheets, project_filter),
        {"pendientes": [], "total": 0},
    )


@register_rpc("agregarPendienteDaily")
def add_daily_pending(
    description: object = "",
    project: object = "",
    owner: object = "",
    priority: object = "",
    due_date: object = None,
) -> JsonObject:
    """Agrega un pendiente."""
    return run_sheet_action(
        lambda sheets: daily_sheets.add_daily_pending(
            sheets,
            (description, project, owner, priority, due_date),
        ),
        {},
    )


@register_rpc("actualizarEstadoPendienteDaily")
def update_daily_pending(
    record_id: object = "",
    new_state: object = "",
) -> JsonObject:
    """Completa o reabre un pendiente."""
    return run_sheet_action(
        lambda sheets: daily_sheets.update_daily_pending_state(
            sheets,
            record_id,
            new_state,
        ),
        {},
    )


@register_rpc("eliminarPendienteDaily")
def delete_daily_pending(record_id: object = "") -> JsonObject:
    """Elimina un pendiente."""
    return run_sheet_action(
        lambda sheets: daily_sheets.delete_daily_pending(sheets, record_id),
        {},
    )


def register_adjustment_functions(suffix: str, sheet_name: str) -> None:
    """
    Registra obtener/agregar/actualizar/eliminar de una hoja de ajustes.

    Args:
        suffix: UAT o Garantia.
        sheet_name: Hoja de los ajustes.
    """

    def list_items(project_filter: object = None) -> JsonObject:
        return run_sheet_action(
            lambda sheets: daily_sheets.list_adjustments(
                sheets,
                sheet_name,
                project_filter,
            ),
            {"ajustes": [], "total": 0},
        )

    def add_item(
        description: object = "",
        project: object = "",
        dev_pct: object = 0,
    ) -> JsonObject:
        return run_sheet_action(
            lambda sheets: daily_sheets.add_adjustment(
                sheets,
                sheet_name,
                (description, project, dev_pct),
            ),
            {},
        )

    def update_item(
        record_id: object = "",
        dev_pct: object = None,
        qa_ready: object = None,
    ) -> JsonObject:
        return run_sheet_action(
            lambda sheets: daily_sheets.update_adjustment(
                sheets,
                sheet_name,
                record_id,
                (dev_pct, qa_ready),
            ),
            {},
        )

    def delete_item(record_id: object = "") -> JsonObject:
        return run_sheet_action(
            lambda sheets: daily_sheets.delete_adjustment(
                sheets,
                sheet_name,
                record_id,
            ),
            {},
        )

    register_rpc(f"obtenerAjustes{suffix}")(list_items)
    register_rpc(f"agregarAjuste{suffix}")(add_item)
    register_rpc(f"actualizarAjuste{suffix}")(update_item)
    register_rpc(f"eliminarAjuste{suffix}")(delete_item)


register_adjustment_functions("UAT", SHEET_UAT_ADJUSTMENTS)
register_adjustment_functions("Garantia", SHEET_WARRANTY_ADJUSTMENTS)


# --- Riesgos y comentarios en Azure ----------------------------------------


@register_rpc("obtenerFormularioRiesgoAzure")
def get_risk_form() -> JsonObject:
    """Campos del formulario de riesgo con las opciones de Azure."""
    return risk_form.build_risk_form(build_daily_azure())


@register_rpc("buscarIteraciones")
def search_iterations(query: object = "") -> JsonObject:
    """Iteration Paths que contienen el texto."""
    return risk_form.search_iterations(build_daily_azure(), query)


@register_rpc("buscarUsuariosAzureDevOps")
def search_users(query: object = "") -> JsonObject:
    """Personas asignadas en el proyecto que coinciden con el texto."""
    return risk_form.search_users(build_daily_azure(), query)


@register_rpc("buscarWorkItemsParaRelacionar")
def search_work_items(query: object = "") -> JsonObject:
    """Work items no cerrados por ID o titulo."""
    return risk_form.search_work_items(build_daily_azure(), query)


@register_rpc("crearWorkItemRiesgoAzure")
def create_risk(form: object = None) -> JsonObject:
    """Crea un work item Risk en Azure DevOps."""
    return risk_form.create_risk_work_item(build_daily_azure(), form)


@register_rpc("agregarComentarioWorkItem")
def add_comment(work_item_id: object = "", comment: object = "") -> JsonObject:
    """Publica un comentario fechado en el work item."""
    return risk_form.add_work_item_comment(
        build_daily_azure(),
        work_item_id,
        comment,
        timezone.localtime(),
    )
