"""Acciones y pendientes Beecker/Cliente: mismos servicios de AER e IXS."""

from typing import Any

from rest_framework.request import Request
from rest_framework.response import Response

from apps.aer import ai_rpc
from apps.aer.services import ai_functions
from apps.daily.services.ixs_functions import fill_args
from apps.daily.services.ixs_store import run_safely
from apps.portal.api.errors import error_response
from apps.portal.api.operations import OperationsScreen
from apps.portal.api.project_client import run_operation, with_project
from apps.portal.api.project_detail import ProjectMilestoneWriteView
from core.exceptions import DashboardError, InvalidRequestError

OPERATIONS = {
    "leer": ("getAccionesAERProyecto", "ixsGetAccionesProyecto"),
    "guardar": ("guardarAccionAER", "ixsGuardarAccion"),
    "actualizar": ("actualizarCampoAccionAER", "ixsActualizarCampoAccion"),
    "eliminar": ("eliminarAccionAER", "ixsEliminarAccion"),
    "limpiar-duplicados": (
        "limpiarDuplicadosAccionesAER",
        "ixsLimpiarDuplicadosAcciones",
    ),
    "partes-leer": ("listarAccionesPartesAER", "ixsListarAccionesPartes"),
    "parte-guardar": ("guardarAccionParteAER", "ixsGuardarAccionParte"),
    "parte-actualizar": (
        "actualizarCampoAccionParteAER",
        "ixsActualizarCampoAccionParte",
    ),
    "parte-eliminar": ("eliminarAccionParteAER", "ixsEliminarAccionParte"),
}


def arguments(
    operation: str, project: str, body: dict[str, Any]
) -> tuple[Any, ...]:
    """Firmas originales; las reglas y validaciones viven en los servicios."""
    if operation == "guardar":
        return with_project(project, body)
    if operation in {"actualizar", "parte-actualizar"}:
        return (project, body.get("uid"), body.get("campo"), body.get("valor"))
    if operation == "eliminar":
        # El original borra por UID; exige permiso de todo el portafolio.
        return (body.get("uid"),)
    if operation == "parte-eliminar":
        return (project, body.get("uid"))
    if operation == "parte-guardar":
        return (project, body.get("datos"))
    return (project,)


def execute(
    service: str, operation: str, project: str, body: dict[str, Any]
) -> dict[str, Any]:
    """Lista cerrada; no expone nombres RPC enviados por el cliente."""
    if service not in {"aer", "ixs"} or operation not in OPERATIONS:
        raise InvalidRequestError("Operación de acciones no válida.")
    aer, ixs = OPERATIONS[operation]
    args = arguments(operation, project, body)
    if service == "aer" and operation.startswith("parte"):
        count, action, drive = ai_functions.FUNCTIONS[aer]
        return run_safely(
            lambda: action(ai_rpc.build_context(drive), fill_args(args, count))
        )
    return run_operation(service, aer, ixs, args)


class ProjectActionsReadView(OperationsScreen):
    """Lecturas con view_operations y alcance total, igual que sus RPC."""

    def get(
        self, request: Request, project_id: str, operation: str
    ) -> Response:
        """Leer acciones o pendientes, sin escrituras desde GET."""
        try:
            if operation not in {"leer", "partes-leer"}:
                raise InvalidRequestError("Lectura de acciones no válida.")
            return self.body(
                execute(
                    str(request.query_params.get("servicio", "")),
                    operation,
                    project_id,
                    {},
                )
            )
        except DashboardError as error:
            return error_response(
                error.http_status, error.code, error.build_message()
            )


class ProjectActionsWriteView(ProjectMilestoneWriteView):
    """Escrituras con edit_operations, alcance total y CSRF heredados."""

    def post(self, request: Any, project_id: str = "", **kwargs: Any) -> Any:
        """Operación explícita de la ruta."""
        self.operation = str(kwargs.get("operation", ""))
        return super().post(request, project_id)

    def perform(
        self, project_id: str, payload: dict[str, Any]
    ) -> dict[str, Any]:
        """No mezcla operaciones de lectura con mutaciones."""
        if self.operation in {"leer", "partes-leer"}:
            raise InvalidRequestError("Escritura de acciones no válida.")
        return execute(
            str(payload.get("servicio", "")),
            self.operation,
            project_id,
            payload,
        )
