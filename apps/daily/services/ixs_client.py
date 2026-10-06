"""Cliente y acciones de la vista IXS (hojas IXS_Cliente_* e IXS_Acciones*)."""

import json
import re
from collections.abc import Mapping
from typing import Any

from apps.daily.services.ixs_store import (
    IxsError,
    IxsStore,
    JsonObject,
    cell,
    project_id,
    write_lock,
)
from core.utils.js_values import (
    js_json,
    js_null_text,
    js_or_text,
    js_str,
    js_truthy,
)

"""BKD.070.016 - Cliente y acciones IXS
Equivale a ixsClienteAccionesLeer(), ixsClienteAccionesGuardar(),
ixsClienteAccionesGobierno(), ixsClienteAccionesEliminar(),
ixsClienteAccionesActualizar*(), ixsClienteAccionesLimpiarDuplicados()
y sus envolturas ixsGuardarContacto(), ixsGuardarAccion(), etc. Cada
registro es una fila UID | ID_Proyecto | DatosJSON | Actualizado.
"""

SHEETS = {
    "contacto": "IXS_Cliente_Contactos",
    "info": "IXS_Cliente_Info",
    "gobierno": "IXS_Cliente_Gobierno",
    "documento": "IXS_Cliente_Documentos",
    "accion": "IXS_Acciones",
    "parte": "IXS_Acciones_Partes",
}
HEADERS = ("UID", "ID_Proyecto", "DatosJSON", "Actualizado")
SAVE_TYPES = ("contacto", "info", "documento", "accion", "parte")
ACTION_FIELDS = (
    "accion",
    "responsable",
    "prioridad",
    "fechaInicio",
    "fechaLimite",
    "fechaReal",
    "estado",
    "dependencia",
    "notas",
)
PART_FIELDS = (
    "accion",
    "responsable",
    "fechaLimite",
    "proximaRevision",
    "estado",
    "notas",
)
MAX_GOVERNANCE_ROWS = 100
CLOSED_ACTION = re.compile(r"^completado|cancelado\Z", re.IGNORECASE)
STOPPED_ACTION = re.compile(r"detenido", re.IGNORECASE)


def sheet_name(record_type: object) -> str:
    """
    Hoja del tipo de registro, como IXS_CA_HOJAS_[tipo].

    Raises:
        IxsError: Si el tipo no existe.
    """
    name = SHEETS.get(record_type) if isinstance(record_type, str) else None

    if not name:
        raise IxsError("Tipo de registro inválido.")

    return name


def ensure_sheet(store: IxsStore, record_type: object) -> str:
    """Crea la hoja del tipo con sus encabezados (ixsCAHoja_(tipo, true))."""
    name = sheet_name(record_type)
    store.writer.ensure_sheet(name, HEADERS)

    return name


def read_records(
    store: IxsStore,
    record_type: str,
    project: str,
) -> list[JsonObject]:
    """
    Registros del proyecto con su UID, como ixsCALeerFilas_().

    Args:
        store: Hojas de la vista.
        record_type: Tipo de registro.
        project: ID del proyecto.

    Returns:
        Los datos de cada fila valida, con la llave "uid" al final.
    """
    records: list[JsonObject] = []

    for row in store.values(sheet_name(record_type))[1:]:
        if js_str(cell(row, 1)).strip() != project:
            continue

        try:
            data = json.loads(js_str(cell(row, 2) or "{}"))
        except ValueError:
            continue

        record = dict(data) if isinstance(data, dict) else {}
        record["uid"] = js_str(cell(row, 0))
        records.append(record)

    return records


def read_project(store: IxsStore, project: str) -> JsonObject:
    """
    Cliente, acciones y pendientes del proyecto (ixsCALeerInterno_).

    Args:
        store: Hojas de la vista.
        project: ID del proyecto.

    Returns:
        La respuesta completa del original.
    """
    actions = read_records(store, "accion", project)
    today = store.local_now().strftime("%Y-%m-%d")
    open_actions = [
        action
        for action in actions
        if not CLOSED_ACTION.search(state_text(action.get("estado")))
    ]

    return {
        "ok": True,
        "proyectoId": project,
        "cliente": {
            "contactos": read_records(store, "contacto", project),
            "info": (read_records(store, "info", project) or [{}])[0],
            "gobierno": read_records(store, "gobierno", project),
            "documentos": read_records(store, "documento", project),
            "resumen": {},
        },
        "acciones": {
            "filas": actions,
            "abiertas": open_actions,
            "vencidas": [
                action
                for action in open_actions
                if js_truthy(action.get("fechaLimite"))
                and js_str(action.get("fechaLimite"))[:10] < today
            ],
            "detenidas": [
                action
                for action in open_actions
                if STOPPED_ACTION.search(js_or_text(action.get("estado")))
            ],
        },
        "partes": read_records(store, "parte", project),
    }


def state_text(value: object) -> str:
    """Estado como String(x.estado || 'Pendiente')."""
    return js_str(value) if js_truthy(value) else "Pendiente"


def normalize_record(
    record_type: str, payload: Mapping[str, Any]
) -> JsonObject:
    """
    Datos del formulario con los nombres internos (ixsCANormalizar_).

    Args:
        record_type: Tipo de registro.
        payload: Formulario con llaves como "Nombre" o "Fecha_Limite".

    Returns:
        Los datos a guardar.
    """

    def pick(key: str) -> str:
        return js_null_text(payload.get(key)).strip()

    def flag(key: str) -> bool:
        return js_truthy(payload.get(key))

    if record_type == "contacto":
        return {
            "nombre": pick("Nombre"),
            "cargo": pick("Cargo"),
            "rol": pick("Rol"),
            "area": pick("Area"),
            "correo": pick("Correo"),
            "telefono": pick("Telefono"),
            "nivelDecision": pick("Nivel_Decision"),
            "estado": pick("Estado"),
            "canal": pick("Canal"),
            "alcance": pick("Alcance"),
            "notas": pick("Notas"),
            "requerimientos": flag("Requerimientos"),
            "aprueba": flag("Aprueba"),
            "valida": flag("Valida"),
            "decide": flag("Decide"),
            "informado": flag("Informado"),
            "esDecisor": flag("Es_Decisor"),
        }

    if record_type == "info":
        return {
            "areaPrincipal": pick("Area_Principal"),
            "sponsor": pick("Sponsor"),
            "productOwner": pick("Product_Owner"),
            "correoDistribucion": pick("Correo_Distribucion"),
            "rutaEscalamiento": pick("Ruta_Escalamiento"),
            "canales": pick("Canales"),
            "proximaReunion": pick("Proxima_Reunion"),
            "tipoReunion": pick("Tipo_Reunion"),
        }

    if record_type == "documento":
        return {
            "nombre": pick("Nombre"),
            "tipo": pick("Tipo"),
            "url": pick("URL"),
            "accion": pick("Accion"),
            "notas": pick("Notas"),
        }

    if record_type == "accion":
        return {
            "accion": pick("Accion"),
            "responsable": pick("Responsable"),
            "fechaInicio": pick("Fecha_Inicio"),
            "fechaLimite": pick("Fecha_Limite"),
            "fechaReal": pick("Fecha_Real"),
            "estado": pick("Estado") or "Pendiente",
            "dependencia": pick("Dependencia"),
            "prioridad": pick("Prioridad") or "Media",
            "notas": pick("Notas"),
            "comentarios": pick("Notas"),
        }

    return {
        "accion": pick("Accion"),
        "responsable": pick("Responsable"),
        "fechaLimite": pick("Fecha_Limite"),
        "proximaRevision": pick("Proxima_Revision"),
        "estado": pick("Estado") or "Pendiente",
        "notas": pick("Notas"),
    }


def save_row(
    store: IxsStore,
    record_type: str,
    project: str,
    uid: str,
    data: Mapping[str, Any],
) -> str:
    """
    Actualiza la fila del UID o agrega una nueva (ixsCAGuardarFila_).

    Args:
        store: Hojas de la vista.
        record_type: Tipo de registro.
        project: ID del proyecto.
        uid: UID existente, o "" para crear.
        data: Datos del registro.

    Returns:
        El UID guardado.

    Raises:
        IxsError: Si el UID no pertenece al proyecto.
    """
    name = ensure_sheet(store, record_type)
    rows = store.values(name)
    target = 0

    if uid and len(rows) > 1:
        target = next(
            (
                number
                for number, row in enumerate(rows[1:], start=2)
                if js_str(cell(row, 0)) == uid
                and js_str(cell(row, 1)) == project
            ),
            0,
        )

        if not target:
            raise IxsError("Registro no encontrado en este proyecto.")

    final_uid = uid or store.new_uid()
    row = [final_uid, project, js_json(data), store.iso_now()]

    if target:
        store.writer.write_row(name, target, row)
    else:
        store.writer.append_row(name, row)

    return final_uid


def read_client_actions(store: IxsStore, project_value: object) -> JsonObject:
    """ixsClienteAccionesLeer(): todo lo del proyecto."""
    return read_project(store, project_id(project_value))


def save_record(
    store: IxsStore,
    record_type: object,
    payload_value: object,
) -> JsonObject:
    """
    Guarda contacto, info, documento, accion o pendiente del cliente.

    Args:
        store: Hojas de la vista.
        record_type: Tipo de registro.
        payload_value: Formulario (incluye ID_Proyecto y UID).

    Returns:
        El proyecto actualizado con el "uid" guardado.

    Raises:
        IxsError: Con los mensajes de validacion del original.
    """
    with write_lock():
        payload = payload_value if isinstance(payload_value, dict) else {}
        project = project_id(payload.get("ID_Proyecto"))

        if record_type not in SAVE_TYPES:
            raise IxsError("Tipo inválido.")

        record_type_text = str(record_type)
        data = normalize_record(record_type_text, payload)

        if record_type_text == "contacto" and not data["nombre"]:
            raise IxsError("Escribe el nombre del contacto.")

        if record_type_text in ("accion", "parte") and not data["accion"]:
            raise IxsError("Escribe la acción.")

        if record_type_text == "info":
            uid = str(
                (read_records(store, "info", project) or [{}])[0].get("uid")
                or "",
            )
        else:
            uid = js_or_text(payload.get("UID")).strip()

        saved = save_row(store, record_type_text, project, uid, data)

        return {**read_project(store, project), "uid": saved}


def save_governance(
    store: IxsStore,
    project_value: object,
    rows_value: object,
) -> JsonObject:
    """
    Reemplaza las reuniones de gobierno del proyecto.

    Args:
        store: Hojas de la vista.
        project_value: ID del proyecto.
        rows_value: Lista de reuniones (Reunion, Frecuencia, ...).

    Returns:
        El proyecto actualizado.
    """
    with write_lock():
        project = project_id(project_value)
        name = ensure_sheet(store, "gobierno")

        if (
            not isinstance(rows_value, list)
            or len(rows_value) > MAX_GOVERNANCE_ROWS
        ):
            raise IxsError("Lista de reuniones inválida.")

        existing = store.values(name)

        for number in range(len(existing), 1, -1):
            if js_str(cell(existing[number - 1], 1)) == project:
                store.writer.delete_row(name, number)

        for item in rows_value:
            meeting = item if isinstance(item, dict) else {}

            if js_or_text(meeting.get("Reunion")).strip():
                save_row(
                    store,
                    "gobierno",
                    project,
                    "",
                    {
                        "reunion": js_or_text(meeting.get("Reunion")),
                        "frecuencia": js_or_text(meeting.get("Frecuencia")),
                        "participantes": js_or_text(
                            meeting.get("Participantes")
                        ),
                        "canal": js_or_text(meeting.get("Canal")),
                    },
                )

        return read_project(store, project)


def delete_record(
    store: IxsStore,
    record_type: object,
    project_value: object,
    uid: object,
) -> JsonObject:
    """
    Elimina el registro del proyecto (busca desde la ultima fila).

    Args:
        store: Hojas de la vista.
        record_type: Tipo de registro.
        project_value: ID del proyecto.
        uid: UID del registro.

    Returns:
        El proyecto actualizado.
    """
    with write_lock():
        project = project_id(project_value)
        name = sheet_name(record_type)

        if not store.reader.sheet_exists(name):
            raise IxsError("Registro no encontrado.")

        rows = store.values(name)
        wanted = uid_text(uid)
        number = next(
            (
                number
                for number in range(len(rows), 1, -1)
                if js_str(cell(rows[number - 1], 0)) == wanted
                and js_str(cell(rows[number - 1], 1)) == project
            ),
            0,
        )

        if not number:
            raise IxsError("Registro no encontrado en este proyecto.")

        store.writer.delete_row(name, number)

        return read_project(store, project)


def uid_text(uid: object) -> str:
    """UID como String(uid); un argumento ausente es "undefined"."""
    return "undefined" if uid is None else js_str(uid)


def update_field(
    store: IxsStore,
    record_type: str,
    request: tuple[object, object, object, object],
) -> JsonObject:
    """
    Cambia un campo de una accion o de un pendiente.

    Args:
        store: Hojas de la vista.
        record_type: "accion" o "parte".
        request: ID del proyecto, UID, campo y valor.

    Returns:
        El proyecto actualizado.
    """
    project_value, uid, field_name, value = request
    allowed = ACTION_FIELDS if record_type == "accion" else PART_FIELDS
    missing = (
        "Acción no encontrada."
        if record_type == "accion"
        else ("Pendiente no encontrado.")
    )

    with write_lock():
        project = project_id(project_value)

        if field_name not in allowed:
            raise IxsError("Campo no editable.")

        wanted = uid_text(uid)
        record = next(
            (
                item
                for item in read_records(store, record_type, project)
                if item["uid"] == wanted
            ),
            None,
        )

        if record is None:
            raise IxsError(missing)

        record[str(field_name)] = js_null_text(value)

        if record_type == "accion" and field_name == "notas":
            record["comentarios"] = record["notas"]

        save_row(store, record_type, project, wanted, record)

        return read_project(store, project)


def remove_duplicate_actions(
    store: IxsStore, project_value: object
) -> JsonObject:
    """
    Borra acciones repetidas (accion, responsable y fecha limite).

    Conserva la de mas abajo, como el original que recorre desde la
    ultima fila.

    Args:
        store: Hojas de la vista.
        project_value: ID del proyecto.

    Returns:
        El proyecto con "eliminados".
    """
    with write_lock():
        project = project_id(project_value)
        name = SHEETS["accion"]

        if not store.reader.sheet_exists(name):
            return {**read_project(store, project), "eliminados": 0}

        rows = store.values(name)
        seen: set[str] = set()
        removed = 0

        for number in range(len(rows), 1, -1):
            row = rows[number - 1]

            if js_str(cell(row, 1)) != project:
                continue

            try:
                action = json.loads(js_str(cell(row, 2) or "{}"))
            except ValueError as error:
                raise IxsError(str(error)) from error

            action = action if isinstance(action, dict) else {}
            key = "|".join(
                js_or_text(action.get(name_key)).strip().lower()
                for name_key in ("accion", "responsable", "fechaLimite")
            )

            if key in seen:
                store.writer.delete_row(name, number)
                removed += 1
            else:
                seen.add(key)

        return {**read_project(store, project), "eliminados": removed}


def save_part(
    store: IxsStore,
    project_value: object,
    part_value: object,
) -> JsonObject:
    """ixsGuardarAccionParte(): guarda un pendiente del formulario."""
    part = part_value if isinstance(part_value, dict) else {}
    payload = {
        **part,
        "ID_Proyecto": project_value,
        "Accion": part.get("accion"),
        "Responsable": part.get("responsable"),
        "Fecha_Limite": part.get("fechaLimite"),
        "Proxima_Revision": part.get("proximaRevision"),
        "Estado": part.get("estado"),
        "Notas": part.get("notas"),
    }

    return save_record(store, "parte", payload)


def parts_only(result: JsonObject) -> JsonObject:
    """{"ok": True, "filas": partes} o el error tal cual."""
    return (
        {"ok": True, "filas": result["partes"]} if result.get("ok") else result
    )


def with_client_key(result: JsonObject, key: str) -> JsonObject:
    """Agrega result.cliente[key] arriba, como las envolturas del original."""
    if not result.get("ok"):
        return result

    return {**result, key: result["cliente"][key]}
