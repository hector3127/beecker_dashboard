"""Minutas IA de AER/T&M: hoja, plantilla y carpeta de Drive."""

import re
import unicodedata
from collections import deque
from typing import Any

from apps.aer.services.ai_common import (
    PROMPTS,
    AerAiContext,
    AerAiError,
    clip,
    read_rows,
    validate_project,
)
from core.exceptions import DashboardError, describe_error
from core.utils.dates import to_local_naive
from core.utils.js_values import js_locale_key, js_slice, js_str
from core.utils.locks import script_lock

"""BKD.080.012 - IA AER: minutas
Equivale a listarMinutasIAProyectoAER(), guardarMinutaIAProyectoAER(),
obtenerConfigCarpetaMinutasAER(), guardarConfigCarpetaMinutasAER(),
obtenerPromptMinutaDefectoAER(), buscarMinutasCarpetaAER() y
generarBorradorMinutaDesdeCarpetaClaudeAER(). Drive solo se lee; nunca se
crean ni convierten archivos.
"""

JsonObject = dict[str, Any]

MINUTES_SHEET = "AER_IA_Minutas"
MINUTES_HEADERS = (
    "UID",
    "ID_Proyecto",
    "Fecha",
    "Tema",
    "Contenido",
    "Guardado_En",
)
MINUTES_KINDS = ("", "", "date", "", "", "datetime")
CONFIG_SHEET = "AER_IA_Minutas_Config"
CONFIG_HEADERS = (
    "ID_Proyecto",
    "Folder_URL",
    "Nombre_Busqueda",
    "Actualizado",
    "Nombre_Frecuente",
    "Prompt_Minuta",
)
CONFIG_KINDS = ("", "", "", "datetime", "", "")
FOLDER_ID = re.compile(r"(?:/folders/|[?&]id=)([-\w]{12,})", re.IGNORECASE)
RESOURCE_KEY = re.compile(r"[?&]resourcekey=([-\w]+)", re.IGNORECASE)
NON_ALNUM = re.compile(r"[^a-z0-9]+")
TERM_SPLIT = re.compile(r"[,;]+")
WHITESPACE = re.compile(r"\s+")
FOLDER_MIME = "application/vnd.google-apps.folder"
DOC_MIME = "application/vnd.google-apps.document"
TEXT_MIME = "text/plain"
MAX_FOLDERS = 18
MAX_FILES = 200
MAX_DEPTH = 2
MAX_RESULTS = 60
MAX_TEXT_BYTES = 200000
MAX_LISTED = 30


def default_prompt() -> str:
    """Plantilla de minuta por defecto (_aeri70PromptMinutaDefecto_)."""
    return str(PROMPTS["defaultMinute"])


def last_minute_brief(ctx: AerAiContext, project_id: str) -> str:
    """Contenido de la ultima minuta del proyecto (850 caracteres)."""
    for row in reversed(read_rows(ctx.reader, MINUTES_SHEET, MINUTES_KINDS)):
        if row[1].strip() == project_id:
            return clip(row[4], 850)

    return ""


def list_minutes(ctx: AerAiContext, project_value: object) -> JsonObject:
    """Minutas guardadas del proyecto, las mas recientes primero."""
    try:
        project_id = validate_project(ctx.reader, project_value)
        rows = [
            {
                "uid": row[0],
                "fecha": row[2],
                "tema": row[3],
                "contenido": row[4],
                "guardado": row[5],
            }
            for row in read_rows(ctx.reader, MINUTES_SHEET, MINUTES_KINDS)
            if row[1] == project_id
        ]
        rows.sort(key=lambda row: js_locale_key(row["guardado"]), reverse=True)

        return {"ok": True, "filas": rows[:MAX_LISTED]}
    except DashboardError as error:
        return {"ok": False, "error": describe_error(error)}


def save_minute(
    ctx: AerAiContext,
    project_value: object,
    data: Any,
) -> JsonObject:
    """Agrega una minuta a AER_IA_Minutas (guardarMinutaIAProyectoAER)."""
    try:
        project_id = validate_project(ctx.reader, project_value)
        values = data if isinstance(data, dict) else {}
        topic = clip(values.get("tema"), 140)
        content = clip(values.get("contenido"), 9500)

        if not topic or not content:
            raise AerAiError("Completa el tema y el contenido de la minuta.")

        with script_lock(10):
            if not ctx.reader.sheet_exists(MINUTES_SHEET):
                ctx.writer.ensure_sheet(MINUTES_SHEET, MINUTES_HEADERS)

            uid = ctx.new_uid()
            ctx.writer.append_row(
                MINUTES_SHEET,
                [
                    uid,
                    project_id,
                    clip(values.get("fecha"), 12) or ctx.today(),
                    topic,
                    content,
                    ctx.stamp(),
                ],
            )

        return {"ok": True, "uid": uid}
    except DashboardError as error:
        return {"ok": False, "error": describe_error(error)}


def read_config(ctx: AerAiContext, project_id: str) -> JsonObject:
    """Carpeta, filtros y plantilla del proyecto (_aeri57ReadConfig)."""
    template = default_prompt()

    for row in read_rows(ctx.reader, CONFIG_SHEET, CONFIG_KINDS):
        if row[0].strip() == project_id:
            return {
                "folderUrl": row[1],
                "nombreBusqueda": row[2],
                "nombreFrecuente": row[4],
                "promptMinuta": row[5].strip() or template,
            }

    return {
        "folderUrl": "",
        "nombreBusqueda": "",
        "nombreFrecuente": "",
        "promptMinuta": template,
    }


def get_config(ctx: AerAiContext, project_value: object) -> JsonObject:
    """obtenerConfigCarpetaMinutasAER()."""
    try:
        project_id = validate_project(ctx.reader, project_value)

        return {"ok": True, "config": read_config(ctx, project_id)}
    except DashboardError as error:
        return {"ok": False, "error": describe_error(error)}


def get_default_prompt(ctx: AerAiContext, project_value: object) -> JsonObject:
    """obtenerPromptMinutaDefectoAER()."""
    try:
        validate_project(ctx.reader, project_value)

        return {"ok": True, "prompt": default_prompt()}
    except DashboardError as error:
        return {"ok": False, "error": describe_error(error)}


def folder_parts(url: object) -> JsonObject:
    """ID y resourcekey de la URL de una carpeta de Drive."""
    value = js_str(url or "").strip()
    match = FOLDER_ID.search(value)

    if not match:
        raise AerAiError(
            "Pega la URL de una carpeta de Google Drive (…/folders/ID).",
        )

    key = RESOURCE_KEY.search(value)

    return {"id": match.group(1), "key": key.group(1) if key else ""}


def text_or(value: object, fallback: str, limit: int) -> str:
    """String(v || fallback).trim().slice(0, limit)."""
    raw = js_str(value) if value else fallback

    return js_slice(raw.strip(), 0, limit)


def ensure_config_sheet(ctx: AerAiContext) -> None:
    """Crea la hoja o corrige los encabezados de las columnas 5 y 6."""
    if not ctx.reader.sheet_exists(CONFIG_SHEET):
        ctx.writer.ensure_sheet(CONFIG_SHEET, CONFIG_HEADERS)
        return

    header = list(ctx.reader.read_values(CONFIG_SHEET)[:1] or [[]])[0]

    for column in (5, 6):
        current = js_str(header[column - 1]) if len(header) >= column else ""

        if current.strip() != CONFIG_HEADERS[column - 1]:
            ctx.writer.write_cell(
                CONFIG_SHEET,
                1,
                column,
                CONFIG_HEADERS[column - 1],
            )


def save_config(
    ctx: AerAiContext,
    project_value: object,
    data: Any,
) -> JsonObject:
    """Guarda carpeta, filtros y plantilla (guardarConfigCarpetaMinutasAER)."""
    try:
        project_id = validate_project(ctx.reader, project_value)
        values = data if isinstance(data, dict) else {}
        folder_url = text_or(values.get("folderUrl"), "", 700)
        search = text_or(values.get("nombreBusqueda"), project_id, 90)
        frequent = text_or(values.get("nombreFrecuente"), "", 100)
        template = (
            text_or(values.get("promptMinuta"), "", 3000) or default_prompt()
        )

        if folder_url:
            folder_parts(folder_url)

        if folder_url and len(search) < 3:
            raise AerAiError(
                "Captura al menos 3 caracteres del nombre o clave del "
                "proyecto.",
            )

        if folder_url and len(frequent) < 2:
            raise AerAiError(
                "Captura el nombre frecuente de los archivos, por ejemplo: "
                "Minuta.",
            )

        with script_lock(10):
            ensure_config_sheet(ctx)
            rows = read_rows(ctx.reader, CONFIG_SHEET, ("",))
            index = next(
                (
                    i
                    for i, row in enumerate(rows)
                    if row[0].strip() == project_id
                ),
                -1,
            )
            row = [
                project_id,
                folder_url,
                search,
                ctx.stamp(),
                frequent,
                template,
            ]

            if index >= 0:
                ctx.writer.write_row(CONFIG_SHEET, index + 2, row)
            else:
                ctx.writer.append_row(CONFIG_SHEET, row)

        return {
            "ok": True,
            "config": {
                "folderUrl": folder_url,
                "nombreBusqueda": search,
                "nombreFrecuente": frequent,
                "promptMinuta": template,
            },
        }
    except DashboardError as error:
        return {"ok": False, "error": describe_error(error)}


def normalize(value: object) -> str:
    """Minusculas sin acentos y solo letras/numeros (_aeri57Norm)."""
    text = unicodedata.normalize("NFD", js_str(value or ""))
    text = "".join(char for char in text if not 0x0300 <= ord(char) <= 0x036F)

    return NON_ALNUM.sub(" ", text.lower()).strip()


def scan_folder(ctx: AerAiContext, project_id: str) -> JsonObject:
    """
    Busca minutas en la carpeta del proyecto (_aeri57Scan).

    Recorre hasta 18 carpetas, 2 niveles y 200 archivos; solo cuenta los
    archivos cuyo nombre contiene alguno de los nombres frecuentes.
    """
    config = read_config(ctx, project_id)

    if not config["folderUrl"]:
        raise AerAiError("Primero configura y guarda el enlace de la carpeta.")

    if len(config["nombreBusqueda"]) < 3:
        raise AerAiError(
            "Configura el nombre del proyecto para filtrar las minutas.",
        )

    if len(config["nombreFrecuente"]) < 2:
        raise AerAiError(
            "Configura el nombre frecuente de los archivos para buscar "
            "minutas.",
        )

    folder_id = folder_parts(config["folderUrl"])["id"]
    root_name = ctx.drive.folder_name(folder_id)
    needle = normalize(config["nombreBusqueda"])
    terms = [
        term
        for term in (
            normalize(part)
            for part in TERM_SPLIT.split(config["nombreFrecuente"])
        )
        if len(term) >= 2
    ]

    if not terms:
        raise AerAiError("Indica al menos un nombre frecuente válido.")

    project_key = normalize(project_id)
    base_key = normalize(project_id.split("_")[0])
    queue = deque([(folder_id, root_name, 0, False)])
    results: list[JsonObject] = []
    examined = folders = 0
    cut = False

    while queue and folders < MAX_FOLDERS and examined < MAX_FILES:
        current_id, name, depth, in_project = queue.popleft()
        folders += 1
        folder_key = normalize(name)
        inside = (
            in_project
            or needle in folder_key
            or project_key in folder_key
            or base_key in folder_key
        )
        children = ctx.drive.list_children(current_id)

        for item in children:
            if item.mime_type == FOLDER_MIME:
                continue

            if examined >= MAX_FILES:
                cut = True
                break

            examined += 1
            file_key = normalize(item.name)
            relevant = (
                inside
                or needle in file_key
                or (len(project_key) > 5 and project_key in file_key)
                or (len(base_key) > 5 and base_key in file_key)
            )

            if not any(term in file_key for term in terms):
                continue

            modified = to_local_naive(item.modified)
            results.append(
                {
                    "id": item.item_id,
                    "nombre": item.name,
                    "url": item.url,
                    "mime": item.mime_type,
                    "legible": item.mime_type in (DOC_MIME, TEXT_MIME),
                    "coincideProyecto": relevant,
                    "resourceKey": "",
                    "fecha": modified.strftime("%Y-%m-%d"),
                },
            )

        if depth < MAX_DEPTH:
            for item in children:
                if folders + len(queue) >= MAX_FOLDERS:
                    break

                if item.mime_type == FOLDER_MIME:
                    queue.append((item.item_id, item.name, depth + 1, inside))

    if queue or examined >= MAX_FILES:
        cut = True

    results.sort(key=lambda item: js_locale_key(item["nombre"]))
    results.sort(key=lambda item: item["fecha"], reverse=True)
    results.sort(key=lambda item: not item["coincideProyecto"])

    return {
        "filas": results[:MAX_RESULTS],
        "totalEncontradas": len(results),
        "examinados": examined,
        "limitado": cut,
        "busqueda": config["nombreBusqueda"],
        "patron": config["nombreFrecuente"],
        "carpeta": root_name,
    }


def search_folder(ctx: AerAiContext, project_value: object) -> JsonObject:
    """buscarMinutasCarpetaAER()."""
    try:
        project_id = validate_project(ctx.reader, project_value)

        return {"ok": True, **scan_folder(ctx, project_id)}
    except DashboardError as error:
        return {"ok": False, "error": describe_error(error)}


def read_file(ctx: AerAiContext, meta: JsonObject) -> str:
    """Texto de un Google Doc o TXT de la carpeta (_aeri57ReadFile)."""
    if meta["mime"] == TEXT_MIME:
        content = ctx.drive.download_text(meta["id"])

        if len(content.encode("utf-8")) > MAX_TEXT_BYTES:
            raise AerAiError(
                f"Archivo de texto demasiado grande: {meta['nombre']}",
            )

        return str(content)

    if meta["mime"] == DOC_MIME:
        return str(ctx.drive.export_document(meta["id"]))

    raise AerAiError(
        "Este tipo de archivo solo permite abrir el vínculo; para extraer "
        f"texto utiliza Google Docs o TXT: {meta['nombre']}",
    )


def draft_from_folder(
    ctx: AerAiContext,
    project_value: object,
    raw_snapshot: Any,
    data: Any,
) -> JsonObject:
    """Borrador de minuta con 1 a 5 archivos de la carpeta y Claude."""
    from apps.aer.services.ai_claude import ask_claude

    try:
        project_id = validate_project(ctx.reader, project_value)
        values = data if isinstance(data, dict) else {}
        ids_value = values.get("ids")
        ids = (
            ["" if item is None else str(item) for item in ids_value]
            if isinstance(ids_value, list)
            else []
        )

        if not ids or len(ids) > 5:
            raise AerAiError(
                "Selecciona entre 1 y 5 minutas de Google Docs/TXT."
            )

        if len(set(ids)) != len(ids):
            raise AerAiError("Hay archivos repetidos en la selección.")

        files = scan_folder(ctx, project_id)["filas"]
        extracted = []

        for number, file_id in enumerate(ids, start=1):
            meta = next((item for item in files if item["id"] == file_id), None)

            if meta is None:
                raise AerAiError(
                    "Una minuta no pertenece a los resultados de esta "
                    "carpeta/proyecto. Busca otra vez.",
                )

            if not meta["legible"]:
                raise AerAiError(
                    "Convierte a Google Docs/TXT para extraer el contenido "
                    f"de: {meta['nombre']}",
                )

            raw = WHITESPACE.sub(" ", read_file(ctx, meta)).strip()

            if not raw:
                raise AerAiError(f"La minuta está vacía: {meta['nombre']}")

            extracted.append(
                f"FUENTE {number} [{clip(meta['nombre'], 95)}, "
                f"{meta['fecha']}]: {js_slice(raw, 0, 1350)}",
            )

        question = (
            f"Tema: {clip(values.get('tema'), 100)}; Fecha: "
            f"{clip(values.get('fecha'), 12)}; Instrucciones/notas: "
            f"{clip(values.get('notas'), 900)}\nMINUTAS SELECCIONADAS:\n"
            + "\n".join(extracted)
        )
        result = ask_claude(
            ctx, "minuta", project_id, raw_snapshot, question, False
        )

        if result.get("ok"):
            result["fuentes"] = len(extracted)
            result["archivos"] = len(ids)

        return result
    except DashboardError as error:
        return {"ok": False, "error": describe_error(error)}
