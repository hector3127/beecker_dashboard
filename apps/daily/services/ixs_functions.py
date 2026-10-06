"""Funciones de hojas de la vista IXS con las firmas del original."""

import inspect
from collections.abc import Callable
from typing import Any

from apps.daily.services import bee_com, ixs_client, ixs_planning
from apps.daily.services.ixs_store import IxsStore, JsonObject, run_safely

"""BKD.070.019 - Funciones IXS de hojas
Nombre de Apps Script -> funcion, incluidas las envolturas que cambian
el orden de los argumentos (ixsEliminarContacto(uid, id)) o la forma de
la respuesta (ixsListarAccionesPartes()).
"""


def call_action(
    action: Callable[..., JsonObject],
    store: IxsStore,
    args: tuple[object, ...],
) -> JsonObject:
    """
    Llama la accion con los argumentos del frontend.

    Como en google.script.run, los que faltan llegan como None y los que
    sobran se ignoran.
    """
    parameters = list(inspect.signature(action).parameters.values())[1:]

    if any(
        parameter.kind is inspect.Parameter.VAR_POSITIONAL
        for parameter in parameters
    ):
        return action(store, *args)

    return action(store, *fill_args(args, len(parameters)))


def guarded(action: Callable[..., JsonObject]) -> Callable[..., JsonObject]:
    """Ejecuta la accion dentro de su propio manejo de errores."""

    def wrapper(store: IxsStore, *args: object) -> JsonObject:
        return run_safely(lambda: call_action(action, store, args))

    return wrapper


def governance_wrapper(
    store: IxsStore,
    project_value: object = None,
    rows: object = None,
) -> JsonObject:
    """ixsGuardarGobiernoCliente(): agrega "gobierno" arriba."""
    result = guarded(ixs_client.save_governance)(store, project_value, rows)

    return ixs_client.with_client_key(result, "gobierno")


def document_save_wrapper(
    store: IxsStore, payload: object = None
) -> JsonObject:
    """ixsGuardarDocumentoCliente(): agrega "documentos" arriba."""
    result = guarded(ixs_client.save_record)(store, "documento", payload)

    return ixs_client.with_client_key(result, "documentos")


def document_delete_wrapper(
    store: IxsStore,
    uid: object = None,
    project_value: object = None,
) -> JsonObject:
    """ixsEliminarDocumentoCliente(uid, id)."""
    result = guarded(ixs_client.delete_record)(
        store,
        "documento",
        project_value,
        uid,
    )

    return ixs_client.with_client_key(result, "documentos")


def parts_wrapper(
    action: Callable[..., JsonObject],
) -> Callable[..., JsonObject]:
    """Regresa {"ok", "filas": partes} como ixs*AccionParte()."""

    def wrapper(store: IxsStore, *args: object) -> JsonObject:
        return ixs_client.parts_only(guarded(action)(store, *args))

    return wrapper


def update_action(store: IxsStore, *args: object) -> JsonObject:
    """ixsClienteAccionesActualizar(id, uid, campo, valor)."""
    return ixs_client.update_field(store, "accion", fill_args(args, 4))


def update_part(store: IxsStore, *args: object) -> JsonObject:
    """ixsClienteAccionesActualizarParte(id, uid, campo, valor)."""
    return ixs_client.update_field(store, "parte", fill_args(args, 4))


def fill_args(args: tuple[object, ...], count: int) -> Any:
    """Completa los argumentos que no envio el frontend con None."""
    return tuple(args[:count]) + (None,) * max(0, count - len(args))


def swap_delete(record_type: str) -> Callable[..., JsonObject]:
    """Eliminar con la firma (uid, id) de las envolturas del original."""

    def action(
        store: IxsStore,
        uid: object = None,
        project_value: object = None,
    ) -> JsonObject:
        return ixs_client.delete_record(store, record_type, project_value, uid)

    return action


def typed_save(record_type: str) -> Callable[..., JsonObject]:
    """Guardar un tipo fijo con la firma (payload)."""

    def action(store: IxsStore, payload: object = None) -> JsonObject:
        return ixs_client.save_record(store, record_type, payload)

    return action


def list_parts(store: IxsStore, project_value: object = None) -> JsonObject:
    """ixsListarAccionesPartes(id)."""
    return ixs_client.read_client_actions(store, project_value)


def delete_part(
    store: IxsStore,
    project_value: object = None,
    uid: object = None,
) -> JsonObject:
    """ixsEliminarAccionParte(id, uid)."""
    return ixs_client.delete_record(store, "parte", project_value, uid)


SHEET_FUNCTIONS: dict[str, Callable[..., JsonObject]] = {
    "ixsClienteAccionesLeer": ixs_client.read_client_actions,
    "ixsClienteAccionesGuardar": ixs_client.save_record,
    "ixsClienteAccionesGobierno": ixs_client.save_governance,
    "ixsClienteAccionesEliminar": ixs_client.delete_record,
    "ixsClienteAccionesActualizar": update_action,
    "ixsClienteAccionesActualizarParte": update_part,
    "ixsClienteAccionesLimpiarDuplicados": ixs_client.remove_duplicate_actions,
    "ixsGuardarContacto": typed_save("contacto"),
    "ixsEliminarContacto": swap_delete("contacto"),
    "ixsGuardarClienteInfo": typed_save("info"),
    "ixsGuardarGobiernoCliente": governance_wrapper,
    "ixsGuardarDocumentoCliente": document_save_wrapper,
    "ixsEliminarDocumentoCliente": document_delete_wrapper,
    "ixsGuardarAccion": typed_save("accion"),
    "ixsActualizarCampoAccion": update_action,
    "ixsLimpiarDuplicadosAcciones": ixs_client.remove_duplicate_actions,
    "ixsEliminarAccion": swap_delete("accion"),
    "ixsGetAccionesProyecto": ixs_client.read_client_actions,
    "ixsListarAccionesPartes": parts_wrapper(list_parts),
    "ixsGuardarAccionParte": parts_wrapper(ixs_client.save_part),
    "ixsActualizarCampoAccionParte": parts_wrapper(update_part),
    "ixsEliminarAccionParte": parts_wrapper(delete_part),
    "ixsRecursosLeer": ixs_planning.read_resources,
    "ixsRecursosGuardar": ixs_planning.save_resource,
    "ixsPlanLeer": ixs_planning.read_plan,
    "ixsPlanGuardar": ixs_planning.save_plan,
    "ixsPlanEliminar": ixs_planning.delete_plan,
    "beeComListar": bee_com.list_communications,
    "beeComGuardar": bee_com.save_communication,
}
