"""Account follow-up and the global history share persistent agreements."""

import pytest
from django.urls import reverse

from apps.portal.models import ExecutiveAgreement

pytestmark = pytest.mark.django_db


def test_account_view_filters_aliases_and_completed_agreements(client):
    opened = ExecutiveAgreement.objects.create(account="Heineken", title="A")
    ExecutiveAgreement.objects.create(
        account="Heineken", title="B", status="done"
    )
    ExecutiveAgreement.objects.create(account="Other", title="C")
    rows = client.get(
        reverse("portal:acuerdos_ejecutivos"),
        {"account": "Heineken Mexico", "pending_only": "1"},
    ).json()["items"]
    assert [row["id"] for row in rows] == [opened.pk]


def test_completing_an_account_item_keeps_it_in_global_history(client):
    item = ExecutiveAgreement.objects.create(
        account="Cuenta A", title="Revisar", notes="Conservar seguimiento"
    )
    url = reverse("portal:acuerdos_ejecutivos")
    response = client.post(
        url + "?account=Cuenta%20A&pending_only=1",
        {"action": "status", "id": item.pk, "status": "done"},
    )
    assert response.status_code == 200
    assert response.json()["items"] == []
    saved = client.get(url).json()["items"][0]
    assert saved["status"] == "done"
    assert saved["notes"] == "Conservar seguimiento"


def test_account_request_cannot_change_another_accounts_item(client):
    item = ExecutiveAgreement.objects.create(account="Other", title="Otro")
    response = client.post(
        reverse("portal:acuerdos_ejecutivos") + "?account=Cuenta%20A",
        {"action": "status", "id": item.pk, "status": "done"},
    )
    assert response.status_code == 404
    item.refresh_from_db()
    assert item.status == "open"


@pytest.mark.parametrize("status", ["invalid", "", "closed"])
def test_quick_status_change_rejects_invalid_states(client, status):
    item = ExecutiveAgreement.objects.create(account="A", title="Revisar")
    response = client.post(
        reverse("portal:acuerdos_ejecutivos"),
        {"action": "status", "id": item.pk, "status": status},
    )
    assert response.status_code == 400
    item.refresh_from_db()
    assert item.status == "open"


def test_account_create_ignores_posted_account_outside_scope(client):
    response = client.post(
        reverse("portal:acuerdos_ejecutivos") + "?account=Cuenta%20A",
        {
            "account": "Other",
            "title": "Nuevo",
            "kind": "pending",
            "status": "open",
        },
    )
    assert response.status_code == 200
    assert response.json()["items"][0]["account"] == "Cuenta A"
