from copy import deepcopy
from datetime import date

from apps.clockify.services.clockify_client import ClockifyProject
from core.utils.source_refresh import force_sources
from tests.clockify.fakes import FakeClockifyClient
from tests.clockify.test_time_entry_loader import REPORT_ENTRY, build_loader


def test_manual_refresh_ignores_report_cache_and_uses_live_entries():
    api = FakeClockifyClient(
        [ClockifyProject("c1", "AMK.008")], {"c1": [deepcopy(REPORT_ENTRY)]}
    )
    loader = build_loader(api)
    original = loader.load_project(
        "AMK.008", (date(2026, 9, 1), date(2026, 9, 30))
    )
    token = force_sources.set(True)
    try:
        refreshed = loader.load_project(
            "AMK.008", (date(2026, 9, 1), date(2026, 9, 30))
        )
    finally:
        force_sources.reset(token)
    assert len(api.report_calls) == 2
    assert sum(e.duration_hours for e in refreshed) == sum(
        e.duration_hours for e in original
    )
    loader.load_project("AMK.008", (date(2026, 9, 1), date(2026, 9, 30)))
    assert len(api.report_calls) == 2
