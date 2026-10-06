from datetime import date, datetime

import pytest

from apps.clockify.exceptions import ClockifyProjectError
from apps.clockify.services.clockify_client import ClockifyProject
from apps.clockify.services.time_entry_loader import ClockifyTimeEntryLoader
from core.exceptions import TimeEntrySourceError
from tests.clockify.fakes import DictCache, FakeClockifyClient
from tests.fakes import InMemorySheetRepository

SHEETS = {
    "Proyectos": [["ID_Proyecto"], ["AMK.008"], ["AMK.008_S2"]],
    "Recursos": [["Proyecto", "Nombre del recurso"], ["IXB.002", "Ana"]],
    "Historico_Proyectos": [
        ["Project ID", "Status", "Start", "Finish"],
        ["AMK.008", "Discovery", "01/01/2026", ""],
        ["AMK.008_S2", "Discovery", "01/02/2026", ""],
        ["IXB.002", "Discovery", "01/03/2026", ""],
    ],
    "Banda salarial": [["Nombre", "Banda"], ["Ana Ruiz", "B1"]],
    "Master rates": [["Banda", "", "", "Rate"], ["B1", "", "", 15]],
}

REPORT_ENTRY = {
    "_id": "e1",
    "projectId": "c1",
    "userName": "Ana Ruiz",
    "billable": True,
    "description": "Pruebas",
    "timeInterval": {"start": "2026-09-30T23:30:00Z", "duration": 5400},
}


def build_loader(client, sheets=SHEETS):
    return ClockifyTimeEntryLoader(
        reader=InMemorySheetRepository(sheets),
        client_factory=lambda: client,
        workspace_id="ws",
        today=date(2026, 10, 2),
        cache_store=DictCache(),
        cache_prefix="test",
    )


def test_entries_are_mapped_and_deduplicated():
    client = FakeClockifyClient(
        [ClockifyProject("c1", "AMK.008"), ClockifyProject("c2", "IXB.002")],
        {"c1": [REPORT_ENTRY]},
    )

    entries = build_loader(client).load_all()

    assert len(entries) == 1
    entry = entries[0]
    assert entry.project_id == "AMK.008"
    assert entry.duration_hours == 1.5
    assert entry.costing_rate == 15
    assert entry.entry_date == datetime(2026, 9, 30)
    # Los reportes se piden en paralelo; el orden de llamada puede variar.
    assert sorted(call[1] for call in client.report_calls) == [
        date(2026, 1, 1),
        date(2026, 2, 1),
        date(2026, 3, 1),
    ]


def test_any_failing_project_stops_the_load():
    client = FakeClockifyClient(
        [ClockifyProject("c1", "AMK.008"), ClockifyProject("c2", "IXB.002")],
        {"c1": [REPORT_ENTRY]},
        failing={"c2"},
    )

    with pytest.raises(ClockifyProjectError) as error_info:
        build_loader(client).load_all()

    assert "IXB.002" in error_info.value.detail


def test_project_without_range_is_reported():
    sheets = dict(SHEETS)
    sheets["Proyectos"] = [["ID_Proyecto"], ["SIN.RANGO"]]
    sheets["Recursos"] = [["Proyecto"]]
    client = FakeClockifyClient([ClockifyProject("c9", "SIN.RANGO")], {})

    with pytest.raises(ClockifyProjectError) as error_info:
        build_loader(client, sheets).load_all()

    assert "rango de fechas" in error_info.value.detail


def test_strict_report_uses_cache_and_force_refresh():
    client = FakeClockifyClient(
        [ClockifyProject("c1", "AMK.008 - Robot")],
        {"c1": [REPORT_ENTRY]},
    )
    loader = build_loader(client)
    date_range = (date(2026, 9, 1), date(2026, 9, 30))

    report = loader.load_strict_project_report("AMK.008", date_range, False)
    loader.load_strict_project_report("AMK.008", date_range, False)
    loader.load_strict_project_report("AMK.008", date_range, True)

    assert report.project.name == "AMK.008 - Robot"
    assert report.request_count == 1
    assert len(report.entries) == 1
    assert len(client.report_calls) == 2


def test_strict_report_errors_name_the_project():
    client = FakeClockifyClient(
        [ClockifyProject("c1", "AMK.008")],
        {},
        failing={"c1"},
    )
    date_range = (date(2026, 9, 1), date(2026, 9, 30))

    with pytest.raises(ClockifyProjectError) as missing:
        build_loader(client).load_strict_project_report(
            "IXB.009",
            date_range,
            False,
        )

    assert "IXB.009" in missing.value.detail

    with pytest.raises(TimeEntrySourceError) as failed:
        build_loader(client).load_strict_project_report(
            "AMK.008",
            date_range,
            False,
        )

    assert failed.value.detail.endswith("Proyecto: AMK.008 [c1].")
