"""Unfiltered Summary inventory persists independent sprint and CR rows."""

from datetime import date
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
    gateway.create_client.return_value.get_iteration_tree.side_effect = (
        lambda project_id: (
            {
                "name": "General_S2",
                "children": [
                    {
                        "name": "Discovery_S2",
                        "identifier": "dis-s2",
                        "path": "AMK.012/General_S2/Discovery_S2",
                        "attributes": {
                            "startDate": "2026-05-14T00:00:00Z",
                            "finishDate": "2026-05-26T00:00:00Z",
                        },
                    },
                    {
                        "name": "Development_S2",
                        "identifier": "dev-s2",
                        "attributes": {
                            "startDate": "2026-05-27T00:00:00Z",
                            "finishDate": "2026-06-22T00:00:00Z",
                        },
                    },
                    {"name": "Deployment_S2", "attributes": {}},
                ],
            }
            if project_id == "one"
            else {}
        )
    )
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
    assert inventory_rows("s2")[1][0]["iteration_finish"] == "2026-06-22"
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
        response = client.get(
            reverse("portal:summary_inventory"),
            {"q": "S2", "corte": "2026-06-01"},
        )
    assert response.status_code == 200
    assert b"AMK.012_S2" in response.content
    assert b"AMK.012_S1" not in response.content
    assert b'name="q"' in response.content
    assert response["Cache-Control"] == "no-store"


@pytest.mark.parametrize(
    "cut,expected",
    [
        ("2026-05-13", 0),
        ("2026-05-14", 1),
        ("2026-06-22", 1),
        ("2026-06-23", 0),
    ],
)
def test_cut_range_includes_boundaries(inventory, cut, expected):
    assert len(inventory_rows(cut=date.fromisoformat(cut))[1]) == expected


def test_stage_recomputed_for_cut_and_today(inventory):
    assert (
        inventory_rows(cut=date(2026, 5, 15))[1][0]["calendar_stage"]
        == "Discovery"
    )
    assert (
        inventory_rows(cut=date(2026, 6, 1))[1][0]["calendar_stage"]
        == "Development"
    )
    with patch(
        "apps.portal.services.summary_inventory.timezone.localdate",
        return_value=date(2026, 6, 1),
    ):
        assert inventory_rows("S2")[1][0]["calendar_stage"] == "Development"


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


@pytest.mark.parametrize(
    "number,spelling", [(1, "SPRNT"), (2, "SPRNT"), (2, "SPRINT")]
)
def test_local_replay_links_cr_summary_without_provider_calls(
    inventory, number, spelling
):
    source = inventory.evaazuresource_set.get(azure_id="one")
    summary = source.payload["summary"]
    summary["description"] = (
        f"CHANGE REQUEST {number} / {spelling} 1\nDM: Alberto\nService: RaaS\n"
        "Project Name: Asistencia\nBudget: 90\n"
        "Start: 22/12/2025\nFinish: 24/04/2026"
    )
    summary["iteration_tree"] = {
        "name": f"General_CR{number}",
        "children": [
            {
                "name": f"Discovery_CR{number}",
                "attributes": {
                    "startDate": "2025-12-22",
                    "finishDate": "2026-01-02",
                },
            },
            {
                "name": f"Deployment_CR{number}",
                "attributes": {
                    "startDate": "2026-01-28",
                    "finishDate": "2026-04-24",
                },
            },
        ],
    }
    source.save()
    with patch(
        "apps.portal.services.summary_inventory.AzureDevOpsGateway",
        side_effect=AssertionError("external read"),
    ):
        replay = extract_summaries(from_local=True)
    run, rows = inventory_rows("AMK.012", date(2026, 1, 29))
    assert run == replay
    assert len(rows) == 1
    assert rows[0]["display_id"] == f"AMK.012_CR{number}"
    assert rows[0]["summary_scope"] == f"CR{number}_S1"
    assert rows[0]["fields"]["delivery_manager"] == "Alberto"
    assert rows[0]["budget"] == "90"
    assert (
        replay.metrics["source_observed_at"]
        == inventory.metrics["source_observed_at"]
    )
