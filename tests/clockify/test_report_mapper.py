from datetime import datetime
from zoneinfo import ZoneInfo

from apps.clockify.services.report_mapper import build_time_entry_from_report

MEXICO = ZoneInfo("America/Mexico_City")


def test_entry_keeps_local_start_and_end_times():
    entry = build_time_entry_from_report(
        {
            "_id": "e1",
            "userName": "Ana",
            "timeInterval": {
                "start": "2026-10-02T01:30:00Z",
                "end": "2026-10-02T03:00:00Z",
                "duration": 5400,
            },
        },
        "AER.001",
        {},
        MEXICO,
    )

    assert entry.started_at == datetime(2026, 10, 1, 19, 30)
    assert entry.ended_at == datetime(2026, 10, 1, 21, 0)
    assert entry.entry_date == datetime(2026, 10, 1)
    assert entry.duration_hours == 1.5


def test_entry_without_times_has_none():
    entry = build_time_entry_from_report(
        {"id": "e2", "timeInterval": {"duration": "PT1H"}},
        "AER.001",
        {},
        MEXICO,
    )

    assert entry.started_at is None
    assert entry.ended_at is None
