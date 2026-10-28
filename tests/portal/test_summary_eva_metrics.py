"""Stored EVA fields, historical hours and honest snapshot availability."""

from datetime import date
from unittest.mock import Mock, patch

import pytest

from apps.portal.services.eva_azure_source import candidate_rows
from apps.portal.services.summary_eva_metrics import at_cut, enrich
from apps.portal.services.summary_inventory import (
    extract_summaries,
    inventory_rows,
)

CUT = date(2026, 10, 28)


def candidate(scope="S1", budget="2"):
    row = candidate_rows("AMK.001", f"Sprint 1\nBudget: {budget}")[0]
    row.update(
        scope=scope,
        iteration_start="2026-10-01",
        iteration_finish="2026-10-31",
        stages=[{"stage": "Discovery"}],
    )
    return row


def item(kind, state, title, scope="S1"):
    return {
        "fields": {
            "System.WorkItemType": kind,
            "System.State": state,
            "System.Title": title,
            "System.IterationPath": (
                f"AMK.001\\General_{scope}\\Discovery_{scope}"
            ),
        }
    }


def entry(key, day, hours, scope="S1"):
    return {
        "id": key,
        "billable": True,
        "taskName": f"Discovery_{scope}",
        "timeInterval": {
            "start": f"2026-10-{day:02}T16:00:00Z",
            "duration": hours * 3600,
        },
    }


def test_counts_risks_and_hours_share_persistable_evidence():
    rows = [candidate()]
    items = [
        item("Task", "Closed", "Done"),
        item("Task", "Active", "Next"),
        item("Risk", "Active", "Risk 1"),
        item("Risk", "Closed", "Old"),
    ]
    records = [entry("a", 2, 1), entry("b", 3, 2)]

    def clock(data, *args, **kwargs):
        assert kwargs["include_all_scopes"]
        data["rows"][0]["clockify_project_id"] = "provider"
        return {**data, "clockify_evidence": {"provider": records}}

    with patch(
        "apps.portal.services.summary_eva_metrics._clockify", side_effect=clock
    ):
        evidence = enrich(rows, {}, items, True, ([], "ws", frozenset()), CUT)
    evidence["observed_date"] = CUT.isoformat()
    at_cut(rows, evidence, CUT)
    metrics = rows[0]["eva_metrics"]
    assert metrics["burn"] == 3
    assert metrics["etc"] == -1
    assert metrics["hoursDeviation"] == -1
    assert metrics["avance"] == 150
    assert metrics["wi"]["discovery"] == {
        "total": 4,
        "cerrados": 2,
        "pendientes": 2,
    }
    assert metrics["wi"]["general"]["total"] == 4
    assert metrics["riesgos"] == ["Risk 1"]
    assert metrics["azure_pending"] is False
    at_cut(rows, evidence, date(2026, 10, 2))
    assert rows[0]["eva_metrics"]["burn"] == 1
    assert rows[0]["eva_metrics"]["azure_pending"] is True
    at_cut(rows, evidence, date(2026, 10, 29))
    assert rows[0]["eva_metrics"]["burn"] is None


def test_transport_failure_does_not_become_zero_counts():
    rows = [candidate()]
    enrich(rows, {}, [], False, None, CUT)
    assert rows[0]["eva_metrics"]["azure_pending"]
    assert rows[0]["eva_metrics"]["burn"] is None


def test_base_counts_exclude_named_sibling_scopes():
    rows = [candidate("BASE")]
    unscoped = item("Task", "Closed", "Base")
    unscoped["fields"]["System.IterationPath"] = "AMK.001\\Discovery"
    enrich(
        rows, {}, [unscoped, item("Task", "Active", "Sibling")], True, None, CUT
    )
    metric = rows[0]["eva_metrics"]
    assert metric["wi"]["discovery"]["total"] == 1
    assert metric["wi"]["general"]["cerrados"] == 1


def test_duplicate_scopes_remain_pending():
    rows = [candidate(), candidate()]
    enrich(rows, {}, [], True, None, CUT)
    assert all(r["eva_metrics"]["azure_pending"] for r in rows)


def test_cr_alias_hours_and_zero_budget():
    row = candidate("CR2", "0")
    row["summary_scope"] = "CR2_S1"
    rows = [row]
    enrich(rows, {}, [], True, None, CUT)
    row["eva_metrics"]["clockify_project_id"] = "provider"
    evidence = {
        "observed_date": CUT.isoformat(),
        "clockify": {"provider": [entry("alias", 2, 3, "CR2_S1")]},
    }
    at_cut(rows, evidence, CUT)
    assert row["eva_metrics"]["burn"] == 3
    assert row["eva_metrics"]["etc"] == -3
    assert row["eva_metrics"]["avance"] is None


def test_dedicated_scope_does_not_absorb_sibling_hours():
    rows = [candidate("S1"), candidate("S2")]
    enrich(rows, {}, [], True, None, CUT)
    for index, row in enumerate(rows):
        row["eva_metrics"].update(
            clockify_project_id=f"provider{index}",
            clockify_dedicated_scope=True,
        )
    record = entry("untagged", 2, 1)
    record["taskName"] = ""
    at_cut(
        rows,
        {
            "observed_date": CUT.isoformat(),
            "clockify": {"provider0": [record], "provider1": []},
        },
        CUT,
    )
    assert rows[0]["eva_metrics"]["burn"] == 1
    assert rows[1]["eva_metrics"]["burn"] == 0


@pytest.mark.django_db
def test_extraction_persists_eva_fields_and_read_has_no_provider_calls():
    gateway = Mock()
    client = gateway.create_client.return_value
    client.list_summary_projects.return_value = [
        {"id": "azure", "name": "AMK.001", "description": "SPRINT 1\nBudget: 2"}
    ]
    client.get_iteration_tree.return_value = {
        "name": "General_S1",
        "children": [
            {
                "name": "Discovery_S1",
                "attributes": {
                    "startDate": "2026-10-01",
                    "finishDate": "2026-10-15",
                },
            },
            {
                "name": "Deployment_S1",
                "attributes": {
                    "startDate": "2026-10-16",
                    "finishDate": "2026-10-31",
                },
            },
        ],
    }
    client.list_eva_work_items.return_value = [item("Task", "Closed", "Done")]

    def clock(data, *args, **kwargs):
        from apps.portal.services.eva_native_rows import assign_hours

        data["rows"][0]["clockify_project_id"] = "provider"
        records = [entry("a", 2, 3)]
        assign_hours(data["rows"], records, CUT)
        return {**data, "clockify_evidence": {"provider": records}}

    with (
        patch(
            "apps.portal.services.summary_inventory.AzureDevOpsGateway",
            return_value=gateway,
        ),
        patch(
            "apps.portal.services.summary_inventory.ClockifyClient"
        ) as clock_client,
        patch(
            "apps.portal.services.summary_inventory.store_state",
            return_value=("stamp", frozenset()),
        ),
        patch(
            "apps.portal.services.summary_inventory.timezone.localdate",
            return_value=CUT,
        ),
        patch(
            "apps.portal.services.summary_eva_metrics._clockify",
            side_effect=clock,
        ),
    ):
        clock_client.return_value.list_projects.return_value = []
        run = extract_summaries()
    client.list_eva_work_items.assert_called_once_with("AMK.001")
    stored = (
        run.evaazuresource_set.get()
        .evascopesnapshot_set.get()
        .row["eva_metrics"]
    )
    assert stored["burn"] == 3
    assert stored["wi"]["general"]["total"] == 1
    with patch(
        "apps.portal.services.summary_inventory.AzureDevOpsGateway",
        side_effect=AssertionError("network"),
    ):
        _, rows = inventory_rows(cut=CUT)
    assert rows[0]["eva_metrics"]["etc"] == -1
    assert rows[0]["eva_metrics"]["azure_pending"] is False
