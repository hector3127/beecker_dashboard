"""Riesgos AER: servicios originales, alcance total y permisos del RPC."""

from typing import Any

from apps.aer import rpc
from apps.daily.services.ixs_functions import fill_args
from apps.daily.services.ixs_store import run_safely
from apps.portal.api.project_client import with_project
from apps.portal.api.project_detail import (
    ProjectMilestoneWriteView,
    ProjectRead,
)
from core.exceptions import InvalidRequestError

OPERATIONS = {
    "leer": "getRiesgosAERProyecto",
    "guardar": "guardarRiesgoAER",
    "eliminar": "eliminarRiesgoAER",
    "limpiar-duplicados": "limpiarDuplicadosRiesgosAER",
}


def execute(
    operation: str, project: str, body: dict[str, Any]
) -> dict[str, Any]:
    """Lista cerrada y firmas exactas; no cambia validaciones de negocio."""
    if operation not in OPERATIONS:
        raise InvalidRequestError("Operación de riesgos AER no válida.")
    args = (
        with_project(project, body)
        if operation == "guardar"
        else (body.get("uid"),)
        if operation == "eliminar"
        else (project,)
    )
    # El borrado conserva su firma por UID y exige portafolio completo.
    count, action = rpc.FUNCTIONS[OPERATIONS[operation]]
    return run_safely(lambda: action(rpc.build_store(), fill_args(args, count)))


class AerRisksReadView(ProjectRead):
    """Lectura con view_operations y alcance total, antes de las fuentes."""

    def load(self, project_id: str) -> dict[str, Any]:
        """Mismo resumen de riesgos del proyecto."""
        return execute("leer", project_id, {})


class AerRisksWriteView(ProjectMilestoneWriteView):
    """edit_operations, alcance total, cuerpo objeto y CSRF heredados."""

    def post(self, request: Any, project_id: str = "", **kwargs: Any) -> Any:
        """La operación procede de la ruta explícita."""
        self.operation = str(kwargs.get("operation", ""))
        return super().post(request, project_id)

    def perform(
        self, project_id: str, payload: dict[str, Any]
    ) -> dict[str, Any]:
        """GET no se expone como una escritura."""
        if self.operation == "leer":
            raise InvalidRequestError("Escritura de riesgos AER no válida.")
        return execute(self.operation, project_id, payload)
