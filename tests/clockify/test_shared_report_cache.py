from concurrent.futures import ThreadPoolExecutor
from datetime import date
from unittest.mock import Mock

import pytest

from apps.clockify.services.time_entry_loader import ReportPlan
from tests.clockify.test_time_entry_loader import REPORT_ENTRY, build_loader


def test_variants_share_one_download_and_preserve_internal_ids():
    client = Mock()
    client.fetch_detailed_report_counted.return_value = ([REPORT_ENTRY], 1)
    loader = build_loader(client)
    plans = [
        ReportPlan(pid, "c1", date(2026, 9, 1), date(2026, 9, 30))
        for pid in ["AMK.008", "AMK.008_S2"]
    ]
    with ThreadPoolExecutor(max_workers=2) as pool:
        entries = list(
            pool.map(lambda plan: loader._fetch_report(plan, {}), plans)
        )
    assert client.fetch_detailed_report_counted.call_count == 1
    assert entries[0][0].project_id == "AMK.008"
    assert entries[1][0].project_id == "AMK.008_S2"
    loader._download_report(plans[0], {})
    assert client.fetch_detailed_report_counted.call_count == 2


def dated_entry(entry_id, start):
    return {
        **REPORT_ENTRY,
        "_id": entry_id,
        "timeInterval": {"start": start, "duration": 3600},
    }


def test_overlapping_ranges_reuse_months_and_trim_local_dates():
    client = Mock()
    client.fetch_detailed_report_counted.return_value = (
        [
            dated_entry("before", "2026-09-10T12:00:00Z"),
            dated_entry("inside", "2026-09-20T12:00:00Z"),
            # UTC octubre, pero septiembre en America/Mexico_City.
            dated_entry("boundary", "2026-10-01T01:00:00Z"),
        ],
        1,
    )
    loader = build_loader(client)
    full = ReportPlan("AMK.008", "c1", date(2026, 9, 1), date(2026, 9, 30))
    narrow = ReportPlan(
        "AMK.008_S2", "c1", date(2026, 9, 15), date(2026, 9, 30)
    )
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(
            pool.map(lambda p: loader._fetch_report(p, {}), [full, narrow])
        )
    assert client.fetch_detailed_report_counted.call_count == 1
    assert [e.entry_id for e in results[0]] == ["before", "inside", "boundary"]
    assert [e.entry_id for e in results[1]] == ["inside", "boundary"]


def test_only_missing_month_is_downloaded_for_a_longer_range():
    client = Mock()
    client.fetch_detailed_report_counted.return_value = ([], 1)
    loader = build_loader(client)
    factory = Mock(return_value=client)
    loader._client_factory = factory
    loader._fetch_report(
        ReportPlan("A", "c1", date(2026, 8, 10), date(2026, 9, 15)), {}
    )
    assert factory.call_count == 1
    loader._fetch_report(
        ReportPlan("B", "c1", date(2026, 8, 1), date(2026, 10, 2)), {}
    )
    assert factory.call_count == 2
    assert client.fetch_detailed_report_counted.call_count == 3
    assert [
        c.args[2:4] for c in client.fetch_detailed_report_counted.call_args_list
    ] == [
        (date(2026, 8, 1), date(2026, 8, 31)),
        (date(2026, 9, 1), date(2026, 9, 30)),
        (date(2026, 10, 1), date(2026, 10, 2)),
    ]


def test_force_refresh_replaces_shared_month_data():
    client = Mock()
    client.fetch_detailed_report_counted.side_effect = [
        ([dated_entry("old", "2026-09-10T12:00:00Z")], 1),
        ([dated_entry("new", "2026-09-10T12:00:00Z")], 1),
    ]
    loader = build_loader(client)
    plan = ReportPlan("A", "c1", date(2026, 9, 1), date(2026, 9, 30))
    loader._download_report(plan, {}, use_raw_cache=True)
    loader._download_report(plan, {})
    records, count = loader._download_report(plan, {}, use_raw_cache=True)
    assert [e.entry_id for e in records] == ["new"]
    assert count == 0


def test_failed_month_is_retried_without_caching_a_partial_report():
    client = Mock()
    client.fetch_detailed_report_counted.side_effect = [
        ([], 1),
        RuntimeError("offline"),
        ([], 1),
    ]
    loader = build_loader(client)
    plan = ReportPlan("A", "c1", date(2026, 8, 1), date(2026, 9, 30))
    with pytest.raises(RuntimeError, match="offline"):
        loader._fetch_report(plan, {})
    loader._fetch_report(plan, {})
    assert client.fetch_detailed_report_counted.call_count == 3


def test_current_month_coverage_grows_on_the_next_day():
    client = Mock()
    client.fetch_detailed_report_counted.return_value = ([], 1)
    loader = build_loader(client)
    plan = ReportPlan("A", "c1", date(2026, 10, 1), date(2026, 10, 2))
    loader._download_report(plan, {}, use_raw_cache=True)
    loader._today = date(2026, 10, 3)
    loader._download_report(plan, {}, use_raw_cache=True)
    assert [
        c.args[3] for c in client.fetch_detailed_report_counted.call_args_list
    ] == [date(2026, 10, 2), date(2026, 10, 3)]


def test_months_after_today_are_not_requested():
    client = Mock()
    client.fetch_detailed_report_counted.return_value = ([], 1)
    loader = build_loader(client)  # hoy: 2026-10-02
    loader._fetch_report(
        ReportPlan("A", "c1", date(2026, 9, 1), date(2027, 3, 31)), {}
    )
    assert [
        c.args[2] for c in client.fetch_detailed_report_counted.call_args_list
    ] == [date(2026, 9, 1), date(2026, 10, 1)]


def test_full_current_month_can_serve_a_shorter_current_range():
    client = Mock()
    client.fetch_detailed_report_counted.return_value = ([], 1)
    loader = build_loader(client)
    loader._fetch_report(
        ReportPlan("A", "c1", date(2026, 10, 1), date(2026, 10, 31)), {}
    )
    loader._fetch_report(
        ReportPlan("B", "c1", date(2026, 10, 1), date(2026, 10, 2)), {}
    )
    assert client.fetch_detailed_report_counted.call_count == 1


def test_missing_dates_use_exact_query_instead_of_guessing():
    client = Mock()
    client.fetch_detailed_report_counted.side_effect = [
        ([dated_entry("unknown", "invalid")], 1),
        ([], 1),
    ]
    loader = build_loader(client)
    plan = ReportPlan("A", "c1", date(2026, 9, 10), date(2026, 9, 20))
    assert loader._fetch_report(plan, {}) == []
    assert client.fetch_detailed_report_counted.call_args.args[2:4] == (
        date(2026, 9, 10),
        date(2026, 9, 20),
    )
