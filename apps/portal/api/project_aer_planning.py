"""Escrituras de Planeación AER: mismos servicios y permisos que el RPC."""

from typing import Any

from apps.aer import rpc
from apps.daily.services.ixs_functions import fill_args
from apps.daily.services.ixs_store import run_safely
from apps.portal.api.project_client import with_project
from apps.portal.api.project_detail import ProjectMilestoneWriteView
from core.exceptions import InvalidRequestError

OPERATIONS = {
    "guardar": "guardarPlaneacionAER",
    "importar": "guardarLotePlaneacionAER",
    "estado": "actualizarEstadoCierrePlaneacionAER",
    "cerrar": "marcarCierrePlaneacionAER",
    "eliminar": "eliminarPlaneacionAER",
    "eliminar-lote": "eliminarLotePlaneacionAER",
    "vacacion-guardar": "guardarVacacionAER",
    "vacacion-eliminar": "eliminarVacacionAER",
}


def arguments(
    operation: str, project: str, body: dict[str, Any]
) -> tuple[Any, ...]:
    """El ID de la ruta prevalece donde la firma original recibe proyecto."""
    if operation in {"guardar", "vacacion-guardar"}:
        return with_project(project, body)
    if operation == "importar":
        return (project, body.get("items"))
    if operation == "estado":
        return (
            project,
            body.get("uid"),
            body.get("estado"),
            body.get("cierre"),
        )
    if operation == "cerrar":
        return (project, body.get("uid"), body.get("cerrado"))
    if operation == "eliminar":
        # Firma original por UID; autorización de portafolio completo.
        return (body.get("uid"),)
    if operation == "eliminar-lote":
        return (project, body.get("uids"))
    return (body.get("uid"), project)


def execute(
    operation: str, project: str, body: dict[str, Any]
) -> dict[str, Any]:
    """Lista cerrada de operaciones; reglas intactas en apps.aer.services."""
    if operation not in OPERATIONS:
        raise InvalidRequestError("Operación de planeación AER no válida.")
    count, action = rpc.FUNCTIONS[OPERATIONS[operation]]
    args = arguments(operation, project, body)
    return run_safely(lambda: action(rpc.build_store(), fill_args(args, count)))


class AerPlanningWriteView(ProjectMilestoneWriteView):
    """edit_operations, alcance total, cuerpo objeto y CSRF heredados."""

    def post(self, request: Any, project_id: str = "", **kwargs: Any) -> Any:
        """Selecciona la operación de la ruta, nunca una función arbitraria."""
        self.operation = str(kwargs.get("operation", ""))
        return super().post(request, project_id)

    def perform(
        self, project_id: str, payload: dict[str, Any]
    ) -> dict[str, Any]:
        """Reutiliza servicios originales y sus errores públicos."""
        return execute(self.operation, project_id, payload)
