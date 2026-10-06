"""Vistas y diagnosticos de un proyecto Clockify expuestos por RPC."""

from collections.abc import Callable
from typing import Any

from django.conf import settings
from django.utils import timezone

from apps.clockify.exceptions import ClockifyConfigurationError
from apps.clockify.provider import build_clockify_loader
from apps.clockify.services import connection_panel, diagnostics, project_views
from apps.clockify.services.date_ranges import (
    ProjectDateRange,
    ProjectDateRangeResolver,
)
from apps.daily.services.ixs_functions import fill_args
from apps.daily.services.ixs_store import run_safely
from core.exceptions import DashboardError, describe_error
from core.rpc.registry import register_rpc
from core.sheets import sheet_names
from core.sheets.factory import build_sheet_repository
from core.sheets.repository import GoogleSheetRepository

"""BKD.020.017 - RPC de proyecto Clockify
Registra obtenerRangoClockifyProyecto, obtenerEtapasHistoricoAIProyecto,
getRegistrosClockifyProyecto, obtenerResumenTasksTagsClockifyProyecto,
diagnosticoClockify, diagnosticoClockifyCompleto, guardarApiKeyClockify,
guardarWorkspaceClockify y el panel de conexion (listarProyectosClockify,
guardarVinculoProyectoClockify, diagnosticarConexionClockifyProyecto,
diagnosticarHorasClockifyProyecto) con los mismos nombres que
ClockifyService.gs.
"""

JsonObject = dict[str, Any]
Action = Callable[[GoogleSheetRepository, tuple[Any, ...]], JsonObject]

ENV_KEY_ERROR = (
    "La conexión global de Clockify se cambia en CLOCKIFY_API_KEY del "
    "archivo .env."
)
ENV_WORKSPACE_ERROR = (
    "El workspace global de Clockify se cambia en CLOCKIFY_WORKSPACE_ID "
    "del archivo .env."
)


def build_sources(
    repository: GoogleSheetRepository,
) -> project_views.ProjectSources:
    """Proyectos, historico A:I y fecha de hoy."""
    history_sheet = sheet_names.SHEET_PROJECTS_HISTORY
    history = (
        repository.read_values(history_sheet)
        if repository.sheet_exists(history_sheet)
        else []
    )

    return project_views.ProjectSources(
        project_rows=repository.read_as_objects(sheet_names.SHEET_PROJECTS),
        history_values=history,
        today=timezone.localdate(),
    )


def build_resolver(
    repository: GoogleSheetRepository,
) -> ProjectDateRangeResolver:
    """Resolver de rangos de la peticion."""
    return ProjectDateRangeResolver(repository, timezone.localdate())


def project_range(
    repository: GoogleSheetRepository, project: Any
) -> JsonObject:
    """obtenerRangoClockifyProyecto()."""
    try:
        date_range = build_resolver(repository).resolve(
            str(project or "").strip(),
        )
    except DashboardError as error:
        return {
            "ok": False,
            "error": describe_error(error),
            "fechaInicio": None,
            "fechaFin": None,
        }

    return project_views.range_dates(date_range)


def project_stages(
    repository: GoogleSheetRepository, project: Any
) -> JsonObject:
    """obtenerEtapasHistoricoAIProyecto()."""
    clean_id = str(project or "").strip()

    return project_views.stages_response(
        build_sources(repository),
        clean_id,
        build_resolver(repository).resolve_from_history(clean_id),
    )


def hours_loader(repository: GoogleSheetRepository) -> Callable[[str], Any]:
    """Horas del proyecto; el error de configuracion queda en la respuesta."""

    def load(project_id: str) -> Any:
        return build_clockify_loader(repository).load_project_hours(project_id)

    return load


def project_entries(
    repository: GoogleSheetRepository,
    project: Any,
) -> JsonObject:
    """getRegistrosClockifyProyecto()."""
    return project_views.project_entries(
        build_sources(repository),
        project,
        hours_loader(repository),
    )


def tasks_summary(
    repository: GoogleSheetRepository, project: Any
) -> JsonObject:
    """obtenerResumenTasksTagsClockifyProyecto()."""
    return project_views.tasks_summary(
        build_sources(repository),
        project,
        hours_loader(repository),
        lambda clockify_id: build_clockify_loader(
            repository,
        ).load_project_tasks(clockify_id),
    )


def run_diagnostic(
    repository: GoogleSheetRepository,
    project: Any,
    diagnostic: Callable[[diagnostics.DiagnosticContext, object], JsonObject],
) -> JsonObject:
    """Arma el contexto y ejecuta un diagnostico."""
    try:
        loader = build_clockify_loader(repository)
    except ClockifyConfigurationError:
        return {"ok": False, "error": diagnostics.SETUP_ERROR}

    sources = build_sources(repository)

    def range_payload(
        project_id: str, date_range: ProjectDateRange
    ) -> JsonObject:
        return project_views.range_payload(sources, project_id, date_range)

    context = diagnostics.DiagnosticContext(
        loader=loader,
        resource_rows=lambda: repository.read_as_objects(
            sheet_names.SHEET_RESOURCES,
        ),
        range_payload=range_payload,
    )

    return diagnostic(context, project)


def panel_context(
    repository: GoogleSheetRepository,
) -> connection_panel.PanelContext:
    """Cargador de Clockify (None si falta configuracion) y credencial."""
    try:
        loader = build_clockify_loader(repository)
    except ClockifyConfigurationError:
        loader = None

    return connection_panel.PanelContext(
        loader=loader,
        api_key=settings.CLOCKIFY_API_KEY,
        workspace_id=settings.CLOCKIFY_WORKSPACE_ID,
    )


def register(name: str, count: int, action: Action) -> None:
    """Registra una funcion; los errores regresan {"ok": False, "error"}."""

    def handler(*args: object) -> JsonObject:
        return run_safely(
            lambda: action(build_sheet_repository(), fill_args(args, count)),
        )

    handler.__name__ = name
    register_rpc(name)(handler)


FUNCTIONS: dict[str, tuple[int, Action]] = {
    "obtenerRangoClockifyProyecto": (
        1,
        lambda repo, args: project_range(repo, args[0]),
    ),
    "obtenerEtapasHistoricoAIProyecto": (
        1,
        lambda repo, args: project_stages(repo, args[0]),
    ),
    "getRegistrosClockifyProyecto": (
        1,
        lambda repo, args: project_entries(repo, args[0]),
    ),
    "obtenerResumenTasksTagsClockifyProyecto": (
        1,
        lambda repo, args: tasks_summary(repo, args[0]),
    ),
    "diagnosticoClockify": (
        1,
        lambda repo, args: run_diagnostic(
            repo,
            args[0],
            diagnostics.quick_diagnostic,
        ),
    ),
    "diagnosticoClockifyCompleto": (
        1,
        lambda repo, args: run_diagnostic(
            repo,
            args[0],
            diagnostics.full_diagnostic,
        ),
    ),
    "listarProyectosClockify": (
        0,
        lambda repo, args: connection_panel.list_projects(panel_context(repo)),
    ),
    "guardarVinculoProyectoClockify": (
        2,
        lambda repo, args: connection_panel.save_link(
            panel_context(repo),
            repo,
            repo,
            *args,
        ),
    ),
    "diagnosticarConexionClockifyProyecto": (
        1,
        lambda repo, args: connection_panel.connection_check(
            panel_context(repo),
            args[0],
        ),
    ),
    "diagnosticarHorasClockifyProyecto": (
        1,
        lambda repo, args: connection_panel.hours_check(
            panel_context(repo),
            args[0],
        ),
    ),
    "guardarApiKeyClockify": (
        1,
        lambda repo, args: {"ok": False, "error": ENV_KEY_ERROR},
    ),
    "guardarWorkspaceClockify": (
        2,
        lambda repo, args: {"ok": False, "error": ENV_WORKSPACE_ERROR},
    ),
}

for _name, (_count, _action) in FUNCTIONS.items():
    register(_name, _count, _action)
