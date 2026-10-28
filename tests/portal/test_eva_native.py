"""Provider-native EVA allocation, immutable cuts and active route checks."""

from datetime import date
from unittest.mock import patch

import pytest
from django.utils import timezone

from apps.datastore.models import (
    EvaAzureSource,
    EvaExtraction,
    EvaScopeSnapshot,
)
from apps.portal.services.eva_azure_source import candidate_rows
from apps.portal.services.inventory_metrics_core import (
    assign_hours,
    build_row,
    scope_tokens,
)
from tests.portal import test_summary_inventory as inventory_fixtures

inventory = inventory_fixtures.inventory

CUT = date(2026, 10, 28)
SUMMARY = (
    "Sprint 1\nDM: Ana\nService: IxB\nProject Name: Demo\n"
    "Start: 2026-10-01\nFinish: 2026-10-31\nBudget: 10"
)


def item(title="General", state="Active", kind="Epic", scope="S1"):
    return {
        "fields": {
            "System.Title": title,
            "System.State": state,
            "System.WorkItemType": kind,
            "System.IterationPath": f"AMK.012\\General_{scope}",
        }
    }


def row():
    return build_row(
        candidate_rows("AMK.012", SUMMARY)[0], "S1", [item()], [], CUT
    )


def entry(
    key="e1",
    task="General_S1",
    seconds=3600,
    billable=True,
    start="2026-10-02T12:00:00Z",
):
    return {
        "_id": key,
        "billable": billable,
        "taskName": task,
        "timeInterval": {"start": start, "duration": seconds},
    }


@pytest.mark.parametrize(
    "text,expected",
    [
        ("General_S1", {"S1"}),
        ("General_S10", {"S10"}),
        ("General_CR2_S1", {"CR2_S1"}),
        ("Discovery_CR2", {"CR2"}),
    ],
)
def test_exact_scope_tokens(text, expected):
    assert scope_tokens(text) == expected


def test_financials_billable_dedup_dates_and_hours_deviation():
    target = row()
    assign_hours(
        [target],
        [
            entry(seconds=72000),
            entry(seconds=72000),
            entry("free", billable=False),
            entry("later", start="2026-11-01T12:00:00Z"),
        ],
        CUT,
    )
    assert target["burn"] == 20
    assert target["etc"] == target["hoursDeviation"] == -10
    assert target["avance"] == 200
    assert not target["hours_pending"]


def test_remaining_is_positive_but_deviation_zero():
    target = row()
    assign_hours([target], [entry()], CUT)
    assert (target["burn"], target["etc"], target["hoursDeviation"]) == (
        1,
        9,
        0,
    )


def test_untagged_overlapping_scopes_with_equal_starts_are_pending():
    first, second = row(), row()
    second["scope"] = "S2"
    assign_hours([first, second], [entry(task="")], CUT)
    assert first["hours_pending"] and second["hours_pending"]
    assert first["burn"] is None


def test_untagged_hours_go_to_earliest_eligible_scope_once():
    later, earlier = row(), row()
    earlier.update(scope="CR2", fechaInicio="2026-09-01")
    records = [
        entry(task=""),
        entry(task=""),
        entry("tagged", task="General_S1"),
    ]
    assign_hours([later, earlier], records, CUT)
    assert earlier["burn"] == 1
    assert later["burn"] == 1
    assert not earlier["hours_pending"] and not later["hours_pending"]


def test_earliest_scope_must_cover_entry_date():
    current, expired = row(), row()
    expired.update(scope="CR2", fechaInicio="2026-09-01", fechaFin="2026-09-30")
    assign_hours([expired, current], [entry(task="")], CUT)
    assert current["burn"] == 1
    assert expired["burn"] == 0


def test_no_sprint_cross_allocation_and_no_double_count():
    first, second = row(), row()
    second["scope"] = "S10"
    assign_hours(
        [first, second],
        [entry(), entry("e2", task="General_S10", seconds=7200)],
        CUT,
    )
    assert (first["burn"], second["burn"]) == (1, 2)


def test_root_closure_not_finish_date_determines_closed():
    c = candidate_rows("AMK.012", SUMMARY)[0]
    assert build_row(c, "S1", [item(state="Closed")], [], CUT)["closed"]
    c["finish"] = "2026-01-01"
    assert not build_row(c, "S1", [item()], [], CUT)["closed"]
    assert (
        build_row(c, "S1", [item(state="Suspended")], [], CUT)["status"]
        == "Suspendido"
    )


def test_only_active_risks_for_scope():
    target = build_row(
        candidate_rows("AMK.012", SUMMARY)[0],
        "S1",
        [
            item(),
            item("Open", kind="Risk"),
            item("Old", state="Closed", kind="Risk"),
            item("Other", kind="Risk", scope="S2"),
        ],
        [],
        CUT,
    )
    assert target["riesgos"] == ["Open"]


@pytest.fixture
def observed(db):
    run = EvaExtraction.objects.create(
        cut=CUT,
        started_at=timezone.now(),
        finished_at=timezone.now(),
        published=True,
        metrics={"total_seconds": 2},
    )
    source = EvaAzureSource.objects.create(
        extraction=run, azure_id="a", name="AMK.012", payload={}
    )
    target = row()
    assign_hours([target], [entry()], CUT)
    EvaScopeSnapshot.objects.create(
        source=source, project_id=target["idProyecto"], scope="S1", row=target
    )
    return run


def test_eva_route_no_sheets_or_provider_http(inventory, client, monkeypatch):
    monkeypatch.setattr(
        "apps.portal.views.timezone.localdate", lambda: date(2026, 6, 1)
    )
    with (
        patch(
            "requests.sessions.Session.request",
            side_effect=AssertionError("network"),
        ),
        patch(
            "core.sheets.factory.build_sheet_repository",
            side_effect=AssertionError("sheet"),
        ),
    ):
        response = client.get("/operativa/eva-1/")
        assert response.status_code == 200
        html = response.content.decode()
        assert "AMK.012_S2" in html
        assert "Actualizar fuentes Azure / Clockify" not in html
        assert "Summary, iteraciones" in html
        assert 'name="corte"' in html
        assert 'method="get"' in html
        assert "Última extracción:" not in html
        assert "Consultando estado de extracción" not in html
        assert "Las cifras reales aparecerán" not in html


def test_partial_cut_notice_is_not_a_connection_error(
    inventory, client, monkeypatch
):
    inventory.issues = ["Summary incompleto"]
    inventory.save(update_fields=["issues"])
    monkeypatch.setattr(
        "apps.portal.views.timezone.localdate", lambda: date(2026, 6, 1)
    )
    response = client.get("/operativa/eva-1/")
    assert response.context["error"] == ""
    assert "incidencias de origen" in response.context["eva_source_notice"]
    html = response.content.decode()
    assert "Las cifras reales aparecerán" not in html
    assert "Fuente no disponible" not in html


def test_invalid_range_never_becomes_zero_hours():
    target = row()
    target["fechaInicio"], target["fechaFin"] = "2026-10-31", "2026-10-01"
    assign_hours([target], [], CUT)
    assert target["hours_pending"] and target["burn"] is None
