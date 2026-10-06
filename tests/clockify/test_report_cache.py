from datetime import date

import pytest

from apps.clockify.services.clockify_client import ClockifyProject
from apps.clockify.services.report_cache import report_cache_seconds
from apps.clockify.services.time_entry_loader import ClockifyTimeEntryLoader
from tests.clockify.fakes import DictCache, FakeClockifyClient
from tests.fakes import InMemorySheetRepository

TODAY = date(2026, 10, 2)
DAY = 86400
SIX_HOURS = 21600
HALF_HOUR = 1800

HISTORY = [
    ["Project ID", "Status", "x", "Start", "Finish"],
    ["AMK.008", "Discovery", "", "05/01/2026", "20/01/2026"],
    ["AMK.008", "Deployment OP", "", "01/05/2026", "30/06/2026"],
    ["IXB.002", "Discovery", "", "01/02/2026", ""],
]

SHEETS = {
    "Proyectos": [["ID_Proyecto"], ["AMK.008"], ["IXB.002"]],
    "Recursos": [["Proyecto", "Nombre del recurso"]],
    "Historico_Proyectos": HISTORY,
    "Banda salarial": [["Nombre", "Banda"], ["Ana Ruiz", "B1"]],
    "Master rates": [["Banda", "", "", "Rate"], ["B1", "", "", 15]],
}

REPORT_ENTRY = {
    "_id": "e1",
    "projectId": "c1",
    "userName": "Ana Ruiz",
    "billable": True,
    "description": "Pruebas",
    "timeInterval": {"start": "2026-02-10T15:00:00Z", "duration": 3600},
}


@pytest.mark.parametrize(
    ("has_entries", "end_date", "expected"),
    [
        (True, date(2026, 6, 30), DAY),
        (False, date(2026, 6, 30), DAY),
        (True, date(2026, 10, 1), DAY),
        (True, TODAY, SIX_HOURS),
        (False, TODAY, HALF_HOUR),
        (True, date(2026, 12, 31), SIX_HOURS),
        (False, date(2026, 12, 31), HALF_HOUR),
    ],
)
def test_report_cache_seconds(has_entries, end_date, expected):
    assert report_cache_seconds(has_entries, end_date, TODAY) == expected


def build_loader(cache):
    client = FakeClockifyClient(
        [ClockifyProject("c1", "AMK.008"), ClockifyProject("c2", "IXB.002")],
        {"c1": [REPORT_ENTRY], "c2": [REPORT_ENTRY]},
    )

    return ClockifyTimeEntryLoader(
        reader=InMemorySheetRepository(SHEETS),
        client_factory=lambda: client,
        workspace_id="ws",
        today=TODAY,
        cache_store=cache,
        cache_prefix="test",
    )


def report_timeouts(cache):
    return {
        key.split(":")[3]: timeout
        for key, timeout in cache.timeouts.items()
        if key.startswith("test:report:")
    }


def test_portfolio_keeps_closed_projects_for_a_day():
    cache = DictCache()

    build_loader(cache).load_all()

    assert report_timeouts(cache) == {"AMK.008": DAY, "IXB.002": SIX_HOURS}


def test_project_hours_use_the_same_rule():
    cache = DictCache()

    build_loader(cache).load_project_hours("AMK.008")
    build_loader(cache).load_project_hours("IXB.002")

    assert report_timeouts(cache) == {"AMK.008": DAY, "IXB.002": SIX_HOURS}


def test_strict_report_of_a_closed_range_is_kept_a_day():
    cache = DictCache()
    loader = build_loader(cache)

    loader.load_strict_project_report(
        "AMK.008",
        (date(2026, 1, 1), date(2026, 6, 30)),
        False,
    )
    loader.load_strict_project_report(
        "IXB.002",
        (date(2026, 9, 1), date(2026, 10, 2)),
        False,
    )

    strict = {
        key.split(":")[3]: timeout
        for key, timeout in cache.timeouts.items()
        if key.startswith("test:strict_report:")
    }
    assert strict == {"AMK.008": DAY, "IXB.002": SIX_HOURS}
