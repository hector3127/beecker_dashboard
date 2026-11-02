"""Totales completos separados de capacidad y sus asignaciones."""

from datetime import date

import pytest
from django.utils import timezone

from apps.datastore.models import ClockifyMonthSync, ClockifyTimeEntry, SyncRun
from apps.portal.services.clockify_month_totals import clockify_month_totals

pytestmark = pytest.mark.django_db


def test_all_people_projects_weekends_and_nonbillable_are_counted(settings):
    settings.CLOCKIFY_STORE_ENABLED = True
    run = SyncRun.objects.create(kind="test")
    ClockifyMonthSync.objects.create(
        month=date(2026, 10, 1),
        entries_count=3,
        total_seconds=43200,
        synced_at=timezone.now(),
        run=run,
    )
    for key, hours, billable, day in [
        ("external", 5, True, 3),
        ("other", 4, False, 4),
        ("third", 3, True, 5),
    ]:
        ClockifyTimeEntry.objects.create(
            entry_id=key,
            project_id=key,
            user_id=key,
            user_name=key,
            month=date(2026, 10, 1),
            entry_date=date(2026, 10, day),
            duration_seconds=hours * 3600,
            billable=billable,
        )
    ClockifyTimeEntry.objects.create(
        entry_id="another-month",
        project_id="old",
        user_id="old",
        month=date(2026, 9, 1),
        duration_seconds=100 * 3600,
    )
    result = clockify_month_totals("2026-10")
    assert result["consumed"] == 12
    assert result["billable"] == 8
    assert result["entries"] == 3 and result["people"] == 3


def test_unsynced_month_is_unknown_not_zero(settings):
    settings.CLOCKIFY_STORE_ENABLED = True
    assert clockify_month_totals("2026-10") == {
        "available": False,
        "month": "2026-10",
    }


def test_disabled_store_uses_legacy_source(settings):
    settings.CLOCKIFY_STORE_ENABLED = False
    assert clockify_month_totals("2026-10") is None
