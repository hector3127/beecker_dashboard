"""Configuracion y conexion de Azure DevOps desde el panel Daily."""

from collections.abc import Callable
from typing import Any

from apps.daily.exceptions import AzureHttpError
from apps.daily.services.azure_connection import ConnectionStore, DailyCache
from apps.daily.services.daily_azure_client import DailyAzureClient
from core.exceptions import DashboardError
from core.utils.text import strip_accents

"""BKD.070.008 - Configuracion de Azure del Daily
Equivale a guardarConfigAzureDevOps(), obtenerConfigAzureDevOps(),
desconectarAzureDevOps(), listarProyectosAzureDevOps(),
listarProyectosGuardadosAzureDevOps(), cambiarProyectoActivoAzureDevOps()
y probarConexionAzureDevOps(). La organizacion y el PAT son los del .env
(como la configuracion compartida del original); el panel solo cambia el
proyecto activo.
"""

JsonObject = dict[str, Any]

ClientFactory = Callable[[str, str], DailyAzureClient]

PAT_SUFFIX_LENGTH = 4
UNAUTHORIZED_STATUSES = frozenset({401, 203})
NOT_FOUND = 404
CACHE_SUFFIXES = ("", "_tobe_cr_base", "_tipo_Risk", "_tipo_Opportunity")
ENV_ONLY_MESSAGE = (
    "La organización y el token se configuran en el archivo .env "
    "(AZURE_DEVOPS_ORGANIZATION y AZURE_DEVOPS_PAT)."
)


def clear_project_cache(store: ConnectionStore, cache: DailyCache) -> None:
    """
    Borra la cache de work items del proyecto activo.

    Args:
        store: Configuracion de Azure.
        cache: Cache del panel.
    """
    prefix = store.load().cache_prefix

    for suffix in CACHE_SUFFIXES:
        cache.delete(f"{prefix}{suffix}")


def argument_text(value: object) -> str:
    """
    Convierte un argumento como String(x || '').trim().

    Args:
        value: Valor recibido.

    Returns:
        El texto sin espacios externos.
    """
    return str(value).strip() if value else ""


def save_azure_config(
    store: ConnectionStore,
    cache: DailyCache,
    config: tuple[object, object, object],
) -> JsonObject:
    """
    Guarda el proyecto activo (la organizacion y el PAT vienen del .env).

    Args:
        store: Configuracion de Azure.
        cache: Cache del panel.
        config: Organizacion, proyecto y PAT escritos en el modal.

    Returns:
        {"ok": True} o {"ok": False, "error"}.
    """
    organization, project, token = (argument_text(value) for value in config)

    if not organization:
        return {"ok": False, "error": "Falta el nombre de la organización."}

    if not project:
        return {
            "ok": False,
            "error": "Falta el nombre del proyecto en Azure DevOps.",
        }

    if not token and not store.personal_access_token:
        return {"ok": False, "error": "Falta el Personal Access Token."}

    if organization != store.organization or (
        token and token != store.personal_access_token
    ):
        return {"ok": False, "error": ENV_ONLY_MESSAGE}

    store.set_active_project(project)
    clear_project_cache(store, cache)

    return {"ok": True}


def read_azure_config(store: ConnectionStore) -> JsonObject:
    """
    Configuracion actual sin exponer el PAT (solo sus ultimos 4).

    Args:
        store: Configuracion de Azure.

    Returns:
        Organizacion, proyecto y si hay PAT.
    """
    token = store.personal_access_token

    return {
        "ok": True,
        "global": bool(token),
        "organizacion": store.organization,
        "proyecto": store.active_project(),
        "patConfigurado": bool(token),
        "patSufijo": token[-PAT_SUFFIX_LENGTH:] if token else "",
    }


def disconnect_azure(store: ConnectionStore, cache: DailyCache) -> JsonObject:
    """
    Vuelve al proyecto del .env y borra la cache.

    En el original, con configuracion compartida, desconectar no quitaba
    el PAT comun; aqui tampoco se puede quitar desde el panel.

    Args:
        store: Configuracion de Azure.
        cache: Cache del panel.

    Returns:
        {"ok": True}.
    """
    clear_project_cache(store, cache)
    store.clear_active_project()

    return {"ok": True}


def project_sort_key(name: str) -> tuple[str, str, str]:
    """
    Orden como localeCompare: letra base, luego acentos, luego minusculas.

    Args:
        name: Nombre del proyecto.

    Returns:
        La llave de orden.
    """
    return strip_accents(name).lower(), name.lower(), name.swapcase()


def list_azure_projects(
    organization_value: object,
    token_value: object,
    store: ConnectionStore,
    build_client: ClientFactory = DailyAzureClient,
) -> JsonObject:
    """
    Lista los Team Projects visibles con el PAT.

    Args:
        organization_value: Organizacion escrita en el modal.
        token_value: PAT escrito; vacio usa el del .env.
        store: Configuracion de Azure.
        build_client: Crea el cliente (organizacion, PAT).

    Returns:
        {"ok", "proyectos", "mensaje"?} o {"ok": False, "error"}.
    """
    organization = argument_text(organization_value)
    token = argument_text(token_value) or store.personal_access_token

    if not organization:
        return {
            "ok": False,
            "error": "Falta el nombre de la organización.",
            "proyectos": [],
        }

    if not token:
        return {
            "ok": False,
            "error": "Falta el Personal Access Token.",
            "proyectos": [],
        }

    try:
        raw_projects = build_client(organization, token).list_projects()
    except AzureHttpError as error:
        return {
            "ok": False,
            "error": projects_error(error, organization),
            "proyectos": [],
        }
    except DashboardError as error:
        return {"ok": False, "error": error.detail, "proyectos": []}

    projects: list[JsonObject] = sorted(
        (
            {"id": project.get("id"), "nombre": str(project.get("name") or "")}
            for project in raw_projects
        ),
        key=lambda project: project_sort_key(str(project["nombre"])),
    )

    if not projects:
        return {
            "ok": True,
            "proyectos": [],
            "mensaje": "Tu token no tiene acceso a ningún proyecto en "
            f'"{organization}".',
        }

    return {"ok": True, "proyectos": projects}


def projects_error(error: AzureHttpError, organization: str) -> str:
    """
    Mensaje del original para listar proyectos.

    Args:
        error: Respuesta de Azure.
        organization: Organizacion consultada.

    Returns:
        El mensaje.
    """
    if error.status_code in UNAUTHORIZED_STATUSES:
        return (
            "Token inválido o expirado (401). Revisa tu Personal Access Token."
        )

    if error.status_code == NOT_FOUND:
        return (
            f'No se encontró la organización "{organization}" (404). '
            "Revisa el nombre."
        )

    return f"Azure DevOps respondió con código {error.status_code}."


def list_saved_projects(
    store: ConnectionStore,
    build_client: ClientFactory = DailyAzureClient,
) -> JsonObject:
    """
    Lista los proyectos con la organizacion y el PAT del .env.

    Args:
        store: Configuracion de Azure.
        build_client: Crea el cliente (organizacion, PAT).

    Returns:
        La lista con proyectoActivo y sinPAT.
    """
    if not store.organization or not store.personal_access_token:
        return {"ok": True, "proyectos": [], "sinPAT": True}

    result = list_azure_projects(store.organization, "", store, build_client)
    result["proyectoActivo"] = store.active_project()
    result["sinPAT"] = False

    return result


def change_active_project(
    store: ConnectionStore,
    cache: DailyCache,
    new_project: object,
) -> JsonObject:
    """
    Cambia solo el proyecto activo.

    Args:
        store: Configuracion de Azure.
        cache: Cache del panel.
        new_project: Nombre del Team Project.

    Returns:
        {"ok", "proyecto"} o {"ok": False, "error"}.
    """
    project = argument_text(new_project)

    if not project:
        return {"ok": False, "error": "Elige un proyecto."}

    if not store.personal_access_token:
        return {
            "ok": False,
            "error": "Primero conecta tu cuenta de Azure DevOps.",
        }

    store.set_active_project(project)
    clear_project_cache(store, cache)

    return {"ok": True, "proyecto": project}


def test_azure_connection(
    store: ConnectionStore,
    build_client: ClientFactory = DailyAzureClient,
) -> JsonObject:
    """
    Prueba la conexion con el proyecto activo.

    Args:
        store: Configuracion de Azure.
        build_client: Crea el cliente (organizacion, PAT).

    Returns:
        {"ok", "mensaje"} o {"ok": False, "error"}.
    """
    connection = store.load()

    if not connection.is_complete:
        return {
            "ok": False,
            "error": "Falta configurar organización, proyecto o token.",
        }

    client = build_client(
        connection.organization,
        connection.personal_access_token,
    )

    try:
        project = client.get_project(connection.project)
    except AzureHttpError as error:
        return {"ok": False, "error": connection_error(error, connection)}
    except DashboardError as error:
        return {"ok": False, "error": f"No se pudo conectar: {error.detail}"}

    name = project.get("name") or connection.project

    return {"ok": True, "mensaje": f'Conectado correctamente a "{name}".'}


def connection_error(error: AzureHttpError, connection: Any) -> str:
    """
    Mensaje del original para probar la conexion.

    Args:
        error: Respuesta de Azure.
        connection: Conexion probada.

    Returns:
        El mensaje.
    """
    if error.status_code in UNAUTHORIZED_STATUSES:
        return (
            "Token inválido o expirado (401). Genera un nuevo Personal "
            "Access Token en Azure DevOps."
        )

    if error.status_code == NOT_FOUND:
        return (
            f'No se encontró el proyecto "{connection.project}" en la '
            f'organización "{connection.organization}" (404). Revisa los '
            "nombres."
        )

    return f"Azure DevOps respondió con código {error.status_code}."
