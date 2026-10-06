"""Pendientes Beecker / Cliente de un proyecto AER/T&M."""

import re
from datetime import date
from typing import Any

from apps.aer.services.ai_common import (
    AerAiContext,
    AerAiError,
    clip,
    read_rows,
    validate_project,
)
from core.exceptions import DashboardError, describe_error
from core.utils.js_values import js_locale_key
from core.utils.locks import script_lock

"""BKD.080.013 - IA AER: pendientes Beecker / Cliente
Equivale a listarAccionesPartesAER(), guardarAccionParteAER(),
actualizarCampoAccionParteAER() y eliminarAccionParteAER(): una hoja
para todo el portafolio (AER_Acciones_BeeckerCliente) con UID por fila.
"""

JsonObject = dict[str, Any]

SHEET = "AER_Acciones_BeeckerCliente"
HEADERS = (
    "UID",
    "ID_Proyecto",
    "Accion",
    "Responsable",
    "Fecha_Compromiso",
    "Proxima_Revision",
    "Estado",
    "Notas",
    "Actualizado",
)
KINDS = ("", "", "", "", "date", "date", "", "", "datetime")
STATES = {
    "pendiente": "Pendiente",
    "en progreso": "En progreso",
    "detenido": "Detenido",
    "completado": "Completado",
}
FIELDS = {
    "accion": 2,
    "responsable": 3,
    "fechaLimite": 4,
    "proximaRevision": 5,
    "estado": 6,
    "notas": 7,
}
ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
UPDATED_COLUMN = 9


def text(value: object, limit: int = 500) -> str:
    """String(v ?? '').trim().slice(0, max || 500)."""
    return clip(value, limit or 500)


def side(value: object) -> str:
    """Beecker o Cliente (_aerp67Parte)."""
    lowered = text(value, 30).lower()

    if lowered not in ("beecker", "cliente"):
        raise AerAiError("El responsable debe ser Beecker o Cliente.")

    return "Cliente" if lowered == "cliente" else "Beecker"


def state(value: object) -> str:
    """Pendiente, En progreso, Detenido o Completado (_aerp67Estado)."""
    lowered = text(value, 30).lower()

    if lowered not in STATES:
        raise AerAiError("Estado de acción inválido.")

    return STATES[lowered]


def day(value: object) -> str:
    """YYYY-MM-DD valida o vacio (_aerp67Fecha)."""
    raw = text(value, 20)

    if not raw:
        return ""

    if not ISO_DATE.match(raw):
        raise AerAiError("Fecha inválida.")

    try:
        date.fromisoformat(raw)
    except ValueError as error:
        raise AerAiError("Fecha inválida.") from error

    return raw


def project_parts(ctx: AerAiContext, project_id: str) -> list[JsonObject]:
    """Pendientes del proyecto ordenados por fecha compromiso y accion."""
    parts = [
        {
            "uid": row[0],
            "accion": row[2],
            "responsable": row[3],
            "fechaLimite": row[4],
            "proximaRevision": row[5],
            "estado": row[6],
            "notas": row[7],
            "actualizado": row[8],
        }
        for row in read_rows(ctx.reader, SHEET, KINDS)
        if row[1] == project_id and row[0]
    ]
    parts.sort(key=lambda part: js_locale_key(part["accion"]))
    parts.sort(key=lambda part: js_locale_key(part["fechaLimite"] or "9999"))

    return parts


def list_parts(ctx: AerAiContext, project_value: object) -> JsonObject:
    """listarAccionesPartesAER()."""
    try:
        project_id = validate_project(ctx.reader, project_value)

        return {"ok": True, "filas": project_parts(ctx, project_id)}
    except DashboardError as error:
        return {"ok": False, "error": describe_error(error)}


def find_row(ctx: AerAiContext, uid: str, project_id: str) -> int:
    """Numero de fila (base 1) del UID en el proyecto; 0 si no esta."""
    for number, row in enumerate(read_rows(ctx.reader, SHEET, KINDS), start=2):
        if row[0] == uid and row[1] == project_id:
            return number

    return 0


def save_part(
    ctx: AerAiContext,
    project_value: object,
    data: Any,
) -> JsonObject:
    """Crea o reemplaza un pendiente (guardarAccionParteAER)."""
    try:
        project_id = validate_project(ctx.reader, project_value)
        values = data if isinstance(data, dict) else {}
        action = text(values.get("accion"), 360)

        if not action:
            raise AerAiError("Captura la acción o entregable.")

        owner = side(values.get("responsable") or "Beecker")
        due = day(values.get("fechaLimite"))
        review = day(values.get("proximaRevision"))
        status = state(values.get("estado") or "Pendiente")

        with script_lock(10):
            if not ctx.reader.sheet_exists(SHEET):
                ctx.writer.ensure_sheet(SHEET, HEADERS)

            uid = text(values.get("uid"), 60) or ctx.new_uid()
            row_number = len(read_rows(ctx.reader, SHEET, KINDS)) + 2

            if values.get("uid"):
                row_number = find_row(ctx, uid, project_id)

                if not row_number:
                    raise AerAiError(
                        "No se encontró la acción en este proyecto."
                    )

            ctx.writer.write_row(
                SHEET,
                row_number,
                [
                    uid,
                    project_id,
                    action,
                    owner,
                    due,
                    review,
                    status,
                    text(values.get("notas"), 2000),
                    ctx.stamp(),
                ],
            )

        return {
            "ok": True,
            "uid": uid,
            "filas": project_parts(ctx, project_id),
        }
    except DashboardError as error:
        return {"ok": False, "error": describe_error(error)}


def update_part(
    ctx: AerAiContext,
    project_value: object,
    uid_value: object,
    field_name: object,
    value: object,
) -> JsonObject:
    """Cambia un campo del pendiente (actualizarCampoAccionParteAER)."""
    try:
        project_id = validate_project(ctx.reader, project_value)
        uid = text(uid_value, 60)
        name = str(field_name) if isinstance(field_name, str) else ""

        if name not in FIELDS:
            raise AerAiError("Campo no permitido.")

        with script_lock(10):
            if not read_rows(ctx.reader, SHEET, KINDS):
                raise AerAiError("No hay acciones registradas.")

            row_number = find_row(ctx, uid, project_id)

            if not row_number:
                raise AerAiError("No se encontró esta acción.")

            if name == "responsable":
                new_value = side(value)
            elif name == "estado":
                new_value = state(value)
            elif name in ("fechaLimite", "proximaRevision"):
                new_value = day(value)
            else:
                new_value = text(value, 2000 if name == "notas" else 360)

            if name == "accion" and not new_value:
                raise AerAiError("La acción no puede quedar vacía.")

            ctx.writer.write_cell(
                SHEET, row_number, FIELDS[name] + 1, new_value
            )
            ctx.writer.write_cell(
                SHEET, row_number, UPDATED_COLUMN, ctx.stamp()
            )

        return {"ok": True, "filas": project_parts(ctx, project_id)}
    except DashboardError as error:
        return {"ok": False, "error": describe_error(error)}


def delete_part(
    ctx: AerAiContext,
    project_value: object,
    uid_value: object,
) -> JsonObject:
    """Borra un pendiente (eliminarAccionParteAER)."""
    try:
        project_id = validate_project(ctx.reader, project_value)
        uid = text(uid_value, 60)

        with script_lock(10):
            if not read_rows(ctx.reader, SHEET, KINDS):
                raise AerAiError("No hay acciones.")

            row_number = find_row(ctx, uid, project_id)

            if not row_number:
                raise AerAiError("Acción no encontrada.")

            ctx.writer.delete_row(SHEET, row_number)

        return {"ok": True, "filas": project_parts(ctx, project_id)}
    except DashboardError as error:
        return {"ok": False, "error": describe_error(error)}
