from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from googleapiclient.errors import HttpError

from apps.minutas.exceptions import DriveRequestError
from apps.minutas.services.drive_folder import GoogleDriveDocumentSource


def http_error(status):
    return HttpError(SimpleNamespace(status=status, reason="x"), b"{}")


def build_service(pages_by_folder):
    service = MagicMock()

    def list_files(**kwargs):
        folder_id = kwargs["q"].split("'")[1]
        page = int(kwargs["pageToken"] or 0)
        request = MagicMock()
        pages = pages_by_folder[folder_id]
        response = {"files": pages[page]}

        if page + 1 < len(pages):
            response["nextPageToken"] = str(page + 1)

        request.execute.return_value = response
        return request

    service.files.return_value.list.side_effect = list_files
    return service


def item(item_id, mime):
    return {
        "id": item_id,
        "name": item_id,
        "mimeType": mime,
        "createdTime": "2026-10-02T15:00:00Z",
        "webViewLink": f"https://x/{item_id}",
    }


def test_list_documents_walks_pages_and_subfolders():
    doc = "application/vnd.google-apps.document"
    folder = "application/vnd.google-apps.folder"
    service = build_service(
        {
            "root": [
                [item("a", doc), item("sub", folder)],
                [item("b", doc), item("pdf", "application/pdf")],
            ],
            "sub": [[item("c", doc)]],
        },
    )

    documents = GoogleDriveDocumentSource(service).list_documents("root")

    assert [document.document_id for document in documents] == ["a", "b", "c"]
    assert documents[0].created_at.hour == 9


def test_list_documents_reports_permission_errors():
    service = MagicMock()
    service.files.return_value.list.return_value.execute.side_effect = (
        http_error(404)
    )

    with pytest.raises(DriveRequestError, match="cuenta de servicio"):
        GoogleDriveDocumentSource(service).list_documents("root")


def test_export_text_decodes_and_reports_errors():
    service = MagicMock()
    export = service.files.return_value.export.return_value
    export.execute.return_value = b"Hola"

    source = GoogleDriveDocumentSource(service)

    assert source.export_text("a") == "Hola"

    export.execute.side_effect = http_error(403)

    with pytest.raises(DriveRequestError, match="403"):
        source.export_text("a")
