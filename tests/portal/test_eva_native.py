"""Provider-native EVA allocation, immutable cuts and active route checks."""

from datetime import date, datetime
from unittest.mock import Mock, patch
from zoneinfo import ZoneInfo

import pytest
from django.test import Client
from django.utils import timezone

from apps.clockify.services.clockify_client import ClockifyProject
from apps.datastore.models import (
    EvaAzureSource,
    EvaExtraction,
    EvaScopeSnapshot,
)
from apps.portal.services.eva_azure_source import candidate_rows
from apps.portal.services.eva_native_rows import (
    assign_hours,
    build_row,
    resolve_scope,
    scope_tokens,
)
from apps.portal.services.eva_native_store import load_native_cut, snapshot
from apps.portal.services.eva_native_sync import extract_eva
from apps.portal.services.kpi_native_history import load_kpi_history
from core.exceptions import DashboardError
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


def test_untagged_overlapping_scopes_are_pending():
    first, second = row(), row()
    second["scope"] = "S2"
    assign_hours([first, second], [entry(task="")], CUT)
    assert first["hours_pending"] and second["hours_pending"]
    assert first["burn"] is None


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


def test_compound_cr_requires_exact_tree_evidence():
    candidate = candidate_rows(
        "AMK.012", SUMMARY.replace("Sprint 1", "Change Request 2 / Sprint 1")
    )[0]
    tree = [{"path": "AMK.012\\General_CR2"}]
    assert resolve_scope(candidate, tree, [candidate]) == "CR2"
    first = {**candidate, "scope": "CR1_S1"}
    assert (
        resolve_scope(first, [{"path": "AMK.012\\General_CR"}], [first]) == ""
    )


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


def test_failed_or_subset_runs_cannot_replace_inventory(observed):
    EvaExtraction.objects.create(
        cut=CUT,
        started_at=timezone.now(),
        finished_at=timezone.now(),
        published=False,
    )
    EvaExtraction.objects.create(
        cut=CUT,
        started_at=timezone.now(),
        finished_at=timezone.now(),
        published=True,
        full_inventory=False,
    )
    assert snapshot(CUT)["extraction"].pk == observed.pk
    assert load_native_cut(CUT)["eva"].projects[0].burn == 1


def test_past_date_never_uses_current_azure_snapshot(observed):
    assert snapshot(date(2026, 9, 30))["extraction"] is None


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
        assert "Actualizar fuentes Azure / Clockify" in html
        assert "Summary, iteraciones" in html
        assert 'name="corte"' in html
        assert 'method="get"' in html
        assert "Última extracción:" in html
        assert "Consultando estado de extracción" not in html
        assert "Las cifras reales aparecerán" not in html


def test_kpis_read_same_cut_without_sheets(observed):
    now = datetime(2026, 10, 28, 12, tzinfo=ZoneInfo("America/Mexico_City"))
    with (
        patch(
            "apps.portal.services.kpi_native_history.timezone.localtime",
            return_value=now,
        ),
        patch(
            "requests.sessions.Session.request",
            side_effect=AssertionError("network"),
        ),
    ):
        result = load_kpi_history(2026)
    assert result.history.months[-1].view.totals.total == 1
    assert result.history.months[-1].view.totals.time_cost.cost_percent == 100
    assert "Sin cortes" in result.notice


def test_refresh_csrf_and_local_status(observed):
    client = Client(enforce_csrf_checks=True)
    assert client.get("/api/v1/screens/eva1/extraccion/").status_code == 200
    with patch("apps.portal.api.eva_native.request_refresh") as refresh:
        assert (
            client.post(
                "/api/v1/screens/eva1/extraccion/",
                {},
                content_type="application/json",
            ).status_code
            == 403
        )
    refresh.assert_not_called()


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


def test_extractor_publishes_atomically_and_retains_cut_on_provider_failure(
    db, monkeypatch, settings
):
    settings.CLOCKIFY_WORKSPACE_ID = "workspace"
    settings.CLOCKIFY_API_KEY = "fake"
    monkeypatch.setattr(
        "apps.portal.services.eva_native_sync.timezone.localdate", lambda: CUT
    )
    monkeypatch.setattr(
        "apps.portal.services.eva_native_sync.map_in_parallel",
        lambda fn, values, workers: [fn(v) for v in values],
    )
    azure = Mock()
    azure.list_summary_projects.return_value = [
        {"id": "az", "name": "AMK.012", "description": SUMMARY}
    ]
    azure.list_eva_work_items.return_value = [item()]
    azure.list_iterations.return_value = [{"path": "AMK.012\\General_S1"}]
    gateway = Mock()
    gateway.create_client.return_value = azure
    clock = Mock()
    clock.list_projects.return_value = [ClockifyProject("provider", "AMK.012")]
    clock.fetch_detailed_report_counted.return_value = ([entry()], 1)
    with (
        patch(
            "apps.portal.services.eva_native_sync.AzureDevOpsGateway",
            return_value=gateway,
        ),
        patch(
            "apps.portal.services.eva_native_sync.ClockifyClient",
            return_value=clock,
        ),
    ):
        run = extract_eva()
        assert run.published
        assert run.metrics["clockify_report_requests"] == 1
        assert run.metrics["total_seconds"] >= run.metrics["persist_seconds"]
        assert snapshot(CUT)["rows"][0]["burn"] == 1
        azure.list_eva_work_items.side_effect = DashboardError("offline")
        failed = extract_eva()
    assert not failed.published
    assert snapshot(CUT)["extraction"].pk == run.pk
    assert (
        EvaAzureSource.objects.get(extraction=run).payload["clockify"][
            "provider"
        ][0]["_id"]
        == "e1"
    )


def test_unobserved_monthly_totals_are_pending_not_zero(observed):
    from apps.portal.services.kpi_history import build_matrix
    from apps.portal.services.kpi_quarterly import build_quarter_averages

    now = datetime(2026, 10, 28, 12, tzinfo=ZoneInfo("America/Mexico_City"))
    with patch(
        "apps.portal.services.kpi_native_history.timezone.localtime",
        return_value=now,
    ):
        history = load_kpi_history(2026).history
    matrix = build_matrix(history.months, history.managers)
    assert not history.quarters[0].observed
    assert matrix.totals[0] is None
    assert matrix.totals[-1].total == 1
    quarterly = build_quarter_averages(history.months, history.managers)
    assert quarterly.totals[0] is None
    assert quarterly.totals[-1].total == 1


def test_invalid_range_never_becomes_zero_hours():
    target = row()
    target["fechaInicio"], target["fechaFin"] = "2026-10-31", "2026-10-01"
    assign_hours([target], [], CUT)
    assert target["hours_pending"] and target["burn"] is None


def test_unclassified_summary_skips_unrelated_work_items():
    from apps.portal.services.eva_native_sync import _azure

    client, gateway = Mock(), Mock()
    gateway.create_client.return_value = client
    result = _azure(
        {
            "name": "AMK.012",
            "description": SUMMARY.replace("Service: IxB\n", ""),
        },
        gateway,
        CUT,
    )
    client.list_eva_work_items.assert_not_called()
    client.list_iterations.assert_not_called()
    assert result["rows"][0]["servicio"] == "PENDIENTE"


def test_compound_scope_links_use_exact_resolved_azure_scope():
    from apps.portal.services.eva_native_sync import _azure

    client, gateway = Mock(), Mock()
    gateway.create_client.return_value = client
    client.list_eva_work_items.return_value = [item(scope="CR2")]
    client.list_iterations.return_value = [{"path": "AMK.012\\General_CR2"}]
    result = _azure(
        {
            "name": "AMK.012",
            "description": SUMMARY.replace(
                "Sprint 1", "Change Request 2 / Sprint 1"
            ),
        },
        gateway,
        CUT,
    )
    assert result["rows"][0]["idProyecto"] == "AMK.012_CR2"
    assert result["rows"][0]["summary_scope"] == "CR2_S1"
