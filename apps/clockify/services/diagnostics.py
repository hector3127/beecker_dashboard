"""Diagnosticos de Clockify por miembros del proyecto."""

import time
import unicodedata
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import quote

from apps.clockify.exceptions import ClockifyRequestError
from apps.clockify.services.clockify_client import ClockifyClient
from apps.clockify.services.date_ranges import ProjectDateRange
from apps.clockify.services.duration_parser import parse_duration_hours
from apps.clockify.services.project_views import utc_midnight_iso
from apps.clockify.services.time_entry_loader import ClockifyTimeEntryLoader
from core.exceptions import DashboardError, describe_error
from core.utils.numbers import round_half_up
from core.utils.text import extract_base_id, get_flexible_value

"""BKD.020.016 - Diagnosticos de Clockify
Equivale a diagnosticoClockify(), diagnosticoClockifyCompleto(),
_obtenerMiembrosProyectoClockify(), _obtenerUsuariosWorkspaceClockify()
y _filtrarUsuariosPorRecursos(). Consultan las entradas por usuario de la
API estandar, sin cache, solo para revisar la conexion.
"""

JsonObject = dict[str, Any]

SETUP_ERROR = "Configura tu API key y workspace de Clockify primero."
USERS_PAGE_SIZE = 200
USERS_MAX_PAGES = 100
PROFILE_BATCH_SIZE = 4
PROFILE_BATCH_PAUSE_SECONDS = 1.2
USER_PAUSE_SECONDS = 0.1
SAMPLE_PAGE_SIZE = 5
FULL_PAGE_SIZE = 200
SAMPLE_ENTRIES = 3
SUCCESS_LIMIT = 300
ERROR_TEXT_LIMIT = 300
PROFILE_ERROR_LIMIT = 200
SAMPLE_ERROR_LIMIT = 500
NAME_KEYS = ["Nombre del recurso", "Nombre_del_recurso", "Recurso", "Nombre"]


@dataclass(slots=True)
class DiagnosticContext:
    """Cargador de Clockify, filas de Recursos y pausa."""

    loader: ClockifyTimeEntryLoader
    resource_rows: Callable[[], Sequence[Mapping[str, Any]]]
    range_payload: Callable[[str, ProjectDateRange], JsonObject]
    sleep: Callable[[float], None] = time.sleep
    client: ClockifyClient | None = field(default=None)

    def http(self) -> ClockifyClient:
        """Cliente reutilizado durante el diagnostico."""
        if self.client is None:
            self.client = self.loader.create_client()

        return self.client

    def workspace_path(self) -> str:
        """Ruta /workspaces/<id>."""
        return f"/workspaces/{quote(self.loader.workspace_id)}"


def match_name(value: object) -> str:
    """Nombre sin acentos, en minusculas y con espacios simples."""
    text = unicodedata.normalize("NFD", str(value or ""))
    text = "".join(char for char in text if not unicodedata.combining(char))

    return " ".join(text.lower().split())


def workspace_users(context: DiagnosticContext) -> JsonObject:
    """Usuarios del workspace (_obtenerUsuariosWorkspaceClockify)."""
    users: list[JsonObject] = []
    seen: set[str] = set()

    for page in range(1, USERS_MAX_PAGES + 1):
        response = context.http().get(
            f"{context.workspace_path()}/users",
            {"page-size": USERS_PAGE_SIZE, "page": page, "status": "ALL"},
        )

        if response.status_code >= SUCCESS_LIMIT:
            return {
                "ok": False,
                "error": (
                    f"Clockify respondió {response.status_code} al listar "
                    "usuarios del workspace: "
                    f"{response.text[:ERROR_TEXT_LIMIT]}"
                ),
                "usuarios": [],
            }

        batch = response.json()

        for user in batch:
            if user.get("id") not in seen:
                seen.add(user.get("id"))
                users.append(
                    {
                        "id": user.get("id"),
                        "nombre": user.get("name"),
                        "email": user.get("email"),
                    },
                )

        if len(batch) < USERS_PAGE_SIZE:
            return {"ok": True, "usuarios": users}

    return {
        "ok": False,
        "error": (
            "El workspace superó 100 páginas de usuarios; no se usarán "
            "datos incompletos."
        ),
        "usuarios": [],
    }


def read_profile(
    context: DiagnosticContext,
    user_id: str,
) -> tuple[JsonObject, str | None, Any]:
    """Perfil de un miembro: (usuario, error, respuesta cruda)."""
    fallback = {"id": user_id, "nombre": f"Usuario {user_id}", "email": ""}

    try:
        response = context.http().get(
            f"{context.workspace_path()}/member-profile/{quote(user_id)}",
        )

        if response.status_code >= SUCCESS_LIMIT:
            error = (
                f"Código {response.status_code}: "
                f"{response.text[:PROFILE_ERROR_LIMIT]}"
            )
            return fallback, error, None

        profile = response.json()
    except (DashboardError, ValueError) as error:
        return fallback, str(error), None

    user = {
        "id": user_id,
        "nombre": profile.get("name")
        or profile.get("email")
        or f"Usuario {user_id}",
        "email": profile.get("email") or "",
    }

    return user, None, profile


def project_members(context: DiagnosticContext, project_id: str) -> JsonObject:
    """
    Miembros del proyecto de Clockify (_obtenerMiembrosProyectoClockify).

    Lee memberships del proyecto y resuelve el nombre de cada usuario con
    el listado del workspace o, si falta, con su perfil.
    """
    response = context.http().get(
        f"{context.workspace_path()}/projects/{quote(project_id)}",
    )

    if response.status_code >= SUCCESS_LIMIT:
        return {
            "ok": False,
            "error": (
                f"Clockify respondió {response.status_code} al leer el "
                f"proyecto: {response.text[:ERROR_TEXT_LIMIT]}"
            ),
            "usuarios": [],
        }

    memberships = response.json().get("memberships") or []

    if not memberships:
        return {"ok": True, "usuarios": []}

    user_ids = list(
        dict.fromkeys(
            item.get("userId") for item in memberships if item.get("userId")
        ),
    )
    listing = workspace_users(context)
    known = {user["id"]: user for user in listing["usuarios"]}
    pending = [user_id for user_id in user_ids if user_id not in known]
    first_error = None
    first_profile = None

    for start in range(0, len(pending), PROFILE_BATCH_SIZE):
        if start:
            context.sleep(PROFILE_BATCH_PAUSE_SECONDS)

        for user_id in pending[start : start + PROFILE_BATCH_SIZE]:
            user, error, profile = read_profile(context, user_id)
            known[user_id] = user
            first_error = first_error or error

            if first_profile is None:
                first_profile = profile

    return {
        "ok": True,
        "usuarios": [known[user_id] for user_id in user_ids],
        "errorResolucionNombre": first_error,
        "muestraRespuestaCrudaUsuario": first_profile,
    }


def assigned_names(
    project_id: str,
    rows: Sequence[Mapping[str, Any]],
) -> set[str]:
    """Nombres de Recursos asignados al ID o a su base."""
    project_key = match_name(project_id)
    base_key = match_name(extract_base_id(project_id))
    names = set()

    for row in rows:
        row_id = str(get_flexible_value(row, ["Proyecto"]) or "")
        row_key = match_name(row_id)
        row_base = match_name(extract_base_id(row_id))

        if {row_key, row_base} & {project_key, base_key}:
            name = match_name(get_flexible_value(row, NAME_KEYS))

            if name:
                names.add(name)

    return names


def filter_by_resources(
    context: DiagnosticContext,
    project_id: str,
    users: list[JsonObject],
) -> JsonObject:
    """
    Deja solo a la gente asignada en Recursos (_filtrarUsuariosPorRecursos).

    Si Recursos no tiene asignaciones o ningun nombre coincide, regresa a
    todos los miembros en modo emergencia.
    """
    try:
        names = assigned_names(project_id, context.resource_rows())
    except DashboardError:
        return {"usuarios": users, "modoEmergencia": True}

    if not names:
        return {"usuarios": users, "modoEmergencia": True}

    found = [user for user in users if match_name(user["nombre"]) in names]
    found_names = {match_name(user["nombre"]) for user in found}

    if names - found_names:
        listing = workspace_users(context)

        if listing["ok"]:
            found.extend(
                user
                for user in listing["usuarios"]
                if match_name(user["nombre"]) in names - found_names
            )

    if not found and users:
        return {"usuarios": users, "modoEmergencia": True}

    return {"usuarios": found, "modoEmergencia": False}


def user_entries(
    context: DiagnosticContext,
    user_id: str,
    project_id: str,
    date_range: ProjectDateRange,
    page_size: int,
) -> Any:
    """Entradas de un usuario en el proyecto y rango (respuesta cruda)."""
    return context.http().get(
        f"{context.workspace_path()}/user/{quote(user_id)}/time-entries",
        {
            "project": project_id,
            "start": utc_midnight_iso(date_range.start_date),
            "end": utc_midnight_iso(date_range.end_date),
            "page-size": page_size,
            "hydrated": "true",
        },
    )


def entry_hours(entry: Mapping[str, Any]) -> float:
    """Horas de un registro; 0 si la duracion no es valida."""
    interval = entry.get("timeInterval") or {}

    try:
        return parse_duration_hours(interval.get("duration"), "")
    except ClockifyRequestError:
        return 0.0


def unmatched_error(context: DiagnosticContext, project_id: str) -> str:
    """Mensaje con los proyectos disponibles cuando no hay match."""
    try:
        names = ", ".join(
            project.name for project in context.loader.list_clockify_projects()
        )
    except DashboardError as error:
        names = f"error al listarlos: {describe_error(error)}"

    return (
        f'No se encontró match para "{project_id}". Proyectos disponibles '
        f"en Clockify: {names}"
    )


def quick_diagnostic(
    context: DiagnosticContext, project_value: object
) -> JsonObject:
    """
    Primeras entradas crudas del primer usuario (diagnosticoClockify).

    Args:
        context: Cargador, Recursos y pausa.
        project_value: ID interno del proyecto.

    Returns:
        El mismo objeto que el original.
    """
    project_id = str(project_value or "")
    project = context.loader.find_clockify_project(project_id)

    if project is None:
        return {"ok": False, "error": unmatched_error(context, project_id)}

    project_info = {"id": project.project_id, "nombre": project.name}
    date_range = context.loader.resolve_range(project_id)
    range_info = context.range_payload(project_id, date_range)

    if date_range.start_date is None:
        return {
            "ok": False,
            "error": f'No se encontró fecha de Discovery para "{project_id}".',
            "rango": range_info,
        }

    users = project_members(context, project.project_id)
    members_error = None if users["ok"] else users["error"]
    source = "miembros del proyecto"

    if not users["ok"] or not users["usuarios"]:
        users = workspace_users(context)
        source = "usuarios del workspace (respaldo)"

    if not users["ok"]:
        return {
            "ok": False,
            "error": f"Error al listar usuarios ({source}): {users['error']}",
            "errorMiembrosProyecto": members_error,
            "proyectoClockify": project_info,
            "rango": range_info,
        }

    if not users["usuarios"]:
        return {
            "ok": False,
            "error": "El workspace no tiene usuarios.",
            "proyectoClockify": project_info,
            "rango": range_info,
        }

    test_user = users["usuarios"][0]
    response = user_entries(
        context,
        test_user["id"],
        project.project_id,
        date_range,
        SAMPLE_PAGE_SIZE,
    )

    if response.status_code >= SUCCESS_LIMIT:
        return {
            "ok": False,
            "error": (
                f"Clockify respondió {response.status_code} probando con "
                f'"{test_user["nombre"]}": '
                f"{response.text[:SAMPLE_ERROR_LIMIT]}"
            ),
            "proyectoClockify": project_info,
            "rango": range_info,
            "usuarioPrueba": test_user,
            "totalUsuariosEnWorkspace": len(users["usuarios"]),
        }

    entries = response.json()

    return {
        "ok": True,
        "proyectoClockify": project_info,
        "rango": range_info,
        "fuenteUsuarios": source,
        "usuarioPrueba": test_user,
        "totalUsuariosEnWorkspace": len(users["usuarios"]),
        "primerasEntradasCrudas": entries[:SAMPLE_ENTRIES],
        "cantidadEntradasDeEsteUsuario": len(entries),
    }


def user_detail(
    context: DiagnosticContext,
    user: JsonObject,
    project_id: str,
    date_range: ProjectDateRange,
) -> JsonObject:
    """Entradas y horas de un miembro en el rango."""
    response = user_entries(
        context,
        user["id"],
        project_id,
        date_range,
        FULL_PAGE_SIZE,
    )
    context.sleep(USER_PAUSE_SECONDS)

    if response.status_code >= SUCCESS_LIMIT:
        return {
            "usuario": user["nombre"],
            "error": f"Código {response.status_code}",
            "entradas": 0,
            "horas": 0,
        }

    entries = response.json()
    hours = sum(entry_hours(entry) for entry in entries)

    return {
        "usuario": user["nombre"],
        "entradas": len(entries),
        "horas": round_half_up(hours, 2),
    }


def full_diagnostic(
    context: DiagnosticContext, project_value: object
) -> JsonObject:
    """
    Horas de cada miembro asignado en Recursos (diagnosticoClockifyCompleto).

    Args:
        context: Cargador, Recursos y pausa.
        project_value: ID interno del proyecto.

    Returns:
        El mismo objeto que el original.
    """
    project_id = str(project_value or "")
    project = context.loader.find_clockify_project(project_id)

    if project is None:
        return {
            "ok": False,
            "error": f'No se encontró match para "{project_id}".',
        }

    date_range = context.loader.resolve_range(project_id)

    if date_range.start_date is None:
        return {"ok": False, "error": "Sin fecha de Discovery."}

    members = project_members(context, project.project_id)

    if not members["ok"]:
        return {"ok": False, "error": members["error"]}

    selection = filter_by_resources(context, project_id, members["usuarios"])
    details = [
        user_detail(context, user, project.project_id, date_range)
        for user in selection["usuarios"]
    ]

    return {
        "ok": True,
        "proyectoClockify": project.name,
        "rango": context.range_payload(project_id, date_range),
        "totalMiembros": len(selection["usuarios"]),
        "totalMiembrosEnClockify": len(members["usuarios"]),
        "modoEmergenciaSinFiltroRecursos": selection["modoEmergencia"],
        "errorResolucionNombre": members.get("errorResolucionNombre"),
        "muestraRespuestaCrudaUsuario": members.get(
            "muestraRespuestaCrudaUsuario",
        ),
        "detallePorUsuario": details,
        "totalHoras": round_half_up(
            sum(detail["horas"] for detail in details),
            2,
        ),
        "totalEntradas": sum(detail["entradas"] for detail in details),
    }
