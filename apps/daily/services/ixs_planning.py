"""Recursos y planeacion (vacaciones y compromisos) de la vista IXS."""

import json
import math
import re
import unicodedata
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from apps.daily.services.ixs_store import (
    IxsError,
    IxsStore,
    JsonObject,
    cell,
    project_id,
    write_lock,
)
from core.utils.cell_types import CellValue
from core.utils.js_values import (
    js_json,
    js_number,
    js_or_text,
    js_str,
    to_json_number,
)

"""BKD.070.017 - Recursos y planeacion IXS
Equivale a ixsRecursosLeer(), ixsRecursosGuardar(), ixsPlanLeer(),
ixsPlanGuardar() e ixsPlanEliminar(). Los recursos viven en la hoja
Recursos (el estado vacio equivale a Activo) y la planeacion en
IXS_Planeacion con una fila JSON por registro.
"""

RESOURCES_SHEET = "Recursos"
OLD_RESOURCES_SHEET = "IXS_Recursos_Asignados"
PLAN_SHEET = "IXS_Planeacion"
PLAN_HEADERS = ("UID", "ID_Proyecto", "Tipo", "DatosJSON", "Actualizado")
PLAN_TYPES = ("vacacion", "compromiso")
INACTIVE_VALUES = ("inactivo", "false", "no")
MAX_NAME_LENGTH = 150
MAX_ROLE_LENGTH = 100
MAX_HOURS = 100000
MIN_HEADER_COLUMNS = 4
ISO_DAY = re.compile(r"\d{4}-\d{2}-\d{2}", re.ASCII)
MISSING = object()


@dataclass(frozen=True, slots=True)
class ResourceColumns:
    """Columnas (base 0) de la hoja Recursos."""

    project: int
    role: int
    name: int
    hours: int
    state: int


def resource_key(value: object) -> str:
    """
    Llave de comparacion, como ixsRecursosClave_().

    Args:
        value: Texto o celda.

    Returns:
        Sin acentos, con espacios simples y en minusculas.
    """
    text = unicodedata.normalize("NFD", js_or_text(value).strip())
    text = "".join(
        character
        for character in text
        if not 0x0300 <= ord(character) <= 0x036F
    )

    return re.sub(r"\s+", " ", text).lower()


def last_column(rows: list[list[CellValue]]) -> int:
    """Ultima columna con datos, como sheet.getLastColumn()."""
    return max((len(row) for row in rows), default=0)


def resource_columns(
    store: IxsStore, rows: list[list[CellValue]]
) -> ResourceColumns:
    """
    Ubica las columnas de Recursos (ixsRecursosColumnas_).

    Si falta la columna de estado agrega el encabezado "Estado".

    Raises:
        IxsError: Si falta Proyecto, Posicion, Nombre u Horas.
    """
    width = max(MIN_HEADER_COLUMNS, last_column(rows))
    raw = [cell(rows[0] if rows else [], index) for index in range(width)]
    headers = [resource_key(header) for header in raw]

    def find(*alternatives: str) -> int:
        return next(
            (
                index
                for index, header in enumerate(headers)
                if header in alternatives
            ),
            -1,
        )

    columns = {
        "project": find("proyecto", "id_proyecto", "id proyecto"),
        "role": find("posicion", "rol"),
        "name": find("nombre del recurso", "nombre", "recurso"),
        "hours": find("horas estimadas", "horas_estimadas", "horas estimada"),
        "state": find("estado", "activo"),
    }

    if (
        min(
            columns["project"],
            columns["role"],
            columns["name"],
            columns["hours"],
        )
        < 0
    ):
        raise IxsError(
            "La hoja Recursos debe contener Proyecto, Posición, Nombre del "
            "recurso y Horas Estimadas.",
        )

    if columns["state"] < 0:
        columns["state"] = len(raw)
        store.writer.write_cell(
            RESOURCES_SHEET, 1, columns["state"] + 1, "Estado"
        )

    return ResourceColumns(**columns)


def resources_sheet(store: IxsStore) -> ResourceColumns:
    """
    Columnas de Recursos; copia y elimina la hoja anterior si existe.

    Equivale a ixsRecursosHoja_(): las asignaciones de
    IXS_Recursos_Asignados pasan a Recursos y despues se borra esa hoja.

    Raises:
        IxsError: Si no existe la hoja Recursos.
    """
    if not store.reader.sheet_exists(RESOURCES_SHEET):
        raise IxsError("No se encontró la hoja Recursos.")

    columns = resource_columns(store, store.values(RESOURCES_SHEET))

    if store.reader.sheet_exists(OLD_RESOURCES_SHEET):
        migrate_old_resources(store, columns)

    return columns


def migrate_old_resources(store: IxsStore, columns: ResourceColumns) -> None:
    """Copia IXS_Recursos_Asignados a Recursos y elimina la hoja anterior."""
    old_rows = store.values(OLD_RESOURCES_SHEET)[1:]
    existing = store.values(RESOURCES_SHEET)
    index: dict[str, int] = {}

    for number, row in enumerate(existing[1:], start=2):
        key = (
            f"{resource_key(cell(row, columns.project))}|"
            f"{resource_key(cell(row, columns.name))}"
        )

        if key != "|":
            index[key] = number

    last_row = len(existing)

    def write(row_number: int, column: int, value: CellValue) -> None:
        store.writer.write_cell(RESOURCES_SHEET, row_number, column + 1, value)

    for old in old_rows:
        project, name = cell(old, 0), cell(old, 1)

        if not js_str(project).strip() or not js_str(name).strip():
            continue

        key = f"{resource_key(project)}|{resource_key(name)}"
        row_number = index.get(key)

        if not row_number:
            last_row += 1
            row_number = last_row
            index[key] = row_number
            write(row_number, columns.project, project)
            write(row_number, columns.name, name)

        hours = js_number(cell(old, 3))
        state = cell(old, 4)
        write(row_number, columns.role, cell(old, 2))
        write(row_number, columns.hours, number_or_zero(hours))
        write(
            row_number,
            columns.state,
            "Inactivo"
            if state is False or js_str(state).lower() == "false"
            else "Activo",
        )

    store.writer.delete_sheet(OLD_RESOURCES_SHEET)


def number_or_zero(number: float) -> int | float:
    """Number(x) || 0."""
    if math.isnan(number) or number == 0:
        return 0

    return to_json_number(number)


def read_resources_for(store: IxsStore, project: str) -> JsonObject:
    """Recursos del proyecto (ixsRecursosLeer_)."""
    columns = resources_sheet(store)
    wanted = resource_key(project)
    rows = store.values(RESOURCES_SHEET)[1:]

    return {
        "ok": True,
        "proyectoId": project,
        "filas": [
            {
                "nombre": js_str(cell(row, columns.name)).strip(),
                "rol": js_or_text(cell(row, columns.role)),
                "horasEstimadas": number_or_zero(
                    js_number(cell(row, columns.hours)),
                ),
                "activo": resource_key(cell(row, columns.state))
                not in INACTIVE_VALUES,
            }
            for row in rows
            if resource_key(cell(row, columns.project)) == wanted
            and js_str(cell(row, columns.name)).strip()
        ],
    }


def read_resources(store: IxsStore, project_value: object) -> JsonObject:
    """ixsRecursosLeer(): recursos asignados al proyecto."""
    with write_lock():
        return read_resources_for(store, project_id(project_value))


def save_resource(store: IxsStore, payload_value: object) -> JsonObject:
    """
    Agrega o actualiza un recurso del proyecto (ixsRecursosGuardar).

    Args:
        store: Hojas de la vista.
        payload_value: idProyecto, nombre, rol, horasEstimadas y activo.

    Returns:
        Los recursos del proyecto.

    Raises:
        IxsError: Con los mensajes de validacion del original.
    """
    with write_lock():
        payload: Mapping[str, Any] = (
            payload_value if isinstance(payload_value, dict) else {}
        )
        project = project_id(payload.get("idProyecto"))
        name = js_or_text(payload.get("nombre")).strip()
        role = js_or_text(payload.get("rol")).strip()
        raw_hours = payload.get("horasEstimadas", MISSING)
        hours = math.nan if raw_hours is MISSING else js_number(raw_hours)

        if not name or len(name) > MAX_NAME_LENGTH:
            raise IxsError("Escribe un nombre válido.")

        if not role or len(role) > MAX_ROLE_LENGTH:
            raise IxsError("Escribe el rol del recurso.")

        if not math.isfinite(hours) or hours < 0 or hours > MAX_HOURS:
            raise IxsError("Las horas estimadas deben ser un número válido.")

        columns = resources_sheet(store)
        rows = store.values(RESOURCES_SHEET)
        target = next(
            (
                number
                for number, row in enumerate(rows[1:], start=2)
                if resource_key(cell(row, columns.project))
                == resource_key(project)
                and resource_key(cell(row, columns.name)) == resource_key(name)
            ),
            len(rows) + 1,
        )
        values: list[tuple[int, CellValue]] = [
            (columns.project, project),
            (columns.name, name),
            (columns.role, role),
            (columns.hours, to_json_number(hours)),
            (
                columns.state,
                "Inactivo" if payload.get("activo") is False else "Activo",
            ),
        ]

        for column, value in values:
            store.writer.write_cell(RESOURCES_SHEET, target, column + 1, value)

        return read_resources_for(store, project)


def read_plan_for(store: IxsStore, project: str) -> JsonObject:
    """Vacaciones y compromisos del proyecto (ixsPlanLeer_)."""
    store.writer.ensure_sheet(PLAN_SHEET, PLAN_HEADERS)
    result: JsonObject = {
        "ok": True,
        "proyectoId": project,
        "vacaciones": [],
        "compromisos": [],
    }

    for row in store.values(PLAN_SHEET)[1:]:
        plan_type = js_str(cell(row, 2))

        if (
            js_str(cell(row, 1)).strip() != project
            or plan_type not in PLAN_TYPES
        ):
            continue

        try:
            item = json.loads(js_str(cell(row, 3) or "{}"))
        except ValueError:
            continue

        if item is None:
            continue

        if isinstance(item, dict):
            item["uid"] = js_str(cell(row, 0))

        key = "vacaciones" if plan_type == "vacacion" else "compromisos"
        result[key].append(item)

    return result


def read_plan(store: IxsStore, project_value: object) -> JsonObject:
    """ixsPlanLeer(): planeacion del proyecto."""
    return read_plan_for(store, project_id(project_value))


def is_iso_day(value: object) -> bool:
    """Fecha YYYY-MM-DD, como el regex del original sobre String(x || "")."""
    return bool(ISO_DAY.fullmatch(js_or_text(value)))


def plan_data(plan_type: str, payload: Mapping[str, Any]) -> JsonObject:
    """
    Datos validados de una vacacion o un compromiso.

    Raises:
        IxsError: Si faltan datos o las fechas no son validas.
    """
    if plan_type == "vacacion":
        start, end = payload.get("inicio"), payload.get("fin")

        if (
            not js_or_text(payload.get("recurso")).strip()
            or not is_iso_day(start)
            or not is_iso_day(end)
            or js_str(start) > js_str(end)
        ):
            raise IxsError("Indica recurso y fechas válidas.")

        return {
            "recurso": js_str(payload.get("recurso")).strip(),
            "inicio": start,
            "fin": end,
            "estado": text_or(payload.get("estado"), "Pendiente"),
            "comentarios": js_or_text(payload.get("comentarios")).strip(),
            "registradoPor": js_or_text(payload.get("registradoPor")).strip(),
        }

    if not js_or_text(payload.get("actividad")).strip() or not is_iso_day(
        payload.get("fecha"),
    ):
        raise IxsError("Indica actividad y fecha válida.")

    return {
        "actividad": js_str(payload.get("actividad")).strip(),
        "fecha": payload.get("fecha"),
        "responsable": js_or_text(payload.get("responsable")).strip(),
        "estado": text_or(payload.get("estado"), "Pendiente"),
        "tipo": text_or(payload.get("tipo"), "Actividad"),
    }


def text_or(value: object, default: str) -> str:
    """String(x || default).trim()."""
    return (js_or_text(value) or default).strip()


def save_plan(
    store: IxsStore,
    plan_type: object,
    payload_value: object,
) -> JsonObject:
    """
    Agrega o actualiza una vacacion o un compromiso (ixsPlanGuardar).

    Args:
        store: Hojas de la vista.
        plan_type: "vacacion" o "compromiso".
        payload_value: Datos del formulario con idProyecto y uid.

    Returns:
        La planeacion del proyecto.
    """
    with write_lock():
        if plan_type not in PLAN_TYPES:
            raise IxsError("Tipo de registro inválido.")

        payload: Mapping[str, Any] = (
            payload_value if isinstance(payload_value, dict) else {}
        )
        project = project_id(payload.get("idProyecto"))
        uid = js_or_text(payload.get("uid")).strip()
        data = plan_data(str(plan_type), payload)
        store.writer.ensure_sheet(PLAN_SHEET, PLAN_HEADERS)
        rows = store.values(PLAN_SHEET)
        target = (
            next(
                (
                    number
                    for number, row in enumerate(rows[1:], start=2)
                    if js_str(cell(row, 0)) == uid
                    and js_str(cell(row, 1)).strip() == project
                    and js_str(cell(row, 2)) == plan_type
                ),
                0,
            )
            if uid
            else 0
        )

        if uid and not target:
            raise IxsError("Registro no encontrado en este proyecto.")

        row = [
            uid or store.new_uid(),
            project,
            str(plan_type),
            js_json(data),
            store.iso_now(),
        ]

        if target:
            store.writer.write_row(PLAN_SHEET, target, row)
        else:
            store.writer.append_row(PLAN_SHEET, row)

        return read_plan_for(store, project)


def delete_plan(
    store: IxsStore,
    plan_type: object,
    project_value: object,
    uid: object,
) -> JsonObject:
    """
    Elimina una vacacion o un compromiso del proyecto (ixsPlanEliminar).

    Returns:
        La planeacion del proyecto.
    """
    with write_lock():
        project = project_id(project_value)
        store.writer.ensure_sheet(PLAN_SHEET, PLAN_HEADERS)

        if plan_type not in PLAN_TYPES or not js_or_text(uid):
            raise IxsError("Registro inválido.")

        rows = store.values(PLAN_SHEET)
        target = next(
            (
                number
                for number, row in enumerate(rows[1:], start=2)
                if js_str(cell(row, 0)) == js_str(uid)
                and js_str(cell(row, 1)).strip() == project
                and js_str(cell(row, 2)) == plan_type
            ),
            0,
        )

        if not target:
            raise IxsError("Registro no encontrado en este proyecto.")

        store.writer.delete_row(PLAN_SHEET, target)

        return read_plan_for(store, project)
