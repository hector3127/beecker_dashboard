"""Approved historical report import and non-destructive repeatability."""

from datetime import date

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

from apps.datastore.models import DmKpiMetric, DmKpiPeriod
from apps.portal.management.commands.import_kpi_dm_2026 import unique_count
from apps.portal.services.kpi_dm_store import load_kpi_history

pytestmark = pytest.mark.django_db


def test_report_counts_conversion_empty_cells_and_repeatability():
    october = DmKpiPeriod.objects.create(
        month=date(2026, 10, 1), closing_day=date(2026, 10, 29)
    )
    call_command("import_kpi_dm_2026")
    assert DmKpiMetric.objects.count() == 41
    history = load_kpi_history(2026).history
    assert history.months[0].view.totals.total == 20
    assert history.months[1].view.totals.total == 20
    brandon = DmKpiMetric.objects.get(
        observation__period__month=date(2026, 1, 1),
        manager__startswith="Brandon",
    )
    assert (brandon.on_time, brandon.over_budget) == (2, 3)
    assert not DmKpiMetric.objects.filter(
        observation__period__month=date(2026, 9, 1), manager__startswith="Lea"
    ).exists()
    call_command("import_kpi_dm_2026")
    assert DmKpiMetric.objects.count() == 41
    october.refresh_from_db()
    assert october.status == "open"
    assert october.latest_observation is None


def test_existing_period_rolls_back_the_whole_import():
    DmKpiPeriod.objects.create(
        month=date(2026, 2, 1), closing_day=date(2026, 2, 26)
    )
    with pytest.raises(CommandError):
        call_command("import_kpi_dm_2026")
    assert DmKpiPeriod.objects.count() == 1
    assert not DmKpiMetric.objects.exists()


def test_percentages_must_have_a_unique_compatible_integer():
    assert unique_count(8, 63) == 5
    with pytest.raises(ValueError):
        unique_count(3, 40)
    with pytest.raises(ValueError):
        unique_count(400, 50)
