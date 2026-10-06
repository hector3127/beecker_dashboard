"""Panel de conexion de Clockify: proyectos, vinculos y diagnosticos."""

import re
from dataclasses import dataclass
from typing import Any

from apps.clockify.constants import SHEET_MPB, SHEET_PROJECT_LINKS
from apps.clockify.services.project_matcher import normalize_link_key
from apps.clockify.services.time_entry_loader import ClockifyTimeEntryLoader
from core.exceptions import DashboardError, describe_error
from core.sheets.protocols import SheetReader, SheetWriter
from core.utils.js_values import js_or_text
from core.utils.text import to_text

"""BKD.020.018 - Panel de conexion de Clockify
Equivale a listarProyectosClockify(), guardarVinculoProyectoClockify(),
diagnosticarConexionClockifyProyecto(), diagnosticarHorasClockifyProyecto()
y _clockifyIdentidadEfectiva_() de ClockifyService.gs. Los vinculos se
guardan en la hoja Clockify_Vinculos en lugar de PropertiesService.
"""

JsonObject = dict[str, Any]

SETUP_ERROR = "Configura tu API key y workspace de Clockify primero."
LINK_HEADERS = ("ID_Proyecto", "Clockify_Project_ID")
VALID_ID = re.compile(r"^[\w.\-]+$", re.ASCII)
QUERY_VERSION = "2026-09-29-V24"
SIMILAR_LIMIT = 8
KEY_SUFFIX = 4
SUCCESS_LIMIT = 300
CONNECTION_TYPE = "global (.env)"
ACCESS_HINT = (
    " Si el titular no tiene acceso para listar usuarios y Reportes también "
    "devuelve 403, pide una API key de una cuenta con esos permisos en este "
    "workspace."
)
EMPTY_NOTE = (
    " Clockify no devolvió registros visibles en este rango; comprueba este "
    "mismo ID y fechas en su reporte detallado."
)


@dataclass(frozen=True, slots=True)
class PanelContext:
    """Cargador (None si falta configuracion), API key y workspace."""

    loader: ClockifyTimeEntryLoader | None
    api_key: str
    workspace_id: str


def list_projects(context: PanelContext) -> JsonObject:
    """Proyectos del workspace (listarProyectosClockify)."""
    if context.loader is None:
        return {"ok": False, "error": SETUP_ERROR, "proyectos": []}

    try:
        projects = context.loader.list_clockify_projects()
    except DashboardError as error:
        return {"ok": False, "error": describe_error(error), "proyectos": []}

    return {
        "ok": True,
        "proyectos": [
            {
                "id": project.project_id,
                "nombre": project.name,
                "clienteId": project.client_id,
            }
            for project in projects
        ],
    }


def write_link(
    reader: SheetReader,
    writer: SheetWriter,
    internal_id: str,
    clockify_id: str,
) -> None:
    """Crea o actualiza el vinculo en Clockify_Vinculos."""
    if not reader.sheet_exists(SHEET_PROJECT_LINKS):
        writer.ensure_sheet(SHEET_PROJECT_LINKS, LINK_HEADERS)

    values = reader.read_values(SHEET_PROJECT_LINKS)
    headers = [to_text(cell).strip() for cell in (values[0] if values else [])]
    id_column = (
        headers.index(LINK_HEADERS[0]) if LINK_HEADERS[0] in headers else 0
    )
    link_column = (
        headers.index(LINK_HEADERS[1]) if LINK_HEADERS[1] in headers else 1
    )
    key = normalize_link_key(internal_id)

    for row_number, row in enumerate(values[1:], start=2):
        cell = row[id_column] if id_column < len(row) else ""

        if normalize_link_key(to_text(cell)) == key:
            writer.write_cell(
                SHEET_PROJECT_LINKS,
                row_number,
                link_column + 1,
                clockify_id,
            )
            return

    new_row = [""] * max(len(headers), 2)
    new_row[id_column] = internal_id
    new_row[link_column] = clockify_id
    writer.append_row(SHEET_PROJECT_LINKS, new_row)


def save_link(
    context: PanelContext,
    reader: SheetReader,
    writer: SheetWriter,
    project_value: object,
    clockify_value: object,
) -> JsonObject:
    """
    Vincula un ID del panel con un proyecto de Clockify.

    Equivale a guardarVinculoProyectoClockify(); el vinculo prevalece sobre
    la coincidencia por nombre al consultar horas.
    """
    internal_id = js_or_text(project_value).strip()

    if not internal_id or not VALID_ID.match(internal_id):
        return {"ok": False, "error": "Escribe un ID interno válido."}

    listing = list_projects(context)

    if not listing["ok"]:
        return {"ok": False, "error": listing["error"]}

    target = next(
        (
            project
            for project in listing["proyectos"]
            if str(project["id"]) == js_or_text(clockify_value)
        ),
        None,
    )

    if target is None:
        return {
            "ok": False,
            "error": (
                "Selecciona un proyecto visible en el workspace activo de "
                "Clockify."
            ),
        }

    try:
        write_link(reader, writer, internal_id, target["id"])
    except DashboardError as error:
        return {"ok": False, "error": describe_error(error)}

    return {
        "ok": True,
        "idInterno": internal_id,
        "nombreClockify": target["nombre"],
    }


def connection_check(
    context: PanelContext, project_value: object
) -> JsonObject:
    """
    Workspace, proyectos visibles y proyecto encontrado para el ID.

    Equivale a diagnosticarConexionClockifyProyecto().
    """
    internal_id = js_or_text(project_value).strip()

    if not internal_id:
        return {"ok": False, "error": "Escribe el ID de un proyecto que falta."}

    if context.loader is None:
        return {
            "ok": False,
            "error": "Falta conectar Clockify y elegir el workspace.",
        }

    connection = {
        "conexionGlobal": True,
        "workspace": context.workspace_id,
        "sufijo": context.api_key[-KEY_SUFFIX:],
    }
    listing = list_projects(context)

    if not listing["ok"]:
        return {"ok": False, **connection, "error": listing["error"]}

    try:
        match = context.loader.find_clockify_project(internal_id)
    except DashboardError as error:
        return {"ok": False, "error": describe_error(error)}

    base = internal_id.split("_")[0].lower()
    similar = [
        project["nombre"]
        for project in listing["proyectos"]
        if base in str(project["nombre"]).lower()
    ][:SIMILAR_LIMIT]

    return {
        "ok": True,
        **connection,
        "totalProyectos": len(listing["proyectos"]),
        "proyectoEncontrado": match.name if match else "",
        "similares": similar,
    }


def identity_text(context: PanelContext) -> str:
    """Titular de la API key sin exponerla (_clockifyIdentidadEfectiva_)."""
    prefix = f"Conexión {CONNECTION_TYPE}"

    if context.loader is None:
        return f"{prefix}: falta API key o workspace."

    key_text = f"{prefix}, clave ****{context.api_key[-KEY_SUFFIX:]}"

    try:
        response = context.loader.create_client().get("/user")

        if response.status_code >= SUCCESS_LIMIT:
            return (
                f"{key_text}: Clockify no permitió identificar al titular "
                f"(HTTP {response.status_code})."
            )

        user = response.json()
    except (DashboardError, ValueError) as error:
        return f"{key_text}: no se pudo identificar al titular ({error})."

    holder = user.get("name") or user.get("email") or user.get("id")
    email = (
        f" ({user['email']})" if user.get("email") and user.get("name") else ""
    )

    return (
        f"{key_text}, titular: {holder or 'desconocido'}{email}, workspace "
        f"ID: {context.workspace_id}."
    )


def hours_check(context: PanelContext, project_value: object) -> JsonObject:
    """
    Lee las horas del proyecto sin cache (diagnosticarHorasClockifyProyecto).

    Args:
        context: Cargador, API key y workspace.
        project_value: ID interno del proyecto.

    Returns:
        {ok, versionConsulta, error, aviso, registros, usuariosConsultados,
        rango}.
    """
    internal_id = js_or_text(project_value).strip()
    version = {"versionConsulta": QUERY_VERSION}

    if not internal_id:
        return {
            "ok": False,
            **version,
            "error": "Escribe el ID interno del proyecto.",
        }

    if context.loader is None:
        return {"ok": False, **version, "error": SETUP_ERROR}

    date_range = context.loader.resolve_range(internal_id)

    if date_range.start_date is None:
        message = (
            f'No se encontró INICIO en MPB para "{internal_id}" '
            "(SERVICE AER/TYM)."
            if date_range.source == SHEET_MPB
            else f'No se encontró fecha de Discovery para "{internal_id}".'
        )
        return {"ok": False, **version, "error": message}

    identity = identity_text(context)
    range_info = {
        "fechaInicio": date_range.start_date.isoformat(),
        "fechaFin": (
            date_range.end_date.isoformat() if date_range.end_date else None
        ),
        "fuente": date_range.source,
    }

    try:
        hours, request_count = context.loader.load_fresh_project_hours(
            internal_id,
        )
    except DashboardError as error:
        return {
            "ok": False,
            **version,
            "error": f"{describe_error(error)} {identity}{ACCESS_HINT}",
            "aviso": f" {identity}",
            "registros": None,
            "usuariosConsultados": 0,
            "rango": range_info,
        }

    notice = (
        f"Proyecto Clockify: {hours.project_name} [{hours.project_id}]. "
        f"Reporte detallado: {request_count} consulta(s)."
        + ("" if hours.entries else EMPTY_NOTE)
    )

    return {
        "ok": True,
        **version,
        "error": "",
        "aviso": f"{notice} {identity}",
        "registros": len(hours.entries),
        "usuariosConsultados": len(
            {entry.resource_name for entry in hours.entries},
        ),
        "rango": range_info,
    }
