"""Panel Azure del proyecto en la vista IXS (work items, To Be/CR y RAID)."""

import math
import re
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from apps.azure_devops.services.azure_client import encode_url_part
from apps.daily.constants import AZURE_BASE_URL, UNASSIGNED
from apps.daily.exceptions import AzureHttpError
from apps.daily.services.azure_connection import DailyCache
from apps.daily.services.daily_azure_client import DailyAzureClient
from apps.daily.services.work_items import parse_azure_date
from core.exceptions import DashboardError
from core.utils.dates import LOCAL_TIMEZONE
from core.utils.numbers import round_half_up_int, to_number
from core.utils.text import strip_accents

"""BKD.070.012 - Panel Azure IXS
Equivale a obtenerPanelAzureProyectoIXS(): lee todos los work items del
Team Project del proyecto (hasta 750), filtra los del proyecto y su
nomenclatura (S#, CR#, QA#) y les agrega el avance de WorkItems_Avance.
Si Azure falla temporalmente muestra la ultima consulta completa (6 h).
"""

JsonObject = dict[str, Any]

MAX_PANEL_ITEMS = 750
PANEL_BATCH_SIZE = 150
PANEL_CACHE_SECONDS = 300
LAST_OK_CACHE_SECONDS = 21600
STALE_DAYS = 7
DAY_MS = 86_400_000
WIQL_ERROR_CHARS = 250
BATCH_ERROR_CHARS = 160
CLOSED_STATES = frozenset(
    {
        "NOT APPLICABLE",
        "CANCELLED",
        "CLOSED",
        "REJECTED",
        "COMPLETED",
        "INACTIVE",
    },
)
DETAIL_TYPES = frozenset({"TO BE", "CHANGE REQUEST"})
ITERATION_SUFFIX = re.compile(r"(?:S\d+|CR\d*|QA\d*)", re.IGNORECASE | re.ASCII)
TRANSIENT_ERROR = re.compile(
    r"(?:HTTP\s*)(?:408|429|500|502|503|504)\b|direcci[oó]n no disponible|"
    r"address unavailable|temporar(?:ily|y)|temporal(?:mente)?|timed?\s*out|"
    r"tiempo de espera|timeout|service unavailable|servicio no disponible|"
    r"connection reset|connection refused|failure getting resource|"
    r"failed to fetch|network error|dns|socket|too many requests|"
    r"rate limit|resource has been exhausted|exception:.*(?:connect|fetch)",
    re.IGNORECASE,
)
LIMIT_NOTICE = (
    "La consulta superó el límite de 750 Work Items. Los totales mostrados "
    "son parciales; reduce el alcance antes de usarlos para reportes."
)


class PanelError(DashboardError):
    """Error del panel con el mensaje del original."""

    code = "ERR_IXS_PANEL"
    expose_detail = True


@dataclass(slots=True)
class IxsAzure:
    """Configuracion y dependencias del panel IXS."""

    organization: str
    personal_access_token: str
    active_project: str
    resolve_project: Callable[[str], str]
    build_client: Callable[[], DailyAzureClient]
    cache: DailyCache
    load_progress: Callable[[], dict[str, JsonObject]]


def normalize_upper(value: object) -> str:
    """
    Normaliza como el original: sin acentos, mayusculas y sin espacios.

    Args:
        value: Texto.

    Returns:
        El texto normalizado.
    """
    return strip_accents(str(value or "")).upper().strip()


def is_transient(error: Exception) -> bool:
    """
    Indica si el error es temporal, como _ixsAzureErrorTemporalV96_().

    Args:
        error: Error ocurrido.

    Returns:
        True si conviene usar la ultima consulta completa.
    """
    message = error.detail if isinstance(error, DashboardError) else str(error)

    return bool(TRANSIENT_ERROR.search(message))


def cache_text(value: str) -> str:
    """
    Llave de cache con solo letras, numeros, guion y guion bajo.

    Args:
        value: Texto de la llave.

    Returns:
        La llave.
    """
    return re.sub(r"[^A-Z0-9_-]", "_", normalize_upper(value))


def copy_notice(item: Mapping[str, Any]) -> str:
    """
    Aviso de copia temporal, como _ixsAzureTextoCopiaV96_().

    Args:
        item: Resultado guardado con obtenidoEn (ms).

    Returns:
        El aviso con la fecha de la copia.
    """
    stamp = item.get("obtenidoEn")
    formatted = (
        datetime.fromtimestamp(stamp / 1000, UTC)
        .astimezone(LOCAL_TIMEZONE)
        .strftime("%d/%m/%Y %H:%M")
        if isinstance(stamp, int | float)
        else "fecha no disponible"
    )

    return (
        "⚠ Azure respondió con un fallo temporal. Se muestra la última "
        f"consulta completa ({formatted}). Pulsa Sincronizar más tarde para "
        "actualizarla."
    )


def resolve_panel_project(azure: IxsAzure, project_id: str) -> str:
    """
    Team Project del ID interno; si no, el proyecto activo con la misma base.

    Args:
        azure: Configuracion del panel.
        project_id: ID interno.

    Returns:
        El Team Project, o cadena vacia.
    """
    resolved = azure.resolve_project(project_id)

    if resolved:
        return resolved

    configured = azure.active_project
    base_id = project_id.split("_")[0]

    if normalize_upper(configured) == normalize_upper(project_id) or (
        normalize_upper(configured.split("_")[0]) == normalize_upper(base_id)
    ):
        return configured

    return ""


def load_panel(
    azure: IxsAzure,
    project_value: object,
    force_refresh: object,
    now_ms: int,
) -> JsonObject:
    """
    Arma el panel Azure de un proyecto (obtenerPanelAzureProyectoIXS).

    Args:
        azure: Configuracion del panel.
        project_value: ID interno del proyecto.
        force_refresh: Ignora la cache de 5 minutos.
        now_ms: Milisegundos actuales (Date.now()).

    Returns:
        {"ok", "proyectoAzure", "allItems", "items", "stale", "aviso"} o
        {"ok": False, "error"}.
    """
    project_id = str(project_value).strip() if project_value else ""

    if not project_id:
        return {"ok": False, "error": "Selecciona un proyecto."}

    if not azure.organization or not azure.personal_access_token:
        return {
            "ok": False,
            "error": "Conecta Azure DevOps en Configuración para consultar "
            "este proyecto.",
        }

    try:
        azure_project = resolve_panel_project(azure, project_id)

        if not azure_project:
            return {
                "ok": False,
                "error": "No se encontró el Team Project de Azure "
                f"correspondiente a {project_id}. Revisa su nombre y tus "
                "permisos.",
            }

        raw, temporary_notice = load_raw_items(
            azure,
            (project_id, azure_project),
            force_refresh,
            now_ms,
        )
    except DashboardError as error:
        return {"ok": False, "error": error.detail}

    progress = load_progress_safely(azure)
    all_items = [
        merge_progress(item, progress.get(str(item["id"])), now_ms)
        for item in raw["workItems"]
    ]
    stale = [
        item
        for item in all_items
        if normalize_upper(item["estado"]) not in CLOSED_STATES
        and item["diasSinActualizar"] is not None
        and item["diasSinActualizar"] > STALE_DAYS
    ]
    stale.sort(key=lambda item: -item["diasSinActualizar"])
    notices = [
        temporary_notice,
        LIMIT_NOTICE if raw.get("limitReached") else "",
    ]

    return {
        "ok": True,
        "proyectoAzure": azure_project,
        "allItems": all_items,
        "items": [
            item
            for item in all_items
            if normalize_upper(item["tipo"]) in DETAIL_TYPES
        ],
        "stale": stale,
        "aviso": " ".join(notice for notice in notices if notice),
    }


def load_progress_safely(azure: IxsAzure) -> dict[str, JsonObject]:
    """Lee WorkItems_Avance; si falla, el panel sigue sin avance."""
    try:
        return azure.load_progress()
    except DashboardError:
        return {}


def load_raw_items(
    azure: IxsAzure,
    projects: tuple[str, str],
    force_refresh: object,
    now_ms: int,
) -> tuple[JsonObject, str]:
    """
    Lee los work items del Team Project (cache de 5 min y copia de 6 h).

    Args:
        azure: Configuracion del panel.
        projects: ID interno y Team Project.
        force_refresh: Ignora la cache de 5 minutos.
        now_ms: Milisegundos actuales.

    Returns:
        Los work items y el aviso de copia temporal (si aplica).

    Raises:
        PanelError: Cuando Azure falla sin copia disponible.
    """
    project_id, azure_project = projects
    key = "ixs_panel_azure_v96_" + cache_text(
        f"{azure.organization}_{azure_project}_{project_id}",
    )
    last_ok_key = f"{key}_lastok"

    if not force_refresh:
        cached = azure.cache.get(key)

        if isinstance(cached, dict):
            return cached, ""

    try:
        raw = fetch_raw_items(azure, project_id, azure_project)
    except DashboardError as error:
        if not is_transient(error):
            raise

        last_ok = azure.cache.get(last_ok_key)

        if isinstance(last_ok, dict) and isinstance(
            last_ok.get("workItems"), list
        ):
            return last_ok, copy_notice(last_ok)

        raise PanelError(
            "Azure DevOps no respondió después de los reintentos. No se "
            f"mostrarán 0 ni datos parciales. {error.detail}",
        ) from error

    raw["obtenidoEn"] = now_ms
    azure.cache.set(key, raw, PANEL_CACHE_SECONDS)
    azure.cache.set(last_ok_key, raw, LAST_OK_CACHE_SECONDS)

    return raw, ""


def fetch_raw_items(
    azure: IxsAzure,
    project_id: str,
    azure_project: str,
) -> JsonObject:
    """
    Consulta la WIQL del Team Project y los work items en lotes de 150.

    Args:
        azure: Configuracion del panel.
        project_id: ID interno.
        azure_project: Team Project.

    Returns:
        {"totalTeamProject", "limitReached", "workItems"}.

    Raises:
        PanelError: Con el mensaje de Azure del original.
    """
    client = azure.build_client()
    base_url = client.project_url(azure_project)
    escaped_project = azure_project.replace("'", "''")
    query = (
        "SELECT [System.Id] FROM WorkItems WHERE [System.TeamProject] = "
        f"'{escaped_project}' ORDER BY [System.ChangedDate] DESC"
    )

    try:
        payload = client.send(
            "POST",
            f"{base_url}wiql",
            retry=True,
            params={"api-version": "7.1"},
            json={"query": query},
        )
    except AzureHttpError as error:
        raise PanelError(
            f"Azure WIQL ({azure_project}): HTTP {error.status_code}. "
            f"{error.body[:WIQL_ERROR_CHARS]}",
        ) from error

    all_ids = [item["id"] for item in payload.get("workItems") or []]
    ids = all_ids[:MAX_PANEL_ITEMS]
    work_items: list[JsonObject] = []

    for batch_number, start in enumerate(
        range(0, len(ids), PANEL_BATCH_SIZE),
        start=1,
    ):
        end = start + PANEL_BATCH_SIZE
        batch_ids = ids[start:end]

        try:
            batch = client.send(
                "GET",
                f"{base_url}workitems",
                retry=True,
                params={
                    "ids": ",".join(str(item_id) for item_id in batch_ids),
                    "$expand": "fields",
                    "api-version": "7.1",
                },
            )
        except AzureHttpError as error:
            raise PanelError(
                f"Azure Work Items: HTTP {error.status_code} al consultar "
                f"lote {batch_number}. {error.body[:BATCH_ERROR_CHARS]}",
            ) from error

        work_items.extend(batch.get("value") or [])

    work_items = filter_project_items(work_items, project_id, azure_project)

    return {
        "totalTeamProject": len(all_ids),
        "limitReached": len(all_ids) > len(ids),
        "workItems": [
            build_raw_item(
                work_item,
                azure.organization,
                azure_project,
            )
            for work_item in work_items
        ],
    }


def filter_project_items(
    work_items: Sequence[JsonObject],
    project_id: str,
    azure_project: str,
) -> list[JsonObject]:
    """
    Deja solo los work items del proyecto y de su nomenclatura.

    Args:
        work_items: Work items del Team Project.
        project_id: ID interno.
        azure_project: Team Project.

    Returns:
        Los work items del proyecto.
    """
    base_id = project_id.split("_")[0]
    items = list(work_items)

    if normalize_upper(azure_project.split("_")[0]) != normalize_upper(base_id):
        # Team Project general: solo los que mencionan el ID base.
        token = normalize_upper(base_id)
        items = [
            item
            for item in items
            if any(
                token in normalize_upper((item.get("fields") or {}).get(name))
                for name in (
                    "System.Title",
                    "System.AreaPath",
                    "System.IterationPath",
                )
            )
        ]

    suffix = project_id.split("_", 1)[1].strip() if "_" in project_id else ""

    if ITERATION_SUFFIX.fullmatch(suffix):
        wanted = suffix.upper()
        items = [
            item
            for item in items
            if any(
                segment == wanted or segment.endswith(f"_{wanted}")
                for segment in normalize_upper(
                    (item.get("fields") or {}).get("System.IterationPath"),
                ).split("\\")
            )
        ]

    return items


def build_raw_item(
    work_item: Mapping[str, Any],
    organization: str,
    azure_project: str,
) -> JsonObject:
    """
    Datos basicos del work item que se guardan en cache.

    Args:
        work_item: Work item de Azure.
        organization: Organizacion.
        azure_project: Team Project.

    Returns:
        El work item resumido.
    """
    fields = work_item.get("fields") or {}
    person = fields.get("System.AssignedTo")

    return {
        "id": work_item.get("id"),
        "titulo": fields.get("System.Title") or "",
        "tipo": fields.get("System.WorkItemType") or "",
        "estado": fields.get("System.State") or "",
        "asignadoA": person_name(person, UNASSIGNED),
        "iterationPath": fields.get("System.IterationPath") or "",
        "ultimoSeguimiento": fields.get("System.ChangedDate") or "",
        "url": f"{AZURE_BASE_URL}/{encode_url_part(organization)}/"
        f"{encode_url_part(azure_project)}/_workitems/edit/{work_item.get('id')}",
    }


def person_name(person: object, default: str) -> str:
    """
    Nombre visible de una persona de Azure.

    Args:
        person: Valor de System.AssignedTo.
        default: Texto cuando no hay persona.

    Returns:
        displayName o uniqueName; cadena vacia si no trae ninguno.
    """
    if not person:
        return default

    if isinstance(person, dict):
        return str(person.get("displayName") or person.get("uniqueName") or "")

    # Un texto no tiene displayName ni uniqueName: el original deja "".
    return ""


def merge_progress(
    item: Mapping[str, Any],
    saved: Mapping[str, Any] | None,
    now_ms: int,
) -> JsonObject:
    """
    Agrega dias sin actualizar y el avance guardado en Sheets.

    Args:
        item: Work item resumido.
        saved: Avance de WorkItems_Avance.
        now_ms: Milisegundos actuales.

    Returns:
        El work item con su avance.
    """
    progress = saved or {}
    changed = parse_azure_date(item.get("ultimoSeguimiento"))
    days = (
        max(0, math.floor((now_ms - changed.timestamp() * 1000) / DAY_MS))
        if changed is not None
        else None
    )
    dev_pct = to_number(progress.get("devPct") or 0)
    qa_ready = bool(progress.get("qaListo"))

    return {
        **item,
        "diasSinActualizar": days,
        "devConstruidoPct": dev_pct,
        "qaListo": qa_ready,
        "fechaLimiteDev": progress.get("fechaLimiteDev") or "",
        "demo": progress.get("demo") or "",
        "avanceTotal": round_half_up_int(
            dev_pct * 0.8 + (20 if qa_ready else 0)
        ),
    }
