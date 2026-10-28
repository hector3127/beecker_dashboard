"""End-of-day project selection, exact historical DM and bounded hours."""

from datetime import date, datetime

import pytest

from apps.portal.services.eva2 import build_eva2_view
from apps.portal.services.eva_cut import cut_rows, read_cut, select_view
from core.time_entries.models import TimeEntry

CUT = date(2026, 1, 29)


def event(pid, status, start, finish="", manager="Alberto", **extra):
    return {
        "Project ID": pid,
        "Status": status,
        "Start": start,
        "Finish": finish,
        "Delivery Manager": manager,
        "Service": "RaaS",
        "Project Name": pid,
        "Account": "Cliente",
        "Budget  (Hrs)": 100,
        **extra,
    }


def hours(key, day, value, billable=True):
    return TimeEntry(
        key,
        "AMK.009",
        "Persona",
        datetime.fromisoformat(day),
        value,
        billable,
        0,
    )


def test_open_at_cut_includes_overdue_suspended_and_later_completed():
    history = [
        event("A", "Deployment", "2025-10-30", "2026-01-30"),
        event("A", "Completed", "2026-02-01"),
        event("B", "Discovery", "2025-01-01", "2025-09-01"),
        event("B", "Suspendido", "2025-09-02", "", manager="Lea"),
        event("C", "Discovery", "2026-02-01"),
        event("D", "Discovery", "2025-01-01"),
        event("D", "Completed", "2026-01-29"),
        event("E", "Discovery", "2025-01-01"),
        event("E", "Cancelled", "2026-01-28"),
    ]
    rows = cut_rows([], history, CUT, lambda pid: [])
    assert {r["idProyecto"] for r in rows} == {"A", "B"}
    assert (
        next(r for r in rows if r["idProyecto"] == "B")["status"]
        == "Suspendido"
    )
    assert {r["deliveryManager"] for r in rows} == {"Alberto", "Lea"}


def test_cut_uses_dated_exact_dm_and_billable_unique_hours_through_day():
    history = [
        event("AMK.009", "Discovery", "2025-10-01", manager="Alberto"),
        event("AMK.009", "Development", "2026-02-01", manager="Otro"),
        event("AMK.009_S2", "Discovery", "2026-01-01", manager="Brandon"),
    ]
    entries = [
        hours("1", "2026-01-29T23:59:59", 10),
        hours("1", "2026-01-29T23:59:59", 10),
        hours("2", "2026-01-30T00:00:00", 50),
        hours("3", "2026-01-28T00:00:00", 20, False),
    ]
    rows = cut_rows([], history, CUT, lambda pid: entries)
    row = next(r for r in rows if r["idProyecto"] == "AMK.009")
    assert row["deliveryManager"] == "Alberto"
    assert row["burn"] == 10
    assert row["etc"] == 90
    assert row["avance"] == 10


def test_summaries_and_manager_catalog_are_not_limited_to_three():
    rows = cut_rows(
        [],
        [
            event(f"P{i}", "Discovery", "2026-01-01", manager=f"DM{i}")
            for i in range(7)
        ],
        CUT,
        lambda pid: [],
    )
    view = build_eva2_view(rows)
    assert len(view.service_rows) == 7
    selected = select_view(view, "DM4", "RaaS")
    assert (
        selected.total_projects
        == selected.service_totals.total
        == selected.status_totals.total
        == 1
    )
    assert selected.projects[0].manager == "DM4"


def test_cut_uses_mexico_day_for_utc_clockify_entries():
    rows = cut_rows(
        [],
        [event("AMK.009", "Discovery", "2025-10-01")],
        CUT,
        lambda pid: [
            hours("included", "2026-01-30T05:59:59+00:00", 2),
            hours("excluded", "2026-01-30T06:00:00+00:00", 50),
        ],
    )
    assert rows[0]["burn"] == 2


@pytest.mark.parametrize("raw", ["invalid", "2026-02-30", "2099-01-01"])
def test_reject_invalid_or_future_cut(raw):
    with pytest.raises(ValueError):
        read_cut(raw)


def test_cut_page_keeps_all_manager_options_and_masks_azure(
    client, monkeypatch, settings, db
):
    from dataclasses import replace

    settings.PORTAL_LOGIN_REQUIRED = False
    view = build_eva2_view(
        cut_rows(
            [],
            [
                event(f"P{i}", "Discovery", "2026-01-01", manager=f"DM{i}")
                for i in range(7)
            ],
            CUT,
            lambda pid: [],
        )
    )
    view = replace(
        view,
        projects=tuple(replace(p, azure_pending=True) for p in view.projects),
    )
    monkeypatch.setattr(
        "apps.portal.services.eva_inventory_view.load_inventory_eva",
        lambda day, **kwargs: {"eva": view, "inventory_rows": [], "error": ""},
    )
    response = client.get(
        "/operativa/eva-1/", {"corte": "2026-01-29", "manager": "DM4"}
    )
    assert response.status_code == 200
    assert len(response.context["eva_managers"]) == 7
    assert response.context["eva"].total_projects == 1
    assert response.context["eva"].projects[0].manager == "DM4"
    assert "Pendiente" in response.content.decode()


def test_invalid_cut_page_does_not_load_sources(client, monkeypatch, settings):
    settings.PORTAL_LOGIN_REQUIRED = False
    monkeypatch.setattr(
        "apps.portal.services.eva_inventory_view.load_inventory_eva",
        lambda day, **kwargs: pytest.fail("must not read sources"),
    )
    assert client.get("/operativa/eva-1/?corte=invalid").status_code == 400


def test_loader_uses_event_block_budget_and_bounded_clockify(monkeypatch):
    from types import SimpleNamespace

    from apps.portal.services.eva_cut import load_cut
    from tests.fakes import InMemorySheetRepository

    # Duplicate headers in K onward belong to a different table.
    repo = InMemorySheetRepository(
        {
            "Proyectos": [
                ["ID_Proyecto", "Servicio", "Budget_Hrs"],
                ["AMK.009", "RaaS", 999],
            ],
            "Historico_Proyectos": [
                [
                    "Delivery Manager",
                    "Account",
                    "Project ID",
                    "Service",
                    "Project Name",
                    "",
                    "Status",
                    "Start",
                    "Finish",
                    "Budget  (Hrs)",
                    "Delivery Manager",
                    "Client",
                    "Project ID",
                ],
                [
                    "Alberto",
                    "Cuenta",
                    "AMK.009",
                    "RaaS",
                    "Lectura",
                    "",
                    "Discovery",
                    "2025-10-30",
                    "2026-01-30",
                    100,
                    "Otro",
                    "Otra",
                    "OTRO.999",
                ],
            ],
        }
    )
    calls = []

    def load(pid, custom_range):
        calls.append((pid, custom_range))
        return [hours("h", "2026-01-29T12:00:00", 25)]

    monkeypatch.setattr(
        "apps.portal.services.eva_cut.build_sheet_repository", lambda: repo
    )
    monkeypatch.setattr(
        "apps.portal.services.eva_cut.build_clockify_loader",
        lambda reader: SimpleNamespace(load_project=load),
    )
    data = load_cut(CUT)
    assert data["error"] == ""
    project = data["eva"].projects[0]
    assert (
        project.project_id,
        project.manager,
        project.budget,
        project.burn,
    ) == ("AMK.009", "Alberto", 100, 25)
    assert calls == [("AMK.009", (date(2025, 10, 30), CUT))]
    assert project.azure_pending

    from core.exceptions import TimeEntrySourceError

    def missing_loader(reader):
        raise TimeEntrySourceError("Clockify no configurado")

    monkeypatch.setattr(
        "apps.portal.services.eva_cut.build_clockify_loader", missing_loader
    )
    pending = load_cut(CUT)
    assert pending["eva"].total_projects == 1
    assert pending["eva"].projects[0].hours_pending


def test_missing_budget_or_hours_remains_pending_and_out_of_average(
    monkeypatch,
):
    from dataclasses import replace

    from core.exceptions import TimeEntrySourceError

    def unavailable(pid):
        raise TimeEntrySourceError("No sincronizado")

    row = event("A", "Discovery", "2026-01-01")
    row["Budget  (Hrs)"] = ""
    rows = cut_rows([], [row], CUT, unavailable)
    assert rows[0]["budget_pending"] and rows[0]["hours_pending"]
    view = build_eva2_view(rows)
    view = replace(
        view,
        projects=(
            replace(view.projects[0], budget_pending=True, hours_pending=True),
        ),
    )
    assert select_view(view, "", "").time_cost.cost_percent is None
