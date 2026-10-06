"""Vista de cuenta Beecker: proyectos, ROC, MPB y oportunidades."""

import hashlib
import math
import re
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import date
from typing import Any, Protocol

from apps.ejecutivo.constants import SHEET_MPB
from apps.ejecutivo.services.mpb_values import (
    normalize_mpb,
    parse_mpb_date,
    parse_mpb_hours,
    parse_mpb_number,
    read_cell,
)
from core.sheets import sheet_names
from core.sheets.protocols import SheetReader
from core.utils.cell_types import CellValue
from core.utils.js_values import js_null_text, js_or_text

"""BKD.040.010 - Vista de cuenta Beecker
Equivale a obtenerVistaCuentaBeecker(), obtenerOportunidadesCuentaBeecker()
y a la lectura de MPB de beeCuentaMPB_() en DailyPanelService.gs: junta
el historico, ROC, el estado de Proyectos, los proyectos AER/T&M de MPB
y las oportunidades abiertas del backlog para una cuenta.
"""

JsonObject = dict[str, Any]
Rows = list[list[CellValue]]

HEADER_SEARCH_ROWS = 12
HISTORY_START_COLUMN = 11
HISTORY_WIDTH = 36
ROC_SHEET = "ROC"
ROC_WIDTH = 14
MPB_MAX_COLUMNS = 64
MPB_BURN_INDEX = 63
OPPORTUNITY_HEADERS = (
    "account name",
    "opportunity name",
    "opportunity stage",
    "total hours",
)
OPPORTUNITY_MIN_COLUMNS = 6
OPPORTUNITY_PREVIEW_COLUMNS = 80
OPPORTUNITY_CACHE_KEY = "bee_oportunidades_hoja_v1"
OPPORTUNITY_CACHE_SECONDS = 21600
MPB_CACHE_SECONDS = 300

MPB_SERVICE = re.compile(r"^(aer|t\s*&\s*m|tym)$", re.IGNORECASE)
ID_PREFIX = re.compile(r"^(?:roc|raas|aer|ixb|saas|tym|t&m)\.")
ID_SUFFIX = re.compile(r"(?:_(?:s\d+|cr\d*))+$", re.ASCII)
FINISHED = re.compile(
    r"^(?:completed|completado|finalizad[oa]|finished)(?:\b|$)",
    re.ASCII,
)
SUSPENDED = re.compile(r"^(?:suspendid[oa]|suspended)(?:\b|$)", re.ASCII)
CANCELLED = re.compile(
    r"^(?:cancelado|cancelada|cancelled|canceled)(?:\b|$)",
    re.ASCII,
)
NOT_IN_DEVELOPMENT = re.compile(
    r"^(completed|finalizado|cancelled|cancelado|suspendido)$",
)
ACTIVE_ROC = re.compile(
    r"activo|produccion|producción|production|active",
    re.IGNORECASE,
)
CURRENT_STAGE = re.compile(
    r"discovery|development|deployment|desarrollo|implementacion",
    re.IGNORECASE,
)
BUILD_STAGE = re.compile(
    r"development|deployment|desarrollo|implementacion",
    re.IGNORECASE,
)
PROJECT_ID_HEADER = re.compile(
    r"^(project id|id proyecto|id_proyecto|proyecto id)$",
    re.IGNORECASE,
)
STATUS_HEADER = re.compile(r"^(status|estado|estado general|etapa|stage)$")
CLOSED_OPPORTUNITY = re.compile(r"closed", re.IGNORECASE)


class AccountCache(Protocol):
    """Cache con get y set (la de Django cumple)."""

    def get(self, key: str) -> Any:
        """Valor guardado o None."""
        ...

    def set(self, key: str, value: Any, timeout: int) -> None:
        """Guarda el valor por timeout segundos."""
        ...


@dataclass(frozen=True, slots=True)
class OpportunitySource:
    """Hoja del backlog con la fila de encabezados (base 1) y columnas."""

    sheet: str
    header_row: int
    columns: dict[str, int]


def js_round(value: float) -> int:
    """Math.round() de JavaScript (los medios suben)."""
    return math.floor(value + 0.5)


def account_matches(value: object, client: object) -> bool:
    """
    El nombre contiene la cuenta, como beeCuentaCoincide_().

    Args:
        value: Cliente de la fila.
        client: Cuenta seleccionada.

    Returns:
        True si ambos tienen texto y el nombre incluye la cuenta.
    """
    account = normalize_value(client)
    name = normalize_value(value)

    return bool(account) and bool(name) and account in name


def normalize_value(value: object) -> str:
    """beeCuentaNormalizar_() para cualquier valor."""
    if isinstance(value, str | int | float | bool) or value is None:
        return normalize_mpb(value if value is not None else "")

    return normalize_mpb(js_null_text(value))


def id_base(value: object) -> str:
    """
    ID base sin prefijo de servicio ni sufijos _S/_CR (beeCuentaIDBase_).

    Args:
        value: ID del proyecto o del bot.

    Returns:
        El ID base normalizado.
    """
    text = re.sub(r"\s+", "", normalize_value(value))
    text = ID_PREFIX.sub("", text, count=1)

    return ID_SUFFIX.sub("", text, count=1)


def is_finished(value: object) -> bool:
    """Estado completado o finalizado."""
    return bool(FINISHED.search(normalize_value(value)))


def is_terminal(value: object) -> bool:
    """Estado completado, suspendido o cancelado."""
    status = normalize_value(value)

    return is_finished(status) or bool(
        re.search(
            r"^(?:suspendid[oa]|suspended|cancelado|cancelada|cancelled|"
            r"canceled)(?:\b|$)",
            status,
            re.ASCII,
        ),
    )


def in_development(value: object) -> bool:
    """Etapa con texto que no es final (beeCuentaEtapaEnDesarrollo_)."""
    stage = normalize_value(value)

    return bool(stage) and not NOT_IN_DEVELOPMENT.search(stage)


def project_state(stage: object, has_roc: bool) -> str:
    """
    Estado visible del proyecto (beeCuentaEstadoProyecto_).

    Args:
        stage: Etapa o estatus.
        has_roc: Si el proyecto tiene un bot en ROC.

    Returns:
        Suspendido, Cancelado, Producción ROC, Completado, En desarrollo u
        Otro.
    """
    status = normalize_value(stage)

    if SUSPENDED.search(status):
        return "Suspendido"

    if CANCELLED.search(status):
        return "Cancelado"

    if is_finished(status):
        return "Producción ROC" if has_roc else "Completado"

    return "En desarrollo" if in_development(status) else "Otro"


def read_block(
    values: Rows,
    start_column: int,
    width: int,
) -> tuple[list[str], Rows]:
    """
    Columnas de una hoja con su fila de encabezados (beeCuentaHoja_).

    Busca en las primeras 12 filas una con "Client" y "Project ID" o
    "ROC ID". Sin encabezados, los datos empiezan en la fila 2.

    Args:
        values: Celdas de la hoja.
        start_column: Primera columna (base 1).
        width: Numero de columnas.

    Returns:
        Encabezados normalizados y filas de datos.
    """
    rows = [
        [read_cell(row, start_column - 1 + offset) for offset in range(width)]
        for row in values
    ]
    header_at = next(
        (
            index
            for index, row in enumerate(rows[:HEADER_SEARCH_ROWS])
            if any(normalize_value(cell) == "client" for cell in row)
            and any(
                normalize_value(cell) in ("project id", "roc id")
                for cell in row
            )
        ),
        -1,
    )

    if header_at < 0:
        return [], rows[1:]

    return [normalize_value(cell) for cell in rows[header_at]], rows[
        header_at + 1 :
    ]


def field_reader(
    headers: Sequence[str],
) -> Callable[[Sequence[CellValue], str, int], CellValue]:
    """Lee una celda por encabezado o por la posicion de respaldo."""

    def get(row: Sequence[CellValue], name: str, fallback: int) -> CellValue:
        key = normalize_value(name)
        index = headers.index(key) if key in headers else fallback

        return read_cell(row, index)

    return get


def sheet_values(reader: SheetReader, name: str) -> Rows:
    """Celdas de la hoja, o vacio si no existe."""
    if not reader.sheet_exists(name):
        return []

    return [list(row) for row in reader.read_values(name)]


def mpb_cache_key(client: object) -> str:
    """Llave de cache por cuenta, como el MD5 del original."""
    digest = hashlib.md5(  # noqa: S324 - solo es una llave de cache
        normalize_value(client).encode("utf-8"),
    ).hexdigest()

    return f"bee_mpb_cuenta_v1_{digest}"


def load_mpb_projects(
    reader: SheetReader,
    client: object,
    cache: AccountCache | None = None,
) -> list[JsonObject]:
    """
    Proyectos AER/T&M de la cuenta en MPB (beeCuentaMPB_).

    Args:
        reader: Lector de Sheets.
        client: Cuenta.
        cache: Cache de 5 minutos para los lotes de consumo; None lee MPB
            en vivo.

    Returns:
        Un proyecto por ID con su fila de MPB (mpbFila).
    """
    key = mpb_cache_key(client) if cache is not None else ""

    if cache is not None:
        saved = cache.get(key)

        if isinstance(saved, list):
            return saved

    values = sheet_values(reader, SHEET_MPB)

    if len(values) < 2:
        return []

    width = min(MPB_MAX_COLUMNS, max(len(row) for row in values))
    data = [[read_cell(row, index) for index in range(width)] for row in values]
    at = next(
        (
            index
            for index, row in enumerate(data[:HEADER_SEARCH_ROWS])
            if {"cliente", "estatus", "service"}
            <= {normalize_value(cell) for cell in row}
        ),
        -1,
    )

    if at < 0:
        return []

    headers = [normalize_value(cell) for cell in data[at]]

    def col(name: str, fallback: int) -> int:
        key_name = normalize_value(name)
        return headers.index(key_name) if key_name in headers else fallback

    columns = {
        "cliente": col("CLIENTE", 1),
        "id": col("ID", 2),
        "nombre": col("NOMBRE", 4),
        "service": col("SERVICE", 5),
        "inicio": col("INICIO", 6),
        "fin": col("FIN", 8),
        "estatus": col("ESTATUS", 19),
        "manager": col("Delivery Manager", 20),
        "horas": col("HORAS", 32),
    }
    found: dict[str, JsonObject] = {}

    for index, row in enumerate(data[at + 1 :]):

        def value(name: str, current: Sequence[CellValue] = row) -> CellValue:
            return read_cell(current, columns[name])

        if not account_matches(value("cliente"), client):
            continue

        service = js_or_text(value("service")).strip()

        if not MPB_SERVICE.match(service):
            continue

        project_id = js_or_text(value("id")).strip()

        if not project_id:
            continue

        stage = js_or_text(value("estatus")).strip()
        finished = is_finished(stage)
        saved_burn = parse_mpb_number(read_cell(row, MPB_BURN_INDEX))
        found[normalize_value(project_id)] = {
            "id": project_id,
            "cliente": js_or_text(value("cliente")).strip(),
            "nombre": js_or_text(value("nombre")).strip(),
            "servicio": service,
            "etapa": stage,
            "deliveryManager": js_or_text(value("manager")).strip(),
            "inicio": parse_mpb_date(value("inicio")),
            "fin": parse_mpb_date(value("fin")),
            "budget": json_number(parse_mpb_hours(value("horas"))),
            "nps": None,
            "npsAplica": False,
            "finalizado": finished,
            "burnGuardado": (
                json_number(saved_burn)
                if finished and saved_burn is not None and saved_burn >= 0
                else None
            ),
            "mpbFila": index + at + 2,
        }

    result = list(found.values())

    if cache is not None:
        cache.set(key, result, MPB_CACHE_SECONDS)

    return result


def json_number(number: float) -> int | float:
    """Numero como lo serializa JSON.stringify (5.0 -> 5)."""
    return int(number) if float(number).is_integer() else number


def find_opportunity_source(
    reader: SheetReader,
    cache: AccountCache,
) -> OpportunitySource | None:
    """
    Hoja del backlog de oportunidades (beeCuentaOportunidadesFuente_).

    Revisa primero la hoja recordada en cache y despues las demas en
    orden de pestanas; la primera con Account Name, Opportunity Name,
    Opportunity Stage y Total Hours en sus primeras 12 filas gana.

    Args:
        reader: Lector de Sheets.
        cache: Cache donde se recuerda la hoja por 6 horas.

    Returns:
        La hoja con sus columnas, o None.
    """
    cached_name = cache.get(OPPORTUNITY_CACHE_KEY)
    names = reader.list_sheet_names()

    if isinstance(cached_name, str) and cached_name in names:
        names = [cached_name] + [name for name in names if name != cached_name]
    else:
        cached_name = None

    previews = reader.read_previews(
        names,
        HEADER_SEARCH_ROWS,
        OPPORTUNITY_PREVIEW_COLUMNS,
    )

    for name in names:
        preview = previews.get(name) or []

        if (
            not preview
            or max(len(row) for row in preview) < OPPORTUNITY_MIN_COLUMNS
        ):
            continue

        at = next(
            (
                index
                for index, row in enumerate(preview)
                if all(
                    any(normalize_value(cell) == header for cell in row)
                    for header in OPPORTUNITY_HEADERS
                )
            ),
            -1,
        )

        if at < 0:
            continue

        headers = [normalize_value(cell) for cell in preview[at]]

        def col(*aliases: str, current: list[str] = headers) -> int:
            return next(
                (
                    index
                    for index, header in enumerate(current)
                    if header in aliases
                ),
                -1,
            )

        if name != cached_name:
            cache.set(OPPORTUNITY_CACHE_KEY, name, OPPORTUNITY_CACHE_SECONDS)

        return OpportunitySource(
            sheet=name,
            header_row=at + 1,
            columns={
                "account": col("account name"),
                "name": col("opportunity name"),
                "manager": col("delivery manager"),
                "stage": col("opportunity stage"),
                "close": col(
                    "fecha de cierre - diario",
                    "fecha de cierre diario",
                    "fecha de cierre",
                ),
                "hours": col("total hours"),
            },
        )

    return None


def load_opportunities(
    reader: SheetReader,
    client: object,
    cache: AccountCache,
) -> JsonObject:
    """
    Oportunidades abiertas de la cuenta (beeCuentaOportunidades_).

    Returns:
        {"source": hoja, "items": [...]}.
    """
    source = find_opportunity_source(reader, cache)

    if source is None:
        return {"source": "", "items": []}

    columns = source.columns
    rows = sheet_values(reader, source.sheet)[source.header_row :]
    items = []

    for row in rows:
        if not account_matches(read_cell(row, columns["account"]), client):
            continue

        item = {
            "account": js_or_text(read_cell(row, columns["account"])).strip(),
            "name": js_or_text(read_cell(row, columns["name"])).strip(),
            "manager": ""
            if columns["manager"] < 0
            else js_or_text(read_cell(row, columns["manager"])).strip(),
            "stage": js_or_text(read_cell(row, columns["stage"])).strip(),
            "close": ""
            if columns["close"] < 0
            else parse_mpb_date(read_cell(row, columns["close"])),
            "hours": json_number(
                parse_mpb_hours(read_cell(row, columns["hours"]))
            ),
        }

        if item["name"] and not CLOSED_OPPORTUNITY.search(str(item["stage"])):
            items.append(item)

    return {"source": source.sheet, "items": items}


def read_history_projects(
    values: Rows, client: object
) -> dict[str, JsonObject]:
    """
    Proyectos de la cuenta en Historico_Proyectos (una fila por etapa).

    Args:
        values: Celdas de Historico_Proyectos.
        client: Cuenta.

    Returns:
        ID normalizado -> proyecto con sus etapas.
    """
    headers, rows = read_block(values, HISTORY_START_COLUMN, HISTORY_WIDTH)
    get = field_reader(headers)
    projects: dict[str, JsonObject] = {}

    for row in rows:
        client_name = js_or_text(get(row, "Client", 1)).strip()

        if not account_matches(client_name, client):
            continue

        project_id = js_or_text(get(row, "Project ID", 2)).strip()

        if not project_id:
            continue

        identity = normalize_value(project_id)
        item = projects.get(identity) or {
            "id": project_id,
            "client": client_name,
            "nombre": js_or_text(get(row, "Project Name", 4)),
            "servicio": js_or_text(get(row, "Service", 3)),
            "deliveryManager": js_or_text(get(row, "Delivery Manager", 0)),
            "etapas": [],
            "budget": None,
            "burn": None,
            "nps": None,
            "diasSuspension": None,
            "profitability": "",
        }
        item["etapas"].append(
            {
                "nombre": js_or_text(get(row, "Stage", 6)).strip(),
                "fechaFinReal": parse_mpb_date(get(row, "Actual Finish", 11)),
                "fechaFinPlan": parse_mpb_date(get(row, "Plan Finish", 9)),
            },
        )

        for prop, field_name, fallback in (
            ("budget", "Budget", 18),
            ("burn", "Burn", 19),
            ("nps", "NPS", 35),
        ):
            raw = get(row, field_name, fallback)
            number = parse_mpb_number(raw)

            if number is None:
                continue

            item[prop] = (
                js_round(number * 100)
                if prop == "nps"
                and isinstance(raw, int | float)
                and not isinstance(raw, bool)
                and abs(number) <= 1
                else json_number(number)
            )

        on_hold = parse_mpb_number(get(row, "Days On Hold", 28))

        if on_hold is not None:
            item["diasSuspension"] = json_number(
                max(item["diasSuspension"] or 0, on_hold),
            )

        item["profitability"] = js_or_text(
            get(row, "Profitability", 30) or item["profitability"],
        )
        item["nombre"] = item["nombre"] or js_or_text(
            get(row, "Project Name", 4)
        )
        item["servicio"] = item["servicio"] or js_or_text(
            get(row, "Service", 3)
        )
        projects[identity] = item

    return projects


def read_roc(values: Rows, client: object) -> list[JsonObject]:
    """Bots de la cuenta en ROC con ROC ID."""
    headers, rows = read_block(values, 1, ROC_WIDTH)
    get = field_reader(headers)
    roc = [
        {
            "id": js_or_text(get(row, "ROC ID", 3)).strip(),
            "botId": js_or_text(get(row, "BOT ID", 4)).strip(),
            "estado": js_or_text(get(row, "Status ROC", 6)).strip(),
            "proceso": js_or_text(get(row, "Process Name", 7)).strip(),
            "servicio": js_or_text(get(row, "Service", 5)).strip(),
            "inicio": parse_mpb_date(get(row, "Start", 12)),
            "fin": parse_mpb_date(get(row, "Finish", 13)),
            "deliveryManager": js_or_text(
                get(row, "Delivery Manager", 11)
            ).strip(),
        }
        for row in rows
        if account_matches(get(row, "Client", 0), client)
    ]

    return [item for item in roc if item["id"]]


def read_project_statuses(values: Rows) -> dict[str, str]:
    """
    Estado de cada proyecto en la hoja Proyectos.

    Args:
        values: Celdas de Proyectos.

    Returns:
        ID normalizado -> estado.
    """
    if len(values) < 2:
        return {}

    preview = values[:HEADER_SEARCH_ROWS]
    header_index = next(
        (
            index
            for index, row in enumerate(preview)
            if any(
                PROJECT_ID_HEADER.match(js_or_text(cell).strip())
                for cell in row
            )
        ),
        -1,
    )

    if header_index < 0:
        return {}

    width = max(len(row) for row in values)
    headers = [
        normalize_value(read_cell(preview[header_index], index))
        for index in range(width)
    ]
    id_index = next(
        (
            index
            for index, header in enumerate(headers)
            if PROJECT_ID_HEADER.match(header)
        ),
        -1,
    )
    status_index = next(
        (
            index
            for index, header in enumerate(headers)
            if STATUS_HEADER.match(header)
        ),
        -1,
    )
    statuses: dict[str, str] = {}

    if status_index < 0:
        return statuses

    for row in values[header_index + 1 :]:
        project_id = normalize_value(read_cell(row, id_index))

        if project_id:
            statuses[project_id] = js_or_text(read_cell(row, status_index))

    return statuses


def build_history_item(
    project: Mapping[str, Any],
    statuses: Mapping[str, str],
    roc_bot_ids: set[str],
    today: str,
) -> JsonObject:
    """Proyecto del historico con su etapa actual y estado visible."""
    stages = project["etapas"]
    current = [
        stage
        for stage in stages
        if CURRENT_STAGE.search(stage["nombre"]) and not stage["fechaFinReal"]
    ]
    final_stage = stages[-1] if stages else {"nombre": ""}
    base = id_base(project["id"])
    source_status = (
        statuses.get(normalize_value(project["id"])) or statuses.get(base) or ""
    )

    if is_terminal(source_status):
        stage_name = source_status
    elif is_terminal(final_stage["nombre"]):
        stage_name = final_stage["nombre"]
    elif current:
        stage_name = current[0]["nombre"]
    else:
        stage_name = final_stage["nombre"] or source_status

    budget, burn = project["budget"], project["burn"]

    return {
        "id": project["id"],
        "nombre": project["nombre"],
        "cliente": project["client"],
        "servicio": project["servicio"],
        "deliveryManager": project["deliveryManager"],
        "etapa": stage_name,
        "estado": project_state(stage_name, base in roc_bot_ids),
        "budget": budget,
        "burn": burn,
        "nps": project["nps"],
        "diasSuspension": project["diasSuspension"],
        "profitability": project["profitability"],
        "excedido": budget is not None and burn is not None and burn > budget,
        "atrasado": any(
            stage["fechaFinPlan"]
            and stage["fechaFinPlan"] < today
            and not stage["fechaFinReal"]
            and BUILD_STAGE.search(stage["nombre"])
            for stage in stages
        ),
    }


def build_account_view(
    reader: SheetReader,
    client: object,
    cache: AccountCache,
    today: date,
) -> JsonObject:
    """
    Vista completa de la cuenta (obtenerVistaCuentaBeecker).

    Args:
        reader: Lector de Sheets.
        client: Cuenta seleccionada.
        cache: Cache de la hoja de oportunidades.
        today: Fecha local de hoy.

    Returns:
        La respuesta del original o {"ok": False, "error"}.
    """
    if not normalize_value(client):
        return {"ok": False, "error": "Selecciona un cliente."}

    reader.prefetch(
        [
            sheet_names.SHEET_PROJECTS_HISTORY,
            ROC_SHEET,
            sheet_names.SHEET_PROJECTS,
            SHEET_MPB,
        ],
    )
    history = sheet_values(reader, sheet_names.SHEET_PROJECTS_HISTORY)
    projects = read_history_projects(history, client)
    roc_values = sheet_values(reader, ROC_SHEET)
    roc = read_roc(roc_values, client)
    roc_bot_ids = {id_base(item["botId"]) for item in roc} - {""}
    statuses = read_project_statuses(
        sheet_values(reader, sheet_names.SHEET_PROJECTS)
    )
    today_text = today.isoformat()
    projects_list = [
        build_history_item(project, statuses, roc_bot_ids, today_text)
        for project in projects.values()
    ]
    mpb = load_mpb_projects(reader, client)

    for project in mpb:
        burn = project["burnGuardado"]
        item = {
            **project,
            "estado": project_state(
                project["etapa"],
                id_base(project["id"]) in roc_bot_ids,
            ),
            "burn": burn,
            "clockifyPending": burn is None,
            "excedido": burn is not None
            and project["budget"] > 0
            and burn > project["budget"],
            "atrasado": False,
        }
        identity = normalize_value(project["id"])
        index = next(
            (
                position
                for position, existing in enumerate(projects_list)
                if normalize_value(existing["id"]) == identity
            ),
            -1,
        )

        if index >= 0:
            projects_list[index] = item
        else:
            projects_list.append(item)

    with_nps = [
        project for project in projects_list if project["nps"] is not None
    ]
    models = list(
        dict.fromkeys(
            project["servicio"]
            for project in projects_list
            if project["servicio"]
        ),
    )
    opportunities = load_opportunities(reader, client, cache)
    history_rows = read_block(history, HISTORY_START_COLUMN, HISTORY_WIDTH)[1]
    roc_rows = read_block(roc_values, 1, ROC_WIDTH)[1]

    return {
        "ok": True,
        "cliente": js_null_text(client).strip(),
        "fechaCorte": today_text,
        "modelos": models,
        "proyectos": projects_list,
        "mpbPendientes": sum(
            1 for project in mpb if project["burnGuardado"] is None
        ),
        "roc": roc,
        "rocActivos": sum(
            1 for item in roc if ACTIVE_ROC.search(item["estado"])
        ),
        "rocProyectosActivos": len(
            {
                id_base(project["id"])
                for project in projects_list
                if project["estado"] == "Producción ROC"
            },
        ),
        "oportunidades": opportunities["items"],
        "oportunidadesFuente": opportunities["source"],
        "nps": js_round(
            sum(project["nps"] for project in with_nps) / len(with_nps)
        )
        if with_nps
        else None,
        "npsMuestra": len(with_nps),
        "fuentes": {
            "historico": bool(history_rows),
            "roc": bool(roc_rows),
            "mpb": bool(mpb),
        },
    }
