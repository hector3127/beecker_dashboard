"""Horas de CR alojadas en el proyecto base de Clockify."""

from copy import deepcopy
from datetime import date

import pytest

from apps.clockify.exceptions import ClockifyProjectError
from apps.clockify.services.clockify_client import ClockifyProject
from apps.clockify.services.date_ranges import ProjectDateRangeResolver
from apps.clockify.services.project_matcher import resolve_clockify_project
from tests.clockify.fakes import FakeClockifyClient
from tests.clockify.test_time_entry_loader import build_loader
from tests.fakes import InMemorySheetRepository


def sheets(cr_id="AIN.002_CR", history_id=None):
    return {
        "Proyectos": [["ID_Proyecto"], ["AIN.002"], [cr_id]],
        "Recursos": [["Proyecto"]],
        "Historico_Proyectos": [
            ["Project ID", "Status", "Start", "Finish"],
            ["AIN.002", "Discovery", "01/01/2026", ""],
            ["AIN.002", "Deployment", "", "30/06/2026"],
            [history_id or cr_id, "Discovery", "10/03/2026", ""],
            [history_id or cr_id, "Deployment", "", "20/03/2026"],
        ],
    }


def entry(entry_id, day, task, **extra):
    return {
        "_id": entry_id,
        "userName": "Ana",
        "taskName": task,
        "billable": True,
        "timeInterval": {
            "start": f"2026-03-{day:02d}T16:00:00Z",
            "duration": 3600,
        },
        **extra,
    }


def client(entries, dedicated=False):
    return FakeClockifyClient(
        [ClockifyProject("c1", "AIN.002_CR" if dedicated else "AIN.002")],
        {"c1": entries},
    )


@pytest.mark.parametrize("cr_id", ["AIN.002_CR", "AIN.002 CR", "AIN.002 | CR"])
def test_shared_cr_uses_full_id_history_and_only_cr_tasks(cr_id):
    api = client(
        [
            entry("start", 10, "CR - Desarrollo"),
            entry("finish", 20, "cr Pruebas"),
            entry("before", 9, "CR"),
            entry("after", 21, "CR"),
            entry("other", 15, "S1"),
            entry("numbered", 15, "CR1"),
            entry("missing", 15, ""),
            entry("description-only", 15, "General", description="CR"),
            entry("tag-only", 15, "General", tags=["CR"]),
            entry("false-positive", 15, "Scrum"),
        ]
    )
    hours = build_loader(api, sheets(cr_id, "AIN.002_CR")).load_project_hours(
        cr_id
    )
    assert [item.entry_id for item in hours.entries] == ["start", "finish"]
    assert all(item.project_id == cr_id for item in hours.entries)
    assert hours.date_range.source == "Historico_Proyectos"
    assert api.report_calls == [("c1", date(2026, 3, 1), date(2026, 3, 31))]


def test_portfolio_assigns_shared_cr_entries_before_base_without_duplicates():
    api = client([entry("base", 15, "S1"), entry("cr", 15, "CR")])
    entries = build_loader(api, sheets()).load_all()
    assert {item.entry_id: item.project_id for item in entries} == {
        "base": "AIN.002",
        "cr": "AIN.002_CR",
    }
    assert sum(item.duration_hours for item in entries) == 2


def test_numbered_cr_matches_only_its_own_tasks():
    api = client(
        [
            entry("own", 15, "CR1 - Ajustes"),
            entry("other", 15, "CR2"),
            entry("generic", 15, "CR"),
            entry("conflict", 15, "CR1 / CR2"),
        ]
    )
    records = build_loader(api, sheets("AIN.002_CR1")).load_project(
        "AIN.002_CR1"
    )
    assert [item.entry_id for item in records] == ["own"]


def test_custom_range_is_intersected_with_history_for_shared_cr():
    api = client([entry("own", 15, "CR"), entry("outside", 20, "CR")])
    loader = build_loader(api, sheets())
    entries = loader.load_project(
        "AIN.002_CR", (date(2026, 3, 1), date(2026, 3, 16))
    )
    assert [item.entry_id for item in entries] == ["own"]
    assert api.report_calls == [("c1", date(2026, 3, 1), date(2026, 3, 31))]
    assert (
        loader.load_project("AIN.002_CR", (date(2026, 2, 1), date(2026, 2, 10)))
        == []
    )
    assert len(api.report_calls) == 1


def test_month_outside_history_returns_zero_without_downloading():
    api = client([entry("wrong", 15, "CR")])
    report = build_loader(api, sheets()).load_strict_project_report(
        "AIN.002_CR", (date(2026, 10, 1), date(2026, 10, 31)), False
    )
    assert report.entries == []
    assert report.request_count == 0
    assert api.report_calls == []


def test_missing_cr_history_does_not_use_base_period_or_requested_period():
    data = sheets()
    data["Historico_Proyectos"] = data["Historico_Proyectos"][:3]
    api = client([entry("wrong", 15, "CR")])
    loader = build_loader(api, data)
    with pytest.raises(ClockifyProjectError, match="Historico_Proyectos"):
        loader.load_project("AIN.002_CR")
    with pytest.raises(ClockifyProjectError, match="Historico_Proyectos"):
        loader.load_project("AIN.002_CR", (date(2026, 3, 1), date(2026, 3, 31)))
    assert not api.report_calls


def test_fresh_and_strict_loads_apply_the_same_cr_rule():
    api = client([entry("base", 15, "S1"), entry("cr", 15, "CR")])
    loader = build_loader(api, sheets())
    hours, _ = loader.load_fresh_project_hours("AIN.002_CR")
    assert [item.entry_id for item in hours.entries] == ["cr"]
    report = loader.load_strict_project_report(
        "AIN.002_CR", (date(2026, 3, 1), date(2026, 3, 31)), False
    )
    assert [item.entry_id for item in report.entries] == ["cr"]
    assert api.report_calls == [("c1", date(2026, 3, 1), date(2026, 3, 31))]


def test_dedicated_cr_project_keeps_existing_task_behavior():
    api = client([entry("own", 15, "General")], dedicated=True)
    records = build_loader(api, sheets()).load_project("AIN.002_CR")
    assert [item.entry_id for item in records] == ["own"]


def test_task_id_is_resolved_when_report_has_no_task_name():
    api = client(
        [
            entry("own", 15, "", taskId="cr-task"),
            entry("other", 15, "", taskId="base-task"),
            entry("none", 15, ""),
        ]
    )
    api.list_project_tasks = lambda workspace, project: [
        {"id": "cr-task", "name": "CR - Ajustes"},
        {"id": "base-task", "name": "General"},
    ]
    records = build_loader(api, sheets()).load_project("AIN.002_CR")
    assert [item.entry_id for item in records] == ["own"]
    assert records[0].task_name == "CR - Ajustes"


def test_cr_with_mpb_prefix_uses_history_instead_of_mpb_dates():
    data = deepcopy(sheets("AER.AIN.002_CR"))
    data["MPB"] = [
        ["ID", "Service", "Inicio", "Fin"],
        ["AER.AIN.002_CR", "AER", "01/01/2026", "30/09/2026"],
    ]
    period = ProjectDateRangeResolver(
        InMemorySheetRepository(data), date(2026, 10, 1)
    ).resolve("AER.AIN.002_CR")
    assert period.source == "Historico_Proyectos"
    assert period.start_date == date(2026, 3, 10)
    assert period.end_date == date(2026, 3, 20)


def test_cr_fallback_does_not_guess_between_ambiguous_base_projects():
    projects = [
        ClockifyProject("one", "AIN.002 - Uno"),
        ClockifyProject("two", "AIN.002 - Dos"),
    ]
    assert resolve_clockify_project("AIN.002_CR", projects, {}) is None
    assert (
        resolve_clockify_project("AIN.002_CR", projects, {}, strict=True)
        is None
    )
