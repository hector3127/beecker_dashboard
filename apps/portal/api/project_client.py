"""Escrituras de Cliente (contactos, ficha, gobierno y documentos), API v1."""

from collections.abc import Callable
from typing import Any

from apps.aer import rpc as aer_rpc
from apps.daily import ixs_rpc
from apps.daily.services import ixs_functions
from apps.daily.services.ixs_store import run_safely
from apps.portal.api.project_detail import ProjectMilestoneWriteView
from core.exceptions import InvalidRequestError

"""BKD.150.001 - Escrituras de Cliente
La pestaña Cliente es la misma en AER/T&M y en IXB/SaaS/RaaS; solo cambia la
funcion del RPC anterior. `servicio` ("aer" o "ixs") la elige y el proyecto de
la ruta prevalece sobre el del cuerpo. Mismos permisos que ixsGuardar* /
guardar*AER: edit_operations, alcance total y CSRF.
"""

JsonObject = dict[str, Any]
Builder = Callable[[str, dict[str, Any]], tuple[Any, ...]]


def with_project(project: str, body: dict[str, Any]) -> tuple[Any, ...]:
    """Cuerpo sin la bandera de servicio y con el ID de la ruta."""
    payload = {k: v for k, v in body.items() if k != "servicio"}

    return ({**payload, "ID_Proyecto": project},)


def by_uid(project: str, body: dict[str, Any]) -> tuple[Any, ...]:
    """eliminar*(uid, proyecto)."""
    return (body.get("uid"), project)


def governance(project: str, body: dict[str, Any]) -> tuple[Any, ...]:
    """guardarGobierno*(proyecto, filas)."""
    return (project, body.get("filas"))


# operacion -> (funcion AER, funcion IXS, argumentos)
OPERATIONS: dict[str, tuple[str, str, Builder]] = {
    "contacto-guardar": (
        "guardarContactoAER",
        "ixsGuardarContacto",
        lambda p, b: with_project(p, b),
    ),
    "contacto-eliminar": ("eliminarContactoAER", "ixsEliminarContacto", by_uid),
    "info-guardar": (
        "guardarClienteInfoAER",
        "ixsGuardarClienteInfo",
        lambda p, b: with_project(p, b),
    ),
    "gobierno-guardar": (
        "guardarGobiernoClienteAER",
        "ixsGuardarGobiernoCliente",
        governance,
    ),
    "documento-guardar": (
        "guardarDocumentoClienteAER",
        "ixsGuardarDocumentoCliente",
        lambda p, b: with_project(p, b),
    ),
    "documento-eliminar": (
        "eliminarDocumentoClienteAER",
        "ixsEliminarDocumentoCliente",
        by_uid,
    ),
}


def run_operation(
    service: str, aer_name: str, ixs_name: str, args: tuple[Any, ...]
) -> JsonObject:
    """Ejecuta la misma funcion que antes llamaba el RPC."""
    if service == "aer":
        count, action = aer_rpc.FUNCTIONS[aer_name]

        return run_safely(
            lambda: action(
                aer_rpc.build_store(), ixs_functions.fill_args(args, count)
            )
        )

    action_ixs = ixs_functions.SHEET_FUNCTIONS[ixs_name]

    return run_safely(
        lambda: ixs_functions.call_action(
            action_ixs, ixs_rpc.build_store_sheets(), args
        )
    )


class ProjectClientWriteView(ProjectMilestoneWriteView):
    """POST screens/proyectos/<id>/cliente/<operacion>/."""

    def post(self, request: Any, project_id: str = "", **kwargs: Any) -> Any:
        """Elige la operacion de la ruta; la validacion sigue en el servicio."""
        self.operation = str(kwargs.get("operacion", ""))

        return super().post(request, project_id)

    def perform(
        self, project_id: str, payload: dict[str, Any]
    ) -> dict[str, Any]:
        """Despacha a la funcion de AER o de IXS segun `servicio`."""
        service = str(payload.get("servicio", ""))
        found = OPERATIONS.get(self.operation)

        if found is None or service not in {"aer", "ixs"}:
            raise InvalidRequestError("Operación de cliente no válida.")

        aer_name, ixs_name, build = found

        return run_operation(
            service, aer_name, ixs_name, build(project_id, payload)
        )
