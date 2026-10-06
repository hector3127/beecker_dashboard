"""Work items del panel Daily: pendientes, tipos, To Be y sin cambios."""

import json
import math
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

from apps.azure_devops.services.azure_client import encode_url_part
from apps.daily.constants import (
    AZURE_BASE_URL,
    CLOSED_STATES_WIQL,
    DEFAULT_STALE_DAYS,
    ERROR_BODY_CHARS,
    MAX_WORK_ITEMS,
    PENDING_ITEM_FIELDS,
    TYPED_ITEM_FIELDS,
    UNASSIGNED,
    WORK_ITEMS_CACHE_SECONDS,
)
from apps.daily.exceptions import AzureHttpError
from apps.daily.services.azure_connection import AzureConnection, DailyCache
from apps.daily.services.daily_azure_client import DailyAzureClient
from core.exceptions import DashboardError
from core.utils.dates import LOCAL_TIMEZONE, to_utc_iso
from core.utils.numbers import to_number

"""BKD.070.006 - Work items del Daily
Equivale a obtenerWorkItemsPendientes(), obtenerWorkItemsPorTipo(),
obtenerWorkItemsToBeYCR(), obtenerWorkItemsSinSeguimiento() e
inspeccionarCamposWorkItem(). Las respuestas se guardan 5 minutos por
proyecto y forzarRefresh las vuelve a consultar.
"""

JsonObject = dict[str, Any]

UNAUTHORIZED = 401
DAY_SECONDS = 86400
EXPIRED_PAT_RECONNECT_MESSAGE = (
    "Token inválido o expirado. Vuelve a conectar tu cuenta de Azure DevOps."
)
EXPIRED_PAT_MESSAGE = "Token inválido o expirado."
CONNECT_FIRST = "Conecta tu cuenta de Azure DevOps primero."


@dataclass(slots=True)
class DailyAzure:
    """Conexion, cliente y cache del panel Daily."""

    connection: AzureConnection
    build_client: Callable[[], DailyAzureClient]
    cache: DailyCache


@dataclass(frozen=True, slots=True)
class ErrorTexts:
    """Mensajes del original para cada consulta."""

    wiql_unauthorized: str | None
    wiql_failed: Callable[[AzureHttpError], str]
    detail_failed: Callable[[AzureHttpError], str]


DAILY_TEXTS = ErrorTexts(
    wiql_unauthorized=EXPIRED_PAT_RECONNECT_MESSAGE,
    wiql_failed=lambda error: (
        f"Azure DevOps (WIQL) respondió {error.status_code}: "
        f"{error.body[:ERROR_BODY_CHARS]}"
    ),
    detail_failed=lambda error: (
        f"Azure DevOps (detalle) respondió {error.status_code}."
    ),
)
TABLE_TEXTS = ErrorTexts(
    wiql_unauthorized=EXPIRED_PAT_MESSAGE,
    wiql_failed=lambda error: f"WIQL falló: {error.body[:ERROR_BODY_CHARS]}",
    detail_failed=lambda error: f"Detalle falló: {error.status_code}",
)


class QueryFailedError(DashboardError):
    """Consulta a Azure con el mensaje exacto del original."""

    code = "ERR_DAILY_QUERY"
    expose_detail = True


def empty_result(without_token: bool) -> JsonObject:
    """
    Respuesta sin datos.

    Args:
        without_token: True cuando falta configurar Azure.

    Returns:
        {"ok": True, "items": [], "sinPAT", "error": None}.
    """
    return {"ok": True, "items": [], "sinPAT": without_token, "error": None}


def failed_result(message: str) -> JsonObject:
    """
    Respuesta con error.

    Args:
        message: Mensaje para el frontend.

    Returns:
        {"ok": False, "items": [], "sinPAT": False, "error"}.
    """
    return {"ok": False, "items": [], "sinPAT": False, "error": message}


def wiql_project_filter(project: str) -> str:
    """
    Condicion WIQL del Team Project con comillas escapadas.

    Args:
        project: Nombre del proyecto.

    Returns:
        La condicion.
    """
    escaped_project = project.replace("'", "''")

    return f"[System.TeamProject] = '{escaped_project}'"


def query_work_items(
    azure: DailyAzure,
    query: str,
    fields: Sequence[str] | None,
    texts: ErrorTexts,
) -> list[JsonObject]:
    """
    Ejecuta la WIQL y lee hasta 200 work items.

    Args:
        azure: Conexion del panel.
        query: Consulta WIQL.
        fields: Campos; None para todos.
        texts: Mensajes de error del original.

    Returns:
        Los work items.

    Raises:
        QueryFailedError: Con el mensaje que mostraba el original.
    """
    client = azure.build_client()
    project = azure.connection.project

    try:
        ids = client.run_wiql(project, query)[:MAX_WORK_ITEMS]
    except AzureHttpError as error:
        unauthorized = (
            texts.wiql_unauthorized
            if error.status_code == UNAUTHORIZED
            else None
        )
        raise QueryFailedError(
            unauthorized or texts.wiql_failed(error),
        ) from error

    if not ids:
        return []

    try:
        return client.get_work_items(project, ids, fields)
    except AzureHttpError as error:
        raise QueryFailedError(texts.detail_failed(error)) from error


def work_item_url(connection: AzureConnection, work_item_id: object) -> str:
    """
    Enlace al work item (la organizacion va sin codificar, como el original).

    Args:
        connection: Conexion de Azure.
        work_item_id: ID del work item.

    Returns:
        La URL de edicion.
    """
    return (
        f"{AZURE_BASE_URL}/{connection.organization}/"
        f"{encode_url_part(connection.project)}/_workitems/edit/"
        f"{work_item_id}"
    )


def assigned_name(fields: Mapping[str, Any]) -> str:
    """
    Nombre del asignado o "Sin asignar".

    Args:
        fields: Campos del work item.

    Returns:
        El nombre visible.
    """
    assigned = fields.get("System.AssignedTo")

    if not assigned:
        return UNASSIGNED

    if isinstance(assigned, dict):
        return str(
            assigned.get("displayName") or assigned.get("uniqueName") or ""
        )

    return str(assigned)


def assigned_email(fields: Mapping[str, Any]) -> str:
    """
    Correo (uniqueName) del asignado.

    Args:
        fields: Campos del work item.

    Returns:
        El correo, o cadena vacia.
    """
    assigned = fields.get("System.AssignedTo")

    if isinstance(assigned, dict):
        return str(assigned.get("uniqueName") or "")

    return ""


def cached_items(
    azure: DailyAzure,
    cache_suffix: str,
    force_refresh: object,
    load: Callable[[], list[JsonObject]],
) -> tuple[list[JsonObject], bool]:
    """
    Lee los items de cache o los consulta y los guarda 5 minutos.

    Args:
        azure: Conexion del panel.
        cache_suffix: Variante de cache (tipo, tobe...).
        force_refresh: Ignora la cache cuando es verdadero.
        load: Consulta a Azure.

    Returns:
        Los items y si vinieron de cache.
    """
    cache_key = f"{azure.connection.cache_prefix}{cache_suffix}"

    if not force_refresh:
        cached = azure.cache.get(cache_key)

        if isinstance(cached, list):
            return cached, True

    items = load()
    azure.cache.set(cache_key, items, WORK_ITEMS_CACHE_SECONDS)

    return items, False


def run_listing(
    azure: DailyAzure,
    cache_suffix: str,
    force_refresh: object,
    load: Callable[[], list[JsonObject]],
) -> JsonObject:
    """
    Respuesta comun de las tarjetas con cache.

    Args:
        azure: Conexion del panel.
        cache_suffix: Variante de cache.
        force_refresh: Ignora la cache cuando es verdadero.
        load: Consulta a Azure.

    Returns:
        {"ok", "items", "sinPAT", "error"} y "deCache" si aplica.
    """
    if not azure.connection.is_complete:
        return empty_result(True)

    try:
        items, from_cache = cached_items(
            azure,
            cache_suffix,
            force_refresh,
            load,
        )
    except DashboardError as error:
        return failed_result(error.detail)

    result = empty_result(False)
    result["items"] = items

    if from_cache:
        result["deCache"] = True

    return result


def load_pending_work_items(
    azure: DailyAzure, force_refresh: object
) -> JsonObject:
    """
    Work items abiertos del proyecto activo (obtenerWorkItemsPendientes).

    Args:
        azure: Conexion del panel.
        force_refresh: Ignora la cache.

    Returns:
        La respuesta con los work items.
    """
    connection = azure.connection

    def load() -> list[JsonObject]:
        query = (
            "SELECT [System.Id] FROM WorkItems WHERE "
            f"{wiql_project_filter(connection.project)} AND [System.State] "
            f"NOT IN {CLOSED_STATES_WIQL} ORDER BY [System.ChangedDate] DESC"
        )
        work_items = query_work_items(
            azure,
            query,
            PENDING_ITEM_FIELDS,
            DAILY_TEXTS,
        )

        return [
            {
                "id": work_item.get("id"),
                "titulo": fields.get("System.Title") or "",
                "tipo": fields.get("System.WorkItemType") or "",
                "estado": fields.get("System.State") or "",
                "asignadoA": assigned_name(fields),
                "asignadoEmail": assigned_email(fields),
                "fechaCreacion": fields.get("System.CreatedDate") or None,
                "fechaCambio": fields.get("System.ChangedDate") or None,
                "fechaLimite": (
                    fields.get("Microsoft.VSTS.Scheduling.DueDate") or None
                ),
                "tags": fields.get("System.Tags") or "",
                "url": work_item_url(connection, work_item.get("id")),
            }
            for work_item in work_items
            for fields in (work_item.get("fields") or {},)
        ]

    return run_listing(azure, "", force_refresh, load)


def load_work_items_by_type(
    azure: DailyAzure,
    work_item_type: str,
    force_refresh: object,
) -> JsonObject:
    """
    Work items abiertos de un tipo (Risk, Opportunity).

    Args:
        azure: Conexion del panel.
        work_item_type: Tipo de work item.
        force_refresh: Ignora la cache.

    Returns:
        La respuesta con los work items.
    """
    connection = azure.connection

    def load() -> list[JsonObject]:
        escaped_type = work_item_type.replace("'", "''")
        query = (
            "SELECT [System.Id] FROM WorkItems WHERE "
            f"{wiql_project_filter(connection.project)} AND "
            f"[System.WorkItemType] = '{escaped_type}' AND [System.State] "
            f"NOT IN {CLOSED_STATES_WIQL} ORDER BY [System.ChangedDate] DESC"
        )
        work_items = query_work_items(
            azure,
            query,
            TYPED_ITEM_FIELDS,
            DAILY_TEXTS,
        )

        return [
            {
                "id": work_item.get("id"),
                "titulo": fields.get("System.Title") or "",
                "estado": fields.get("System.State") or "",
                "asignadoA": assigned_name(fields),
                "nivel": (
                    fields.get("Microsoft.VSTS.Common.Risk")
                    or fields.get("Microsoft.VSTS.Common.Severity")
                    or fields.get("Microsoft.VSTS.Common.Priority")
                    or ""
                ),
                "fechaCambio": fields.get("System.ChangedDate") or None,
                "url": work_item_url(connection, work_item.get("id")),
            }
            for work_item in work_items
            for fields in (work_item.get("fields") or {},)
        ]

    return run_listing(azure, f"_tipo_{work_item_type}", force_refresh, load)


def load_tobe_work_items(
    azure: DailyAzure,
    force_refresh: object,
    load_progress: Callable[[], dict[str, JsonObject]],
) -> JsonObject:
    """
    Work items To Be y Change Request con su avance guardado en Sheets.

    Args:
        azure: Conexion del panel.
        force_refresh: Ignora la cache de Azure.
        load_progress: Lee WorkItems_Avance (ID -> avance).

    Returns:
        La respuesta con los work items y su avance.
    """
    connection = azure.connection

    def load() -> list[JsonObject]:
        query = (
            "SELECT [System.Id] FROM WorkItems WHERE "
            f"{wiql_project_filter(connection.project)} AND "
            "[System.WorkItemType] IN ('To Be','Change Request') "
            "ORDER BY [System.ChangedDate] DESC"
        )
        work_items = query_work_items(azure, query, None, TABLE_TEXTS)

        return [
            {
                "id": work_item.get("id"),
                "titulo": fields.get("System.Title") or "",
                "asignadoA": assigned_name(fields),
                "estado": fields.get("System.State") or "",
                "url": work_item_url(connection, work_item.get("id")),
            }
            for work_item in work_items
            for fields in (work_item.get("fields") or {},)
        ]

    result = run_listing(azure, "_tobe_cr_base", force_refresh, load)

    if not result["ok"] or result["sinPAT"]:
        return result

    progress_by_id = load_progress()
    result["items"] = [
        add_progress(item, progress_by_id.get(str(item["id"])))
        for item in result["items"]
    ]
    result.pop("deCache", None)

    return result


def add_progress(item: JsonObject, progress: JsonObject | None) -> JsonObject:
    """
    Agrega el avance guardado y el % de avance total.

    Args:
        item: Work item base.
        progress: Avance de WorkItems_Avance, si existe.

    Returns:
        El work item con su avance.
    """
    saved = progress or {
        "devPct": 0,
        "qaListo": False,
        "ttProdListo": False,
        "fechaLimiteDev": None,
        "demo": "",
    }
    total = math.floor(
        saved["devPct"] * 0.8 + (20 if saved["qaListo"] else 0) + 0.5
    )

    return {
        **item,
        "devConstruidoPct": saved["devPct"],
        "qaListo": saved["qaListo"],
        "ttProdListo": saved["ttProdListo"],
        "fechaLimiteDev": saved["fechaLimiteDev"],
        "demo": saved["demo"],
        "avanceTotal": total,
    }


def load_stale_work_items(
    azure: DailyAzure,
    threshold_days: object,
    now: datetime,
) -> JsonObject:
    """
    Work items abiertos sin cambios en mas de N dias (7 por omision).

    Args:
        azure: Conexion del panel.
        threshold_days: Dias sin actualizar.
        now: Momento actual con zona horaria.

    Returns:
        La respuesta ordenada de mas a menos dias sin actualizar.
    """
    connection = azure.connection

    if not connection.is_complete:
        return empty_result(True)

    days = (
        math.trunc(
            to_number(
                threshold_days
                if isinstance(threshold_days, str | int | float)
                else None
            )
        )
        or DEFAULT_STALE_DAYS
    )
    limit_day = (
        now.astimezone(LOCAL_TIMEZONE) - timedelta(days=days)
    ).astimezone(UTC)
    query = (
        "SELECT [System.Id] FROM WorkItems WHERE "
        f"{wiql_project_filter(connection.project)} AND "
        "[System.WorkItemType] IN ('To Be','Change Request','Risk',"
        "'Opportunity') AND [System.State] NOT IN "
        f"{CLOSED_STATES_WIQL} AND [System.ChangedDate] < "
        f"'{limit_day.strftime('%Y-%m-%d')}' ORDER BY [System.ChangedDate] ASC"
    )

    try:
        work_items = query_work_items(azure, query, None, TABLE_TEXTS)
    except DashboardError as error:
        return failed_result(error.detail)

    items: list[JsonObject] = []

    for work_item in work_items:
        fields = work_item.get("fields") or {}
        changed = parse_azure_date(fields.get("System.ChangedDate"))
        items.append(
            {
                "id": work_item.get("id"),
                "titulo": fields.get("System.Title") or "",
                "tipo": fields.get("System.WorkItemType") or "",
                "estado": fields.get("System.State") or "",
                "asignadoA": assigned_name(fields),
                "iterationPath": fields.get("System.IterationPath") or "",
                "ultimoSeguimiento": (
                    to_utc_iso(changed) if changed is not None else None
                ),
                "diasSinActualizar": (
                    math.floor((now - changed).total_seconds() / DAY_SECONDS)
                    if changed is not None
                    else None
                ),
                "url": work_item_url(connection, work_item.get("id")),
            },
        )

    items.sort(key=lambda item: -(item["diasSinActualizar"] or 0))
    result = empty_result(False)
    result["items"] = items

    return result


def read_threshold_days(threshold_days: object) -> int:
    """
    Dias de umbral como Number(dias) || 7.

    Args:
        threshold_days: Valor del frontend.

    Returns:
        Los dias (enteros).
    """
    if not isinstance(threshold_days, str | int | float):
        return DEFAULT_STALE_DAYS

    return math.trunc(to_number(threshold_days)) or DEFAULT_STALE_DAYS


def parse_azure_date(value: object) -> datetime | None:
    """
    Lee una fecha ISO de Azure.

    Args:
        value: Texto ISO (con Z).

    Returns:
        La fecha con zona horaria, o None.
    """
    if not isinstance(value, str) or not value:
        return None

    try:
        moment = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None

    return moment if moment.tzinfo is not None else moment.replace(tzinfo=UTC)


def inspect_work_item_fields(
    azure: DailyAzure, work_item_type: str
) -> JsonObject:
    """
    Muestra todos los campos del work item mas reciente de un tipo.

    Args:
        azure: Conexion del panel.
        work_item_type: Tipo de work item.

    Returns:
        {"ok", "workItemId", "tipo", "campos"} o {"ok": False, "error"}.
    """
    connection = azure.connection

    if not connection.is_complete:
        return {"ok": False, "error": CONNECT_FIRST}

    client = azure.build_client()
    escaped_type = work_item_type.replace("'", "''")
    query = (
        "SELECT [System.Id] FROM WorkItems WHERE "
        f"{wiql_project_filter(connection.project)} AND "
        f"[System.WorkItemType] = '{escaped_type}' "
        "ORDER BY [System.ChangedDate] DESC"
    )

    try:
        ids = client.run_wiql(connection.project, query)
    except AzureHttpError as error:
        return {
            "ok": False,
            "error": f"WIQL falló: {error.body[:ERROR_BODY_CHARS]}",
        }
    except DashboardError as error:
        return {"ok": False, "error": error.detail}

    if not ids:
        return {
            "ok": False,
            "error": "No se encontró ningún Work Item de tipo "
            f'"{work_item_type}" en este proyecto.',
        }

    try:
        work_item = client.get_work_item(connection.project, ids[0])
    except AzureHttpError as error:
        return {
            "ok": False,
            "error": f"Detalle falló: {error.body[:ERROR_BODY_CHARS]}",
        }
    except DashboardError as error:
        return {"ok": False, "error": error.detail}

    fields = work_item.get("fields") or {}

    return {
        "ok": True,
        "workItemId": ids[0],
        "tipo": work_item_type,
        "campos": [
            {"referenceName": name, "valor": js_json(fields[name])}
            for name in sorted(fields)
        ],
    }


def js_json(value: object) -> str:
    """
    Serializa como JSON.stringify (sin espacios y 5.0 como 5).

    Args:
        value: Valor a serializar.

    Returns:
        El texto JSON.
    """
    return json.dumps(
        normalize_numbers(value),
        separators=(",", ":"),
        ensure_ascii=False,
    )


def normalize_numbers(value: object) -> object:
    """
    Convierte flotantes enteros a enteros, como los escribe JavaScript.

    Args:
        value: Valor JSON.

    Returns:
        El valor con numeros normalizados.
    """
    if isinstance(value, float) and value.is_integer():
        return int(value)

    if isinstance(value, dict):
        return {key: normalize_numbers(item) for key, item in value.items()}

    if isinstance(value, list):
        return [normalize_numbers(item) for item in value]

    return value
