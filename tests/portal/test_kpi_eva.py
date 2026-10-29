"""Business rules confirmed for DM compliance against EVA 1."""

from datetime import date, datetime

import pytest

from apps.portal.services.eva_cut import cut_rows
from apps.portal.services.kpi_eva import (
    build_eva_history,
    compliance_view,
    monthly_cuts,
)
from tests.portal.test_eva_cut import event


@pytest.mark.parametrize(
    "year,month,day",
    [
        (2026, 1, 29),
        (2026, 2, 26),
        (2026, 5, 28),
        (2026, 8, 31),
        (2026, 9, 30),
        (2026, 12, 31),
    ],
)
def test_last_monday_through_thursday(year, month, day):
    cuts = monthly_cuts(year, date(2027, 1, 10))
    assert cuts[month - 1][1] == date(year, month, day)
    assert all(cut.weekday() < 4 for _, cut, _ in cuts)
    assert not any(partial for _, _, partial in cuts)


def test_current_friday_cut_is_previous_thursday_and_partial():
    cuts = monthly_cuts(2026, date(2026, 10, 23))
    assert cuts[-1] == ("2026-10", date(2026, 10, 22), True)
    assert monthly_cuts(2027, date(2026, 10, 23)) == []
    assert monthly_cuts(2026, date(2026, 5, 1))[-1][0] == "2026-04"


def row(pid, dm, deviation, advance, **flags):
    return {
        "idProyecto": pid,
        "deliveryManager": dm,
        "desviacionDias": deviation,
        "budget": 100,
        "avance": advance,
        **flags,
    }


def stub_compliance_history(monkeypatch, today):
    from apps.portal.services.kpi_history_loader import KpiHistoryLoad

    history = build_eva_history(
        today.year,
        datetime.combine(today, datetime.min.time()),
        lambda cut: [
            row("A", "Ana", -1, 50),
            row("B", "Ana", 2, 150),
            row("C", "Beto", 0, 100),
        ],
    )
    monkeypatch.setattr(
        "apps.portal.views.load_kpi_history",
        lambda *args: KpiHistoryLoad(history),
    )
    return history


def test_percentages_count_compliant_projects_not_average_their_values():
    view = compliance_view(
        [
            row("A", "DM", -40, 20),
            row("B", "DM", 0, 100),
            row("C", "DM", 10, 101),
            row("D", "DM", -1, 200),
            row("E", "DM", 5, 50),
            row("F", "DM", -2, 150),
        ]
    )
    assert view.totals.total == 6
    assert view.totals.time_cost.time_days == pytest.approx(100 * 4 / 6)
    assert view.totals.time_cost.cost_percent == 50
    assert view.totals.time_late == 2
    assert view.totals.cost_over == 3


def test_totals_use_all_projects_not_mean_of_manager_percentages():
    view = compliance_view(
        [
            row("A", "DM1", -1, 10),
            *[row(str(i), "DM2", 5, 150) for i in range(3)],
        ]
    )
    assert (
        view.totals.time_cost.time_days
        == view.totals.time_cost.cost_percent
        == 25
    )
    assert view.best.name == "DM1"


def test_missing_values_leave_metric_pending_without_reducing_tp():
    view = compliance_view(
        [row("A", "DM", None, 0, hours_pending=True), row("B", "DM", -1, 0)]
    )
    assert view.totals.total == 2
    assert view.totals.time_cost.time_days is None
    assert view.totals.time_cost.cost_percent is None
    assert compliance_view([]).totals.time_cost.cost_percent is None


def test_monthly_inventory_is_same_as_eva1_cut_with_suspended_and_closed():
    events = [
        event("A", "Deployment", "2025-01-01", "2026-01-30"),
        event("B", "Discovery", "2025-01-01"),
        event("B", "Suspendido", "2025-09-01"),
        event("C", "Discovery", "2025-01-01"),
        event("C", "Completed", "2026-01-29"),
        event("D", "Discovery", "2026-01-30"),
    ]
    history = build_eva_history(
        2026,
        datetime(2026, 2, 4),
        lambda cut: cut_rows([], events, cut, lambda pid: []),
    )
    january = history.months[0]
    assert january.cut_label == "29/01/2026"
    assert january.view.totals.total == 2
    assert january.view.totals.time_cost.cost_percent == 0
    selected = cut_rows([], events, date(2026, 1, 29), lambda pid: [])
    assert {r["idProyecto"] for r in selected} == {"A", "B"}
    assert (
        next(r for r in selected if r["idProyecto"] == "A")["desviacionDias"]
        == -1
    )


@pytest.mark.django_db
def test_api_exposes_compliance_percentages_and_workday_cut(
    client, monkeypatch, settings
):
    settings.PORTAL_LOGIN_REQUIRED = False
    from tests.portal.kpi_cut_support import stub_inventory

    stub_inventory(monkeypatch)
    response = client.get("/api/v1/screens/kpis-dm/?corte=2026-01-29")
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["metrics"] == {
        "basis": "eva1_cut_over_budget",
        "t_unit": "percent",
        "c_unit": "percent",
        "cut_weekdays": [0, 1, 2, 3],
    }
    assert data["cut"]["label"] == "29/01/2026"
    assert data["summary"]["totals"]["total"] == 2
    assert data["summary"]["totals"]["t"] == 100
    assert data["summary"]["totals"]["c"] == 50
    assert data["summary"]["rows"][0]["time_late"] == 0
    assert data["summary"]["rows"][0]["cost_over"] == 1


@pytest.mark.django_db
def test_current_eva_sign_changes_without_altering_shared_loader(
    client, monkeypatch, settings
):
    from types import SimpleNamespace

    from apps.portal.services.eva2 import build_eva2_view
    from tests.portal.test_eva2 import make_row

    settings.PORTAL_LOGIN_REQUIRED = False
    shared = build_eva2_view([make_row(desviacionDias=-1)])
    monkeypatch.setattr(
        "apps.portal.views.load_eva2",
        lambda: SimpleNamespace(view=shared, error=""),
    )
    native = build_eva2_view([make_row(desviacionDias=1)])
    monkeypatch.setattr(
        "apps.portal.services.eva_inventory_view.load_inventory_eva",
        lambda cut, **kwargs: {
            "eva": native,
            "inventory_rows": [],
            "error": "",
        },
    )
    response = client.get("/operativa/eva-1/")
    assert response.context["eva"].projects[0].deviation_days == 1
    assert shared.projects[0].deviation_days == -1


@pytest.mark.django_db
def test_explicit_eva_cut_today_uses_same_reconstruction_as_kpis(
    client, monkeypatch, settings
):
    from apps.portal.services.eva2 import build_eva2_view

    settings.PORTAL_LOGIN_REQUIRED = False
    monkeypatch.setattr(
        "django.utils.timezone.localdate", lambda: date(2026, 1, 29)
    )
    rows = cut_rows(
        [],
        [event("A", "Deployment", "2025-01-01", "2026-01-30")],
        date(2026, 1, 29),
        lambda pid: [],
    )
    monkeypatch.setattr(
        "apps.portal.services.eva_inventory_view.load_inventory_eva",
        lambda cut, **kwargs: {
            "eva": build_eva2_view(rows),
            "inventory_rows": [],
            "error": "",
        },
    )
    monkeypatch.setattr(
        "apps.portal.views.load_eva2",
        lambda: pytest.fail("explicit cut must not use live summary"),
    )
    response = client.get("/operativa/eva-1/?corte=2026-01-29")
    assert response.context["eva"].projects[0].deviation_days == -1
    assert (
        response.context["eva"].total_projects
        == compliance_view(rows).totals.total
    )
