"""Carpetas de Drive de cada proyecto para la IA IXS."""

import json
import re
from collections.abc import Iterator, Sequence
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Protocol

from googleapiclient.errors import HttpError

from apps.daily.services.claude_assist import ClaudeSettings
from apps.daily.services.ixs_store import (
    IxsError,
    IxsStore,
    cell,
    project_id,
    write_lock,
)
from apps.minutas.constants import FOLDER_MIME, GOOGLE_DOC_MIME, TEXT_MIME
from apps.minutas.exceptions import DriveRequestError
from core.exceptions import DashboardError
from core.integrations.claude_client import text_blocks
from core.utils.cell_types import CellValue
from core.utils.dates import to_local_naive
from core.utils.js_values import (
    js_json,
    js_len,
    js_or,
    js_or_text,
    js_slice,
    js_str,
)

"""BKD.070.023 - Drive de la IA IXS
Equivale a ixsIADriveConfigLeer(), ixsIADriveConfigGuardar(),
ixsIADriveConfigQuitar(), ixsIADriveListar(), ixsIADriveLeerDocumento()
e ixsIADriveGenerarMinuta(). Las carpetas se leen con la cuenta de
servicio: cada carpeta debe estar compartida con su correo.
"""

JsonObject = dict[str, Any]

SHEET = "IXS_IA_Carpetas"
HEADERS = ("Proyecto", "Carpeta_ID", "Actualizado")
FOLDER_URL = "https://drive.google.com/drive/folders/"
FOLDER_LINK = re.compile(
    r"^(?:https://drive\.google\.com/drive/(?:u/\d+/)?folders/)?([\w-]{10,})"
    r"(?:[/?#].*)?$",
    re.IGNORECASE | re.ASCII,
)
FILE_ID = re.compile(r"^[\w-]{10,}$", re.ASCII)
MINUTE_NAME = re.compile(
    r"minuta|transcript|reuni[oó]n|seguimiento|comit[eé]|daily",
    re.IGNORECASE,
)
ISO_DAY = re.compile(r"\d{4}-\d{2}-\d{2}", re.ASCII)
MAX_FOLDERS = 12
MAX_FILES = 250
MAX_DEPTH = 3
MAX_QUEUE = 60
MAX_CONTENT = 18000
MAX_TRANSCRIPTS = 5
MAX_TRANSCRIPT_TEXT = 5000
MAX_TOPIC = 150
MAX_NOTES = 2400
MIN_NOTES = 15
MINUTE_TOKENS = 2000
LIST_FIELDS = (
    "nextPageToken, files(id, name, mimeType, webViewLink, modifiedTime)"
)
PAGE_SIZE = 1000
TRANSCRIPTS = "transcripciones"
DOCUMENTS = "documentos"


@dataclass(frozen=True, slots=True)
class DriveItem:
    """Archivo o carpeta de Drive."""

    item_id: str
    name: str
    mime_type: str
    url: str
    modified: datetime


class DriveFolders(Protocol):
    """Acceso a las carpetas de Drive del proyecto."""

    def folder_name(self, folder_id: str) -> str:
        """Nombre de la carpeta (falla si no hay acceso)."""
        ...

    def list_children(self, folder_id: str) -> list[DriveItem]:
        """Archivos y subcarpetas directos de la carpeta."""
        ...

    def export_document(self, file_id: str) -> str:
        """Texto de un Google Doc."""
        ...

    def download_text(self, file_id: str) -> str:
        """Contenido de un archivo de texto."""
        ...


class DriveExportError(DashboardError):
    """La exportacion de un Google Doc respondio con error."""

    code = "ERR_DRIVE_EXPORT"
    expose_detail = True

    def __init__(self, status: int) -> None:
        super().__init__(
            f"No se pudo exportar el documento de Drive (HTTP {status}). "
            "Comprueba el acceso a la carpeta y vuelve a autorizar el "
            "despliegue si cambiaste sus permisos.",
        )


class GoogleDriveFolders:
    """Implementacion con la API de Drive v3 y la cuenta de servicio."""

    def __init__(self, service: Any) -> None:
        self._service = service

    def folder_name(self, folder_id: str) -> str:
        """Nombre de la carpeta, como DriveApp.getFolderById(id).getName()."""
        try:
            item = (
                self._service.files()
                .get(fileId=folder_id, fields="name", supportsAllDrives=True)
                .execute()
            )
        except HttpError as error:
            raise DriveRequestError(
                f"Drive respondió {error.resp.status} al abrir la carpeta "
                f"{folder_id}. Compártela con la cuenta de servicio.",
            ) from error

        return str(item.get("name") or "")

    def list_children(self, folder_id: str) -> list[DriveItem]:
        """Hijos de la carpeta (todas las paginas)."""
        return [build_item(item) for item in self._pages(folder_id)]

    def export_document(self, file_id: str) -> str:
        """Exporta un Google Doc como texto plano."""
        try:
            content = (
                self._service.files()
                .export(fileId=file_id, mimeType=TEXT_MIME)
                .execute()
            )
        except HttpError as error:
            raise DriveExportError(error.resp.status) from error

        return decode(content)

    def download_text(self, file_id: str) -> str:
        """Descarga un archivo text/plain."""
        try:
            content = (
                self._service.files()
                .get_media(fileId=file_id, supportsAllDrives=True)
                .execute()
            )
        except HttpError as error:
            raise DriveRequestError(
                f"Drive respondió {error.resp.status} al leer el archivo.",
            ) from error

        return decode(content)

    def _pages(self, folder_id: str) -> Iterator[dict[str, Any]]:
        page_token: str | None = None

        while True:
            try:
                response = (
                    self._service.files()
                    .list(
                        q=f"'{folder_id}' in parents and trashed=false",
                        fields=LIST_FIELDS,
                        pageSize=PAGE_SIZE,
                        pageToken=page_token,
                        supportsAllDrives=True,
                        includeItemsFromAllDrives=True,
                    )
                    .execute()
                )
            except HttpError as error:
                raise DriveRequestError(
                    f"Drive respondió {error.resp.status} al leer la carpeta "
                    f"{folder_id}. Compártela con la cuenta de servicio.",
                ) from error

            yield from response.get("files", [])
            page_token = response.get("nextPageToken")

            if not page_token:
                return


def decode(content: object) -> str:
    """Bytes de Drive a texto UTF-8."""
    if isinstance(content, bytes):
        return content.decode("utf-8", errors="replace")

    return str(content)


def build_item(item: dict[str, Any]) -> DriveItem:
    """Archivo de la API como DriveItem."""
    modified = datetime.fromisoformat(
        str(item.get("modifiedTime") or "1970-01-01T00:00:00Z").replace(
            "Z",
            "+00:00",
        ),
    )

    return DriveItem(
        item_id=str(item.get("id")),
        name=str(item.get("name") or ""),
        mime_type=str(item.get("mimeType") or ""),
        url=str(item.get("webViewLink") or ""),
        modified=modified,
    )


@dataclass(slots=True)
class DriveContext:
    """Hojas, Drive y archivos ya recorridos en esta peticion."""

    store: IxsStore
    drive: DriveFolders
    scanned: dict[str, list[DriveItem]] = field(default_factory=dict)

    def files(self, folder_id: str) -> list[DriveItem]:
        """
        Archivos de la carpeta y subcarpetas (ixsIADriveArchivos_).

        Recorre a lo ancho hasta 3 niveles, 60 carpetas en cola y 250
        archivos.
        """
        if folder_id not in self.scanned:
            self.scanned[folder_id] = self._scan(folder_id)

        return self.scanned[folder_id]

    def _scan(self, folder_id: str) -> list[DriveItem]:
        queue: list[tuple[str, int]] = [(folder_id, 0)]
        files: list[DriveItem] = []

        while queue and len(files) < MAX_FILES:
            current, depth = queue.pop(0)
            children = self.drive.list_children(current)

            for child in children:
                if child.mime_type != FOLDER_MIME and len(files) < MAX_FILES:
                    files.append(child)

            if depth < MAX_DEPTH:
                for child in children:
                    if (
                        child.mime_type == FOLDER_MIME
                        and len(queue) < MAX_QUEUE
                    ):
                        queue.append((child.item_id, depth + 1))

        return files


@dataclass(frozen=True, slots=True)
class FolderRow:
    """Fila de IXS_IA_Carpetas del proyecto (0 si no existe)."""

    row: int
    documents: list[str]
    transcripts: list[str]


def parse_ids(value: CellValue) -> list[str]:
    """Lista JSON de IDs de carpeta validos."""
    try:
        data = json.loads(js_or_text(value) or "[]")
    except ValueError:
        return []

    if not isinstance(data, list):
        return []

    return [item for item in data if FILE_ID.match(js_str(item))]


def folder_row(store: IxsStore, project: str) -> FolderRow:
    """Carpetas del proyecto (ixsIADriveFila_)."""
    store.writer.ensure_sheet(SHEET, HEADERS)
    rows = store.values(SHEET)[1:]
    index = next(
        (
            position
            for position, row in enumerate(rows)
            if js_str(cell(row, 0)) == project
        ),
        -1,
    )

    if index < 0:
        return FolderRow(0, [], [])

    raw = js_or_text(cell(rows[index], 1))
    documents = parse_ids(raw) if raw.startswith("[") else [raw] if raw else []

    return FolderRow(index + 2, documents, parse_ids(cell(rows[index], 3)))


def read_config(store: IxsStore, project_value: object) -> JsonObject:
    """
    Carpetas conectadas del proyecto (ixsIADriveConfigLeer).

    Returns:
        {"ok", "carpetas", "transcripciones", "folderId", "url"}.
    """
    try:
        project = project_id(project_value)
        folders = folder_row(store, project)
    except DashboardError as error:
        return {"ok": False, "error": error.detail}

    first = folders.documents[0] if folders.documents else ""

    return {
        "ok": True,
        "carpetas": folders.documents,
        "transcripciones": folders.transcripts,
        "folderId": first,
        "url": f"{FOLDER_URL}{first}" if first else "",
    }


def folder_kind(value: object) -> str:
    """'transcripciones' o 'documentos'."""
    return TRANSCRIPTS if value == TRANSCRIPTS else DOCUMENTS


def write_folders(
    store: IxsStore,
    project: str,
    folders: FolderRow,
) -> None:
    """Escribe o agrega la fila del proyecto."""
    values: list[CellValue | datetime] = [
        project,
        js_json(folders.documents),
        store.now,
        js_json(folders.transcripts),
    ]

    if folders.row:
        store.writer.write_row(SHEET, folders.row, values)
    else:
        store.writer.append_row(SHEET, values)


def save_folder(
    context: DriveContext,
    project_value: object,
    url_value: object,
    kind_value: object,
) -> JsonObject:
    """
    Conecta una carpeta de Drive al proyecto (ixsIADriveConfigGuardar).

    Returns:
        {"ok", "nombre", "carpetas", "transcripciones"}.
    """
    try:
        with write_lock():
            project = project_id(project_value)
            url = js_or_text(url_value).strip()
            kind = folder_kind(kind_value)
            match = FOLDER_LINK.match(url)

            if not match:
                raise IxsError(
                    "Pega el vínculo de una carpeta de Google Drive válida.",
                )

            folder_id = match.group(1)
            name = context.drive.folder_name(folder_id)
            folders = folder_row(context.store, project)
            selected = (
                folders.transcripts
                if kind == TRANSCRIPTS
                else folders.documents
            )

            if folder_id not in selected:
                selected.append(folder_id)

            if len(selected) > MAX_FOLDERS:
                raise IxsError(
                    "Se permiten hasta 12 carpetas de cada tipo por proyecto.",
                )

            write_folders(context.store, project, folders)
    except DashboardError as error:
        return {
            "ok": False,
            "error": f"No se pudo conectar la carpeta: {error.detail}",
        }

    return {
        "ok": True,
        "nombre": name,
        "carpetas": folders.documents,
        "transcripciones": folders.transcripts,
    }


def remove_folder(
    store: IxsStore,
    project_value: object,
    folder_value: object,
    kind_value: object,
) -> JsonObject:
    """
    Desconecta una carpeta del proyecto (ixsIADriveConfigQuitar).

    Returns:
        Las carpetas que quedan.
    """
    try:
        with write_lock():
            project = project_id(project_value)
            kind = folder_kind(kind_value)
            folders = folder_row(store, project)

            if not folders.row:
                return {"ok": False, "error": "No hay carpetas configuradas."}

            wanted = js_str(folder_value)
            documents = folders.documents
            transcripts = folders.transcripts

            if kind == TRANSCRIPTS:
                transcripts = [item for item in transcripts if item != wanted]
            else:
                documents = [item for item in documents if item != wanted]

            write_folders(
                store,
                project,
                FolderRow(folders.row, documents, transcripts),
            )
    except DashboardError as error:
        return {"ok": False, "error": error.detail}

    return read_config(store, project)


def describe_file(item: DriveItem, folder_id: str, kind: str) -> JsonObject:
    """Archivo como lo regresaba ixsIADriveListar()."""
    return {
        "id": item.item_id,
        "nombre": item.name,
        "mime": item.mime_type,
        "url": item.url,
        "carpeta": folder_id,
        "tipo": kind,
        "fecha": to_local_naive(item.modified).strftime("%Y-%m-%d"),
        "legible": item.mime_type in (GOOGLE_DOC_MIME, TEXT_MIME),
        "minuta": kind == TRANSCRIPTS or bool(MINUTE_NAME.search(item.name)),
    }


def list_files(context: DriveContext, project_value: object) -> JsonObject:
    """
    Archivos de las carpetas conectadas, del mas reciente al mas antiguo.

    Returns:
        {"ok", "configured", "files", "limited"}.
    """
    try:
        project = project_id(project_value)
        folders = folder_row(context.store, project)
        sources = [(folder, TRANSCRIPTS) for folder in folders.transcripts] + [
            (folder, DOCUMENTS) for folder in folders.documents
        ]
        seen: set[str] = set()
        files: list[JsonObject] = []

        for folder_id, kind in sources:
            for item in context.files(folder_id):
                if item.item_id in seen:
                    continue

                seen.add(item.item_id)
                files.append(describe_file(item, folder_id, kind))
    except DashboardError as error:
        return {
            "ok": False,
            "error": "No se pudieron leer los documentos de Drive: "
            f"{error.detail}",
        }

    files.sort(key=lambda file: str(file["fecha"]), reverse=True)

    return {
        "ok": True,
        "configured": bool(sources),
        "files": files,
        "limited": len(files) >= MAX_FILES,
    }


def read_document(
    context: DriveContext,
    project_value: object,
    file_value: object,
) -> JsonObject:
    """
    Texto de un archivo de las carpetas conectadas (ixsIADriveLeerDocumento).

    Returns:
        {"ok", "nombre", "fecha", "contenido", "url", "truncado"}.
    """
    try:
        project = project_id(project_value)
        file_id = js_or_text(file_value)

        if not FILE_ID.match(file_id):
            raise IxsError("Archivo inválido.")

        folders = folder_row(context.store, project)
        folder_ids = folders.documents + folders.transcripts

        if not folder_ids:
            raise IxsError("Conecta primero una carpeta para este proyecto.")

        item = next(
            (
                file
                for folder_id in folder_ids
                for file in context.files(folder_id)
                if file.item_id == file_id
            ),
            None,
        )

        if item is None:
            raise IxsError("El archivo no pertenece a las carpetas conectadas.")

        if item.mime_type == GOOGLE_DOC_MIME:
            content = context.drive.export_document(file_id)
        elif item.mime_type == TEXT_MIME:
            content = context.drive.download_text(file_id)
        else:
            raise IxsError(
                "Este formato se puede abrir en Drive, pero no extraer como "
                "texto. Usa Google Docs o TXT.",
            )
    except DashboardError as error:
        return {"ok": False, "error": error.detail}

    return {
        "ok": True,
        "nombre": item.name,
        "fecha": to_local_naive(item.modified).strftime("%Y-%m-%d"),
        "contenido": js_slice(content, 0, MAX_CONTENT),
        "url": item.url,
        "truncado": js_len(content) > MAX_CONTENT,
    }


def generate_minute(
    settings: ClaudeSettings,
    context: DriveContext,
    request: tuple[object, object, object, object, object],
) -> JsonObject:
    """
    Borrador de minuta con transcripciones y apuntes (ixsIADriveGenerarMinuta).

    Args:
        settings: Configuracion de Claude.
        context: Hojas y Drive.
        request: ID, IDs de transcripciones, tema, fecha y apuntes.

    Returns:
        {"ok", "texto", "fuentes"} o {"ok": False, "error"}.
    """
    try:
        return build_minute(settings, context, request)
    except DashboardError as error:
        return {"ok": False, "error": error.detail}
    except ValueError as error:
        return {"ok": False, "error": str(error)}


def build_minute(
    settings: ClaudeSettings,
    context: DriveContext,
    request: tuple[object, object, object, object, object],
) -> JsonObject:
    """Cuerpo de generate_minute; los errores se convierten afuera."""
    project_value, files_value, topic_value, date_value, notes_value = request
    project = project_id(project_value)
    file_ids: Sequence[Any] = (
        files_value if isinstance(files_value, list) else []
    )

    if len(file_ids) > MAX_TRANSCRIPTS or len(
        {js_json(item) for item in file_ids},
    ) != len(file_ids):
        raise IxsError(
            "Selecciona como máximo cinco transcripciones diferentes."
        )

    topic = js_slice(js_str(js_or(topic_value, "Seguimiento")), 0, MAX_TOPIC)
    day = js_or_text(date_value)
    notes = js_slice(js_or_text(notes_value).strip(), 0, MAX_NOTES)

    if not ISO_DAY.fullmatch(day):
        raise IxsError("Indica la fecha de la reunión.")

    if not file_ids and js_len(notes) < MIN_NOTES:
        raise IxsError(
            "Selecciona transcripciones o escribe al menos 15 caracteres de "
            "apuntes.",
        )

    listing = list_files(context, project)

    if not listing["ok"]:
        raise IxsError(str(listing["error"]))

    allowed = [
        file["id"]
        for file in listing["files"]
        if file["tipo"] == TRANSCRIPTS and file["legible"]
    ]

    if any(item not in allowed for item in file_ids):
        raise IxsError(
            "Selecciona únicamente transcripciones legibles de las carpetas "
            "vinculadas.",
        )

    texts = []

    for file_id in file_ids:
        document = read_document(context, project, file_id)

        if not document["ok"]:
            raise IxsError(str(document["error"]))

        texts.append(
            {
                "nombre": document["nombre"],
                "texto": js_slice(
                    document["contenido"], 0, MAX_TRANSCRIPT_TEXT
                ),
            },
        )

    if not settings.api_key:
        raise IxsError(
            "Configura tu API key de Claude para generar el borrador."
        )

    prompt = (
        f"Redacta en español una minuta editable del proyecto {project} con "
        f"tema {topic} y fecha {day}. Usa EXCLUSIVAMENTE los apuntes y las "
        "transcripciones adjuntas. Cita el nombre de la transcripción junto a "
        "acuerdos y pendientes. No inventes asistentes, acuerdos, responsables "
        "ni fechas; omite lo que no conste. Estructura: resumen, acuerdos, "
        "pendientes, responsables y próximos pasos solo cuando estén "
        f"documentados.\nApuntes: {notes}\nTranscripciones: {js_json(texts)}"
    )
    response = settings.build_client().create_message(
        {
            "model": settings.model,
            "max_tokens": MINUTE_TOKENS,
            "temperature": 0,
            "messages": [{"role": "user", "content": prompt}],
        },
    )

    if response.status_code >= 300:
        raise IxsError(
            f"Claude respondió {response.status_code}: "
            f"{js_slice(response.body, 0, 140)}",
        )

    data = response.json()

    if data.get("stop_reason") == "max_tokens":
        raise IxsError(
            "La respuesta se interrumpió; reduce la selección e inténtalo de "
            "nuevo.",
        )

    text = "\n".join(text_blocks(data)).strip()

    if not text:
        raise IxsError("Claude no devolvió contenido.")

    return {
        "ok": True,
        "texto": js_slice(text, 0, MAX_CONTENT),
        "fuentes": [item["nombre"] for item in texts],
    }
