"""La vista de respuesta elige la plantilla según el tipo de comunicado."""

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

from apps.gmail import views
from apps.gmail.services.credentials_store import StoredCredentials
from tests.gmail.fakes import FakeGmail
from tests.gmail.test_services import ME, project_thread

pytestmark = pytest.mark.django_db
URL = "/gmail/reply/"
BASE = {"project": "MCC.015_S3", "threadId": "19abc123def"}


@pytest.fixture
def api(monkeypatch, settings):
    settings.GMAIL_DELIVERY_MODE = "draft"
    fake = FakeGmail({"19abc123def": project_thread()})
    monkeypatch.setattr(
        views,
        "require_credentials",
        lambda session: StoredCredentials(ME, "token", 9_999_999_999),
    )
    monkeypatch.setattr(views, "GmailApi", lambda token: fake)
    return fake


def test_suspension_is_created_as_a_draft_in_the_thread(client, api):
    response = client.post(
        URL,
        {
            **BASE,
            "kind": "suspension",
            "reason": "Sin accesos.",
            "stage": "Development",
            "resumeDate": "2026-11-02",
            "condition": "la entrega de accesos",
        },
    )

    assert response.status_code == 200
    assert response.json()["result"]["mode"] == "draft"
    assert len(api.drafts) == 1 and api.drafts[0][1] == "19abc123def"


def test_ixb_close_without_mco_is_rejected_and_with_file_is_accepted(
    client, api
):
    data = {**BASE, "kind": "cierre_ixb", "closeDate": "2026-10-15"}

    rejected = client.post(URL, data)
    accepted = client.post(
        URL,
        {**data, "files": SimpleUploadedFile("MCO.pdf", b"%PDF-1.4")},
    )

    assert rejected.status_code == 400
    assert "MCO" in rejected.json()["error"]
    assert accepted.status_code == 200 and len(api.drafts) == 1


def test_default_kind_is_still_the_extension_and_unknown_kinds_fail(
    client, api
):
    extension = client.post(
        URL,
        {
            **BASE,
            "stage": "Deployment",
            "currentDate": "2026-10-07",
            "newDate": "2026-10-09",
            "reason": "Robustecer excepciones.",
            "roadmapLink": "https://drive.google.com/r",
        },
    )
    unknown = client.post(URL, {**BASE, "kind": "otro"})

    assert extension.status_code == 200
    assert unknown.status_code == 400
