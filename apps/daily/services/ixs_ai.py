"""Analisis, preguntas, memoria y minutas con IA de la vista IXS."""

import base64
import hashlib
import json
import re
from collections.abc import Mapping, Sequence
from datetime import datetime
from typing import Any

from apps.daily.services.claude_assist import ClaudeSettings
from apps.daily.services.ixs_ai_facts import build_facts, validate_claims
from apps.daily.services.ixs_store import (
    IxsError,
    IxsStore,
    cell,
    project_id,
    write_lock,
)
from core.exceptions import DashboardError
from core.integrations.claude_client import text_blocks
from core.utils.cell_types import CellValue
from core.utils.dates import to_datetime, to_local_naive
from core.utils.js_values import (
    js_json,
    js_len,
    js_or,
    js_or_text,
    js_slice,
    js_str,
)

"""BKD.070.022 - IA de la vista IXS
Equivale a ixsIAClaude_(), ixsIAAnalizar(), ixsIAPreguntar(),
ixsIAAnalisisLeer(), ixsIAMemoriaLeer(), ixsIAMemoriaActualizar(),
ixsIAMinutasLeer() e ixsIAMinutaGuardar(). Claude solo recibe hechos con
identificador y cada afirmacion de su respuesta debe citarlos.
"""

JsonObject = dict[str, Any]

FACTS_LIMIT = 21000
ANALYSIS_TOKENS = 2300
ANSWER_TOKENS = 800
MAX_QUESTION = 750
ANSWER_LINES = 15
ANALYSIS_ITEMS = 4
MAX_STATE = 100
MIN_QUESTION = 5
ANALYSIS_CACHE_SECONDS = 21600
MAX_ANALYSIS_JSON = 45000
MAX_SNAPSHOT_JSON = 45000
MAX_MEMORY_ANALYSIS_JSON = 25000
MAX_MINUTE = 18000
ANALYSIS_SHEET = "IXS_IA_Analisis"
ANALYSIS_HEADERS = ("Proyecto", "Fecha", "Análisis JSON", "Evidencias JSON")
MEMORY_SHEET = "IXS_IA_Memoria"
MEMORY_HEADERS = ("UID", "Proyecto", "Fecha", "Snapshot JSON", "Análisis JSON")
MINUTES_SHEET = "IXS_IA_Minutas"
MINUTES_HEADERS = ("UID", "Proyecto", "Fecha", "Tema", "Contenido", "Guardado")
ANALYSIS_KEYS = ("resumen", "hallazgos", "recomendaciones", "alertas")
TOP_FACT = re.compile(r"^PR-|^FIN-|^AZ-RES|^CL-RES")
DETAIL_FACT = re.compile(r"^ET-|^REC-|^VAC-|^COM-|^ACC-|^RAID-")
CITED_ID = re.compile(r"\[([A-Z0-9-]+)\]")
ISO_DAY = re.compile(r"\d{4}-\d{2}-\d{2}", re.ASCII)
CODE_FENCE_START = re.compile(r"^```(?:json)?\s*", re.IGNORECASE)
CODE_FENCE_END = re.compile(r"\s*```$")

ANALYSIS_INSTRUCTIONS = (
    "Actúa como analista de proyecto. Usa exclusivamente HECHOS y cita sus "
    "identificadores en CADA afirmación. Devuelve solo JSON: "
    '{"resumen":[{"texto":"","evidencias":["ID"]}],"hallazgos":[{"titulo":'
    '"","detalle":"","prioridad":"Alta","evidencias":["ID"]}],'
    '"recomendaciones":[{"titulo":"","detalle":"","evidencias":["ID"]}],'
    '"alertas":[{"titulo":"","detalle":"","evidencias":["ID"]}],"estado":""}. '
    "Máximo 4 elementos por lista, frases breves. No inventes fechas, "
    "personas, porcentajes, pronósticos o compromisos. No presentes "
    "inferencias como registros. Omite asuntos sin evidencia y evita "
    "enumerar información ausente."
)
INTERRUPTED_MESSAGE = (
    "La respuesta se interrumpió. Vuelve a generar el análisis."
)
UNVERIFIED_MESSAGE = "No se pudo verificar el análisis. Vuelve a intentarlo."
ANSWER_INSTRUCTIONS = (
    "Responde en español usando solo los HECHOS provistos. Cita [ID] tras "
    "cada afirmación verificable. No inventes hechos ni fechas. Si una "
    "afirmación no está respaldada, omítela. Responde directamente la "
    "pregunta, sin listas de datos faltantes."
)


def fact_rank(fact: Mapping[str, Any], question: object) -> int:
    """Prioridad del hecho: indicadores, luego detalle, luego el resto."""
    fact_id = str(fact["id"])

    if TOP_FACT.search(fact_id):
        return 0

    if DETAIL_FACT.search(fact_id):
        return 1

    question_text = js_or_text(question)

    if (
        fact_id.startswith("WI-")
        and question_text
        and fact_id[3:].lower() in question_text.lower()
    ):
        return 0

    return 2


def select_facts(
    context: Mapping[str, Any],
    question: object,
) -> list[JsonObject]:
    """Hechos ordenados por prioridad hasta 21,000 caracteres de JSON."""
    facts = sorted(
        build_facts(context, question),
        key=lambda fact: fact_rank(fact, question),
    )
    selected: list[JsonObject] = []
    used = 0

    for fact in facts:
        size = js_len(js_json(fact))

        if used + size < FACTS_LIMIT:
            selected.append(fact)
            used += size

    return selected


def ask_project(
    settings: ClaudeSettings,
    project: str,
    context: Mapping[str, Any],
    question: object,
    wants_json: bool,
) -> JsonObject:
    """
    Pregunta o analisis con hechos verificables (ixsIAClaude_).

    Args:
        settings: Configuracion de Claude.
        project: ID del proyecto.
        context: Contexto del panel.
        question: Pregunta (vacia para el analisis).
        wants_json: True para el analisis estructurado.

    Returns:
        {"ok", "texto"} o {"ok", "analisis", "evidencias"} con "modelo".

    Raises:
        DashboardError: Si no hay conexion con Claude.
        ValueError: Si Claude responde algo que no es JSON.
    """
    if not settings.api_key:
        return {
            "ok": False,
            "error": "Configura tu API key de Claude en Configuración para "
            "usar IA.",
        }

    selected = select_facts(context, question)
    instructions = ANALYSIS_INSTRUCTIONS if wants_json else ANSWER_INSTRUCTIONS
    question_text = (
        ""
        if wants_json
        else "Pregunta: " + js_slice(js_or_text(question), 0, MAX_QUESTION)
    )
    response = settings.build_client().create_message(
        {
            "model": settings.model,
            "max_tokens": ANALYSIS_TOKENS if wants_json else ANSWER_TOKENS,
            "temperature": 0,
            "messages": [
                {
                    "role": "user",
                    "content": f"{instructions}\nProyecto: {project}\nHECHOS: "
                    f"{js_json(selected)}\n{question_text}",
                },
            ],
        },
    )

    if response.status_code >= 300:
        return {
            "ok": False,
            "error": f"Claude respondió {response.status_code}: "
            f"{js_slice(response.body, 0, 180)}",
        }

    data = response.json()
    text = "\n".join(text_blocks(data))

    if not text:
        return {"ok": False, "error": "Claude no devolvió texto."}

    if not wants_json:
        return answer_result(settings, text, selected)

    return analysis_result(settings, text, selected, data)


def answer_result(
    settings: ClaudeSettings,
    text: str,
    selected: Sequence[JsonObject],
) -> JsonObject:
    """Respuesta libre: solo las lineas que citan hechos validos."""
    lines = [
        {"texto": line, "evidencias": CITED_ID.findall(line)}
        for line in text.split("\n")
    ]
    checked = [
        str(claim["texto"])
        for claim in validate_claims(lines, selected, ANSWER_LINES)
    ]
    first = next((fact for fact in selected if fact["id"] == "PR-1"), None)
    first = first or (selected[0] if selected else None)
    fallback = (
        f"{first['texto']} [{first['id']}]"
        if first
        else "No hay registros verificables para responder."
    )

    return {
        "ok": True,
        "texto": "\n".join(checked) or fallback,
        "modelo": settings.model,
    }


def analysis_result(
    settings: ClaudeSettings,
    text: str,
    selected: list[JsonObject],
    data: Mapping[str, Any],
) -> JsonObject:
    """Analisis estructurado con cada afirmacion validada."""
    try:
        cleaned = CODE_FENCE_END.sub(
            "",
            CODE_FENCE_START.sub("", text.strip(), count=1),
            count=1,
        )

        try:
            parsed = json.loads(cleaned)
        except ValueError:
            start, end = cleaned.find("{"), cleaned.rfind("}")

            if start < 0 or end <= start:
                raise

            parsed = json.loads(cleaned[start : end + 1])

        if not isinstance(parsed, dict):
            raise ValueError("Esquema incompleto")

        analysis: JsonObject = {
            key: validate_claims(parsed.get(key), selected, ANALYSIS_ITEMS)
            for key in ANALYSIS_KEYS
        }
        analysis["estado"] = js_slice(
            js_or_text(parsed.get("estado")),
            0,
            MAX_STATE,
        )
    except (ValueError, TypeError, AttributeError):
        stop_reason = data.get("stop_reason")
        return {
            "ok": False,
            "error": INTERRUPTED_MESSAGE
            if stop_reason == "max_tokens"
            else UNVERIFIED_MESSAGE,
            "motivo": stop_reason or "formato",
        }

    if not analysis["resumen"]:
        summary = next(
            (fact for fact in selected if fact["id"] == "PR-1"), None
        )

        if summary:
            analysis["resumen"] = [
                {
                    "texto": summary["texto"],
                    "evidencias": [summary["id"]],
                    "fuente": summary["fuente"],
                },
            ]

    return {
        "ok": True,
        "analisis": analysis,
        "evidencias": selected,
        "modelo": settings.model,
    }


def valid_context(
    project_value: object, context: object
) -> tuple[str, JsonObject]:
    """ID y contexto cuando el contexto es del mismo proyecto."""
    project = js_or_text(project_value).strip()

    if (
        not project
        or not isinstance(context, dict)
        or js_or_text(context.get("proyecto")) != project
    ):
        return "", {}

    return project, context


def analysis_cache_key(project: str, context: Mapping[str, Any]) -> str:
    """Llave de cache por proyecto y contenido del contexto."""
    digest = hashlib.sha256(js_json(context).encode("utf-8")).digest()
    text = base64.urlsafe_b64encode(digest).decode("ascii")[:28]

    return f"ixsia_{re.sub(r'[^a-zA-Z0-9]', '_', project)}_{text}"


def analyze_project(
    settings: ClaudeSettings,
    store: IxsStore,
    request: tuple[object, object, object],
) -> JsonObject:
    """
    Analisis del proyecto con cache de 6 horas (ixsIAAnalizar).

    Args:
        settings: Configuracion de Claude (su store es la cache).
        store: Hojas de la vista (guarda el ultimo analisis).
        request: ID, contexto y forzar.

    Returns:
        El analisis, con "cache" si viene de la cache.
    """
    project_value, context_value, force = request
    project, context = valid_context(project_value, context_value)

    if not project:
        return {"ok": False, "error": "Datos del proyecto inválidos."}

    key = analysis_cache_key(project, context)

    if not force:
        cached = settings.store.get(key)

        if isinstance(cached, dict):
            return {**cached, "cache": True}

    try:
        result = ask_project(settings, project, context, "", True)
    except DashboardError as error:
        return {"ok": False, "error": error.detail}
    except ValueError as error:
        return {"ok": False, "error": str(error)}

    if result.get("ok"):
        result["fecha"] = store.local_now().strftime("%Y-%m-%d %H:%M")
        settings.store.set(
            key, json.loads(js_json(result)), ANALYSIS_CACHE_SECONDS
        )
        saved = save_analysis(store, project, result)

        if not saved["ok"]:
            result["avisoGuardado"] = saved["error"]

    return result


def ask_question(
    settings: ClaudeSettings,
    request: tuple[object, object, object],
) -> JsonObject:
    """
    Pregunta libre sobre el proyecto (ixsIAPreguntar).

    Args:
        settings: Configuracion de Claude.
        request: ID, contexto y pregunta (minimo 5 caracteres).

    Returns:
        {"ok", "texto", "modelo"} o {"ok": False, "error"}.
    """
    project_value, context_value, question_value = request
    project, context = valid_context(project_value, context_value)
    question = js_or_text(question_value).strip()

    if not project or len(question) < MIN_QUESTION:
        return {
            "ok": False,
            "error": "Escribe una pregunta válida para este proyecto.",
        }

    try:
        return ask_project(settings, project, context, question, False)
    except DashboardError as error:
        return {"ok": False, "error": error.detail}
    except ValueError as error:
        return {"ok": False, "error": str(error)}


def save_analysis(
    store: IxsStore, project_value: str, result: JsonObject
) -> JsonObject:
    """
    Guarda el ultimo analisis del proyecto (ixsIAAnalisisGuardar_).

    Returns:
        {"ok": True} o el aviso de que no se pudo guardar.
    """
    try:
        with write_lock():
            project = project_id(project_value)
            payload = js_json(js_or(result.get("analisis"), {}))
            evidence = js_json(js_or(result.get("evidencias"), []))

            if (
                len(payload) > MAX_ANALYSIS_JSON
                or len(evidence) > MAX_ANALYSIS_JSON
            ):
                raise IxsError(
                    "El análisis excede el tamaño permitido para guardarlo.",
                )

            store.writer.ensure_sheet(ANALYSIS_SHEET, ANALYSIS_HEADERS)
            rows = store.values(ANALYSIS_SHEET)
            target = next(
                (
                    number
                    for number, row in enumerate(rows[1:], start=2)
                    if js_str(cell(row, 0)) == project
                ),
                0,
            )
            record: list[CellValue] = [
                project,
                result["fecha"],
                payload,
                evidence,
            ]

            if target:
                store.writer.write_row(ANALYSIS_SHEET, target, record)
            else:
                store.writer.append_row(ANALYSIS_SHEET, record)
    except DashboardError as error:
        return {
            "ok": False,
            "error": "Se generó el análisis, pero no se pudo guardar: "
            f"{error.detail}",
        }

    return {"ok": True}


def date_text(value: CellValue | datetime, with_time: bool) -> str:
    """Fecha de la hoja como yyyy-MM-dd (HH:mm); el texto queda igual."""
    if isinstance(value, datetime):
        moment: datetime | None = (
            to_local_naive(value) if value.tzinfo else value
        )
    elif isinstance(value, int | float) and not isinstance(value, bool):
        moment = to_datetime(value)
    else:
        return js_str(value)

    if moment is None:
        return js_str(value)

    return moment.strftime("%Y-%m-%d %H:%M" if with_time else "%Y-%m-%d")


def parse_json_cell(value: CellValue, default: str) -> Any:
    """JSON.parse(String(x || default))."""
    return json.loads(js_or_text(value) or default)


def read_analysis(store: IxsStore, project_value: object) -> JsonObject:
    """
    Ultimo analisis guardado, o el de la memoria (ixsIAAnalisisLeer).

    Returns:
        {"ok", "analisis", "evidencias", "fecha"} o {"ok", "analisis": None}.
    """
    try:
        project = project_id(project_value)
        rows = [
            row
            for row in store.values(ANALYSIS_SHEET)[1:]
            if js_str(cell(row, 0)) == project
        ]

        if rows:
            row = rows[-1]
            return {
                "ok": True,
                "analisis": json.loads(js_str(cell(row, 2))),
                "evidencias": parse_json_cell(cell(row, 3), "[]"),
                "fecha": date_text(cell(row, 1), True)
                if cell(row, 1) != ""
                else "",
            }

        memory = read_memory(store, project)

        if memory["ok"]:
            for cut in (memory["actual"], memory["anterior"]):
                if cut and has_findings(cut.get("analisis")):
                    return {
                        "ok": True,
                        "analisis": cut["analisis"],
                        "evidencias": [],
                        "fecha": cut["fecha"],
                        "desdeMemoria": True,
                    }

        return {"ok": True, "analisis": None}
    except (DashboardError, ValueError) as error:
        detail = (
            error.detail if isinstance(error, DashboardError) else str(error)
        )
        return {
            "ok": False,
            "error": f"No se pudo recuperar el último análisis: {detail}",
        }


def has_findings(analysis: object) -> bool:
    """El analisis tiene al menos una lista con elementos."""
    return isinstance(analysis, dict) and any(
        isinstance(analysis.get(key), list) and analysis.get(key)
        for key in ANALYSIS_KEYS
    )


def read_memory(store: IxsStore, project_value: object) -> JsonObject:
    """
    Los dos ultimos cortes del proyecto (ixsIAMemoriaLeer).

    Returns:
        {"ok", "actual", "anterior"}.
    """
    try:
        project = project_id(project_value)
        store.writer.ensure_sheet(MEMORY_SHEET, MEMORY_HEADERS)
        rows = [
            row
            for row in store.values(MEMORY_SHEET)[1:]
            if js_str(cell(row, 1)) == project
        ]
        cuts = [
            {
                "uid": js_str(cell(row, 0)),
                "fecha": date_text(cell(row, 2), True),
                "snapshot": parse_json_cell(cell(row, 3), "{}"),
                "analisis": parse_json_cell(cell(row, 4), "{}"),
            }
            for row in reversed(rows[-2:])
        ]
    except (DashboardError, ValueError) as error:
        detail = (
            error.detail if isinstance(error, DashboardError) else str(error)
        )
        return {"ok": False, "error": detail}

    return {
        "ok": True,
        "actual": cuts[0] if cuts else None,
        "anterior": cuts[1] if len(cuts) > 1 else None,
    }


def save_memory(
    store: IxsStore,
    project_value: object,
    snapshot: object,
    analysis: object,
) -> JsonObject:
    """
    Guarda un corte del proyecto (ixsIAMemoriaActualizar).

    Returns:
        La memoria actualizada.
    """
    try:
        with write_lock():
            project = project_id(project_value)

            if (
                not isinstance(snapshot, dict)
                or js_or_text(snapshot.get("proyecto")) != project
            ):
                raise IxsError("El corte no corresponde al proyecto.")

            snapshot_json = js_json(snapshot)
            analysis_json = js_json(js_or(analysis, {}))

            if (
                len(snapshot_json) > MAX_SNAPSHOT_JSON
                or len(analysis_json) > MAX_MEMORY_ANALYSIS_JSON
            ):
                raise IxsError(
                    "Los datos del corte exceden el tamaño permitido."
                )

            store.writer.ensure_sheet(MEMORY_SHEET, MEMORY_HEADERS)
            store.writer.append_row(
                MEMORY_SHEET,
                [
                    store.new_uid(),
                    project,
                    store.now,
                    snapshot_json,
                    analysis_json,
                ],
            )

            return read_memory(store, project)
    except DashboardError as error:
        return {"ok": False, "error": error.detail}


def read_minutes(store: IxsStore, project_value: object) -> JsonObject:
    """
    Minutas IXS del proyecto, de la mas reciente a la mas antigua.

    Returns:
        {"ok", "filas"}.
    """
    try:
        project = project_id(project_value)
    except DashboardError as error:
        return {"ok": False, "error": error.detail}

    store.writer.ensure_sheet(MINUTES_SHEET, MINUTES_HEADERS)
    rows = [
        row
        for row in store.values(MINUTES_SHEET)[1:]
        if js_str(cell(row, 1)) == project
    ]

    return {
        "ok": True,
        "filas": [
            {
                "uid": js_str(cell(row, 0)),
                "fecha": date_text(cell(row, 2), False),
                "tema": js_or_text(cell(row, 3)),
                "contenido": js_or_text(cell(row, 4)),
                "guardado": date_text(cell(row, 5), True)
                if cell(row, 5) != ""
                else "",
            }
            for row in reversed(rows)
        ],
    }


def save_minute(
    store: IxsStore,
    request: tuple[object, object, object, object],
) -> JsonObject:
    """
    Guarda una minuta del proyecto (ixsIAMinutaGuardar).

    Args:
        store: Hojas de la vista.
        request: ID, tema, fecha (YYYY-MM-DD) y contenido.

    Returns:
        Las minutas del proyecto.
    """
    project_value, topic_value, date_value, content_value = request

    try:
        with write_lock():
            project = project_id(project_value)
            topic = js_or_text(topic_value).strip()
            content = js_or_text(content_value).strip()
            day = js_or_text(date_value).strip()

            if (
                not topic
                or not content
                or not ISO_DAY.fullmatch(day)
                or js_len(content) > MAX_MINUTE
            ):
                raise IxsError("Completa tema, fecha y contenido de la minuta.")

            store.writer.ensure_sheet(MINUTES_SHEET, MINUTES_HEADERS)
            store.writer.append_row(
                MINUTES_SHEET,
                [store.new_uid(), project, day, topic, content, store.now],
            )

            return read_minutes(store, project)
    except DashboardError as error:
        return {"ok": False, "error": error.detail}
