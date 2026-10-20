from datetime import date, datetime

from apps.portal.services.revenue_costs import (
    partition_aer_months,
    resolve_cost_scope,
)
from core.time_entries.models import TimeEntry


def test_aer_month_uses_clockify_base_and_exact_month():
    assert resolve_cost_scope("AER.NEM.001.02", [], date(2026, 10, 19)) == (
        "AER.NEM.001",
        date(2026, 2, 1),
        date(2026, 2, 28),
        2,
    )
    assert (
        resolve_cost_scope(
            "AER.NEM.001", ["AER.NEM.001.02"], date(2026, 10, 19)
        )[3]
        is None
    )


def test_aer_base_and_monthly_variants_partition_hours_without_duplicates():
    ids = ["AER.NEM.001", "AER.NEM.001.02", "aer.nem.001.09"]
    entries = [
        TimeEntry(
            str(m), "AER.NEM.001", "Ana", datetime(2026, m, 5), m, True, 7
        )
        for m in (1, 2, 3, 9, 10)
    ]
    selected = [
        partition_aer_months(
            pid, ids, entries, date(2026, 1, 1), date(2026, 10, 19)
        )
        for pid in ids
    ]
    assert [[e.entry_id for e in group] for group in selected] == [
        ["1", "3", "10"],
        ["2"],
        ["9"],
    ]
    assert sum(e.duration_hours for group in selected for e in group) == sum(
        e.duration_hours for e in entries
    )


def test_without_aer_monthly_variants_base_keeps_selected_date_range():
    entries = [
        TimeEntry(
            str(m), "AER.NEM.001", "Ana", datetime(2026, m, 5), 1, True, 7
        )
        for m in (1, 2, 3)
    ]
    result = partition_aer_months(
        "AER.NEM.001",
        ["AER.NEM.001"],
        entries,
        date(2026, 2, 1),
        date(2026, 3, 31),
    )
    assert [e.entry_id for e in result] == ["2", "3"]


def test_future_month_is_not_an_error_or_unconsulted_project(monkeypatch):
    from django.core.cache import cache

    from apps.portal.services import revenue_costs

    monkeypatch.setattr(
        revenue_costs.timezone, "localdate", lambda: date(2026, 10, 19)
    )
    assert revenue_costs.future_project_month("AER.NEM.001.11")
    assert revenue_costs.future_project_month("ROC.NEM.001.12")
    assert not revenue_costs.future_project_month("AER.NEM.001.09")
    cache.clear()
    result = revenue_costs.cost_summary(ids=["AER.NEM.001.11"])
    assert (
        result["future"] == 1
        and result["pending"] == 0
        and result["consulted"] == 0
    )
    assert result["projects"][0]["status"] == "future"
