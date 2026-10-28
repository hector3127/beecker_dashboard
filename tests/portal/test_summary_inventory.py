"""Unfiltered Summary inventory persists independent sprint and CR rows."""

from unittest.mock import Mock, patch

import pytest
from django.urls import reverse

from apps.datastore.models import EvaExtraction, EvaScopeSnapshot
from apps.portal.services.summary_inventory import (
    extract_summaries,
    inventory_rows,
)


@pytest.fixture
def inventory(db):
    catalog = [
        {
            "id": "one",
            "name": "AMK.012",
            "state": "wellFormed",
            "description": (
                "Sprint 1\nDM: Ana\nService: Other\nBudget: 10\n"
                "Status: Closed\nSprint 2\nBudget: 20\n"
                "Change Request 2\nBudget: 5"
            ),
        },
        {
            "id": "two",
            "name": "Sin codigo",
            "state": "deleted",
            "description": "",
        },
    ]
    gateway = Mock()
    gateway.create_client.return_value.list_summary_projects.return_value = (
        catalog
    )
    with patch(
        "apps.portal.services.summary_inventory.AzureDevOpsGateway",
        return_value=gateway,
    ):
        return extract_summaries()


def test_all_projects_scopes_and_closed_are_preserved(inventory):
    run, rows = inventory_rows()
    assert run == inventory
    assert run.full_inventory is False
    assert run.metrics["projects"] == 2
    assert {r["display_id"] for r in rows} == {
        "AMK.012_S1",
        "AMK.012_S2",
        "AMK.012_CR2",
        "",
    }
    assert inventory_rows("Closed")[1][0]["fields"]["status"] == "Closed"
    assert len(inventory_rows("s2")[1]) == 1
    assert EvaScopeSnapshot.objects.count() == 4
    assert not EvaExtraction.objects.filter(
        published=True, full_inventory=True
    ).exists()


def test_inventory_page_is_local_searchable_and_escaped(
    client, inventory, settings
):
    settings.PORTAL_LOGIN_REQUIRED = False
    with patch(
        "apps.portal.services.summary_inventory.AzureDevOpsGateway",
        side_effect=AssertionError("external read"),
    ):
        response = client.get(reverse("portal:summary_inventory"), {"q": "S2"})
    assert response.status_code == 200
    assert b"AMK.012_S2" in response.content
    assert b"AMK.012_S1" not in response.content
    assert b'name="q"' in response.content
    assert response["Cache-Control"] == "no-store"


def test_failed_transport_keeps_last_inventory(inventory):
    with (
        patch(
            "apps.portal.services.summary_inventory.AzureDevOpsGateway",
            side_effect=RuntimeError("offline"),
        ),
        pytest.raises(RuntimeError),
    ):
        extract_summaries()
    assert inventory_rows()[0] == inventory
