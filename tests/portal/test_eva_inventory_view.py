"""Approved EVA presentation reads exactly the new inventory selection."""

from datetime import date
from unittest.mock import patch

from apps.portal.services.eva_inventory_view import load_inventory_eva
from apps.portal.services.summary_inventory import inventory_rows
from tests.portal import test_summary_inventory as fixtures

inventory = fixtures.inventory


def test_inventory_adapter_matches_detail_and_pivots(inventory):
    cut = date(2026, 6, 1)
    _, rows = inventory_rows(cut=cut)
    result = load_inventory_eva(cut)
    assert result["eva"].total_projects == len(rows) == 1
    project = result["eva"].projects[0]
    assert project.project_id == "AMK.012_S2"
    assert project.status == "Development"
    assert project.start == "14/05/26"
    assert project.end == "22/06/26"
    assert project.budget == 20
    assert project.hours_pending
    assert load_inventory_eva(date(2026, 6, 23))["eva"].total_projects == 0


def test_active_eva_filters_and_source_are_local(client, settings, inventory):
    settings.PORTAL_LOGIN_REQUIRED = False
    with patch(
        "requests.sessions.Session.request",
        side_effect=AssertionError("external read"),
    ):
        response = client.get("/operativa/eva-1/", {"corte": "2026-06-01"})
    assert response.status_code == 200
    assert response.context["eva"].total_projects == 1
    assert response.context["inventory_totals"]["total"] == 1
    assert response.context["eva"].projects[0].project_id == "AMK.012_S2"
    assert b'class="service-pill' in response.content
    assert b'id="eva-extract"' not in response.content
    assert b"Ver inventario de Summary" not in response.content
    assert response.context["eva_card_metrics"]["time_percent"] == 100
    assert (
        client.get(
            "/operativa/eva-1/", {"corte": "2026-06-01", "manager": "Other"}
        )
        .context["eva"]
        .total_projects
        == 0
    )


def test_cards_use_visible_total_of_22(client, settings, db):
    from apps.portal.services.eva2 import build_eva2_view
    from tests.portal.test_eva2 import make_row

    rows = [
        make_row(
            idProyecto=f"P{i}",
            desviacionDias=-1 if i < 18 else 1,
            avance=90 if i < 15 else 110,
            budget=100,
            budget_pending=False,
            hours_pending=False,
        )
        for i in range(22)
    ]
    settings.PORTAL_LOGIN_REQUIRED = False
    with patch(
        "apps.portal.services.eva_inventory_view.load_inventory_eva",
        return_value={
            "eva": build_eva2_view(rows),
            "projected_rows": rows,
            "inventory_rows": [],
            "extraction": None,
            "error": "",
        },
    ):
        response = client.get("/operativa/eva-1/")
    total = response.context["eva_card_metrics"]
    assert total["total"] == 22
    assert total["time_percent"] == 100 * 18 / 22
    assert total["cost_percent"] == 100 * 7 / 22


def test_cards_count_11_projects_with_five_over_budget_and_one_pending(
    client, settings, db
):
    from apps.portal.services.eva2 import build_eva2_view
    from tests.portal.test_eva2 import make_row

    rows = [
        make_row(
            idProyecto=f"P{i}",
            desviacionDias=-1 if i < 10 else 0,
            avance=110 if i < 5 else 100,
            budget=100,
            hours_pending=i == 10,
            progress_pending=i == 10,
            automatic_entries=2 if i == 0 else 0,
            automatic_hours=0.5 if i == 0 else 0,
        )
        for i in range(11)
    ]
    settings.PORTAL_LOGIN_REQUIRED = False
    with patch(
        "apps.portal.services.eva_inventory_view.load_inventory_eva",
        return_value={
            "eva": build_eva2_view(rows),
            "projected_rows": rows,
            "inventory_rows": [],
            "extraction": None,
            "error": "",
        },
    ):
        response = client.get("/operativa/eva-1/")
    metrics = response.context["eva_card_metrics"]
    assert metrics == {
        "total": 11,
        "in_time": 11,
        "over_budget": 5,
        "time_percent": 100,
        "cost_percent": 100 * 5 / 11,
    }
    assert response.context["eva_cost_pending"] == 1
    assert b"45.5%" in response.content
    assert b"5/11" in response.content
    assert response.content.count(b'class="eva-allocation-note"') == 1
    assert b"0.50 h sin tarea/tag" in response.content
