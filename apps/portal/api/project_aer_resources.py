"""Evaluaciones AER: firmas y servicios originales con permiso y CSRF."""

from typing import Any

from apps.aer import rpc
from apps.daily.services.ixs_functions import fill_args
from apps.daily.services.ixs_store import run_safely
from apps.portal.api.project_client import with_project
from apps.portal.api.project_detail import ProjectMilestoneWriteView
from core.exceptions import InvalidRequestError

OPERATIONS = {
    "guardar": "guardarEvaluacionAER",
    "eliminar": "eliminarEvaluacionAER",
}


def execute(
    operation: str, project: str, body: dict[str, Any]
) -> dict[str, Any]:
    """El proyecto de la ruta prevalece; no cambia las reglas del servicio."""
    if operation not in OPERATIONS:
        raise InvalidRequestError("Operación de evaluaciones AER no válida.")
    args = (
        with_project(project, body)
        if operation == "guardar"
        else (body.get("uid"), project)
    )
    count, action = rpc.FUNCTIONS[OPERATIONS[operation]]
    return run_safely(lambda: action(rpc.build_store(), fill_args(args, count)))


class AerResourcesWriteView(ProjectMilestoneWriteView):
    """edit_operations, alcance total, cuerpo objeto y CSRF heredados."""

    def post(self, request: Any, project_id: str = "", **kwargs: Any) -> Any:
        """La operación procede de una ruta explícita."""
        self.operation = str(kwargs.get("operation", ""))
        return super().post(request, project_id)

    def perform(
        self, project_id: str, payload: dict[str, Any]
    ) -> dict[str, Any]:
        """Mismos resultados y errores públicos del servicio anterior."""
        return execute(self.operation, project_id, payload)
