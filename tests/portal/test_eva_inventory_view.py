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
    assert (
        client.get(
            "/operativa/eva-1/", {"corte": "2026-06-01", "manager": "Other"}
        )
        .context["eva"]
        .total_projects
        == 0
    )


def test_refresh_updates_same_inventory_and_history():
    from contextlib import contextmanager

    from apps.portal.services.eva_native_refresh import _refresh

    @contextmanager
    def acquired(*args):
        yield True

    with (
        patch("apps.portal.services.eva_native_refresh.close_old_connections"),
        patch("apps.portal.services.eva_native_refresh.sync_lock", acquired),
        patch(
            "apps.portal.services.eva_native_refresh.download_history"
        ) as history,
        patch(
            "apps.portal.services.eva_native_refresh.extract_summaries"
        ) as extract,
    ):
        _refresh()
    history.assert_called_once()
    extract.assert_called_once()
