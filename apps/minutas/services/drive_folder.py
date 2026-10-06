"""Lectura de la carpeta de minutas en Google Drive."""

import logging
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Protocol

from googleapiclient.errors import HttpError

from apps.minutas.constants import FOLDER_MIME, GOOGLE_DOC_MIME, TEXT_MIME
from apps.minutas.exceptions import DriveRequestError
from core.utils.dates import to_local_naive

"""BKD.060.005 - Carpeta de Drive
Equivale a DriveApp.getFolderById(), recorrerCarpeta() y
exportarDocComoTexto(): recorre la carpeta y sus subcarpetas y exporta
cada Google Doc a texto plano con la cuenta de servicio.
"""

logger = logging.getLogger(__name__)

LIST_FIELDS = (
    "nextPageToken, files(id, name, mimeType, createdTime, webViewLink)"
)
PAGE_SIZE = 1000


@dataclass(frozen=True, slots=True)
class DriveDocument:
    """Google Doc encontrado en la carpeta."""

    document_id: str
    name: str
    created_at: datetime
    url: str


class DocumentSource(Protocol):
    """Acceso a los documentos de la carpeta de minutas."""

    def list_documents(self, folder_id: str) -> list[DriveDocument]:
        """Lista los Google Docs de la carpeta y sus subcarpetas."""
        ...

    def export_text(self, document_id: str) -> str:
        """Exporta un Google Doc a texto plano."""
        ...


class GoogleDriveDocumentSource:
    """Implementacion con la API de Google Drive v3."""

    def __init__(self, service: Any) -> None:
        self._service = service

    def list_documents(self, folder_id: str) -> list[DriveDocument]:
        """
        Lista los Google Docs de la carpeta y de todas sus subcarpetas.

        Args:
            folder_id: ID de la carpeta raiz.

        Returns:
            Los documentos con fecha de creacion en hora local.

        Raises:
            DriveRequestError: Cuando Drive rechaza la consulta.
        """
        documents: list[DriveDocument] = []
        subfolders: list[str] = []

        for item in self._list_children(folder_id):
            mime_type = item.get("mimeType")

            if mime_type == GOOGLE_DOC_MIME:
                documents.append(build_document(item))
            elif mime_type == FOLDER_MIME:
                subfolders.append(str(item.get("id")))

        for subfolder_id in subfolders:
            documents.extend(self.list_documents(subfolder_id))

        return documents

    def export_text(self, document_id: str) -> str:
        """
        Exporta un Google Doc a texto plano.

        Args:
            document_id: ID del documento.

        Returns:
            El texto del documento.

        Raises:
            DriveRequestError: Cuando la exportacion falla.
        """
        try:
            content = (
                self._service.files()
                .export(fileId=document_id, mimeType=TEXT_MIME)
                .execute()
            )
        except HttpError as error:
            raise DriveRequestError(
                f"Export fallo con status {error.resp.status}",
            ) from error

        if isinstance(content, bytes):
            return content.decode("utf-8")

        return str(content)

    def _list_children(self, folder_id: str) -> Iterator[dict[str, Any]]:
        """Recorre todas las paginas de hijos de una carpeta."""
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
                    f"Drive respondio {error.resp.status} al leer la carpeta "
                    f"{folder_id}. Compartela con la cuenta de servicio.",
                ) from error

            yield from response.get("files", [])
            page_token = response.get("nextPageToken")

            if not page_token:
                return


def build_document(item: dict[str, Any]) -> DriveDocument:
    """
    Convierte un archivo de la API en documento.

    Args:
        item: Archivo como lo regresa files.list.

    Returns:
        El documento con fecha local.
    """
    created_at = datetime.fromisoformat(
        str(item.get("createdTime", "")).replace("Z", "+00:00"),
    )

    return DriveDocument(
        document_id=str(item.get("id")),
        name=str(item.get("name") or ""),
        created_at=to_local_naive(created_at),
        url=str(item.get("webViewLink") or ""),
    )
