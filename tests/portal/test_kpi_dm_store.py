"""KPI persistence, exact dates, rollover and immutable past periods."""

from datetime import UTC, date, datetime
from io import StringIO
from unittest.mock import patch

import pytest
from django.core.management import call_command

from apps.datastore.models import (
    DmKpiMetric,
    DmKpiObservation,
    DmKpiPeriod,
    EvaExtraction,
)
from apps.portal.services.kpi_dm_store import load_kpi_cut, load_kpi_history
from apps.portal.services.kpi_dm_sync import (
    capture_current_month,
    close_due_periods,
)

pytestmark = pytest.mark.django_db


def day(monkeypatch, value):
    monkeypatch.setattr(
        "django.utils.timezone.now",
        lambda: datetime.combine(
            value, datetime.min.time(), tzinfo=UTC
        ).replace(hour=18),
    )


def source(value):
    stamp = datetime.combine(value, datetime.min.time(), tzinfo=UTC).replace(
        hour=18
    )
    return EvaExtraction.objects.create(
        cut=value,
        started_at=stamp,
        finished_at=stamp,
        published=True,
        metrics={
            "kind": "summary_inventory",
            "eva_enriched": True,
            "source_observed_at": stamp.isoformat(),
        },
    )


def project(pid, manager, deviation, advance):
    return {
        "display_id": pid,
        "fields": {"delivery_manager": manager},
        "budget": "100",
        "deviation_days": deviation,
        "eva_metrics": {"burn": advance, "avance": advance},
    }


@pytest.fixture
def current(monkeypatch, settings):
    settings.KPI_DM_AUTO_UPDATE_ENABLED = False
    settings.EVA_MONTHLY_CLOSES_ENABLED = False
    day(monkeypatch, date(2026, 10, 28))
    run = source(date(2026, 10, 28))
    rows = [
        project("A", "Ana", -1, 150),
        project("B", "Ana", 1, None),
        project("C", "Beto", 0, 100),
    ]
    monkeypatch.setattr(
        "apps.portal.services.kpi_dm_sync.inventory_rows",
        lambda **kwargs: (run, rows),
    )
    return rows


def test_empty_read_is_pending_and_does_not_contact_sources_or_write():
    with (
        patch(
            "requests.sessions.Session.request",
            side_effect=AssertionError("external read"),
        ),
        patch(
            "apps.portal.services.summary_inventory.inventory_rows",
            side_effect=AssertionError("EVA read"),
        ),
    ):
        history = load_kpi_history(2026)
        assert len(history.history.months) == 12
        assert all(not month.observed for month in history.history.months)
        assert load_kpi_cut(date(2026, 10, 28)).observation is None
    assert (
        DmKpiPeriod.objects.count()
        == DmKpiObservation.objects.count()
        == DmKpiMetric.objects.count()
        == 0
    )


def test_month_filter_uses_latest_saved_pointer_and_preserves_other_years(
    current,
):
    from django.test import RequestFactory

    from apps.portal.views import kpi_context

    observation = capture_current_month()
    context = kpi_context(
        RequestFactory().get(
            "/", {"mes": "2026-10", "history_year": "2025", "dm": "Ana"}
        )
    )
    assert context["kpi_filters"]["month"] == "2026-10"
    assert context["kpi_filters"]["cut"] == observation.cut.isoformat()
    assert context["kpi_filters"]["history_year"] == 2025
    assert context["kpis"].totals.total == 2
    missing = kpi_context(RequestFactory().get("/", {"mes": "2026-09"}))
    assert missing["cut_available"] is False


@pytest.mark.parametrize("month", ["2026-11", "2026-13", "2026-1", "bad"])
def test_month_filter_rejects_invalid_or_future_month(current, month):
    from django.test import RequestFactory
    from rest_framework.exceptions import ValidationError

    from apps.portal.views import kpi_context

    with pytest.raises(ValidationError):
        kpi_context(RequestFactory().get("/", {"mes": month}))


def test_counts_persist_and_percentages_use_dm_total_with_pending(current):
    observation = capture_current_month()
    assert observation.cut == date(2026, 10, 28)
    assert observation.period.month == date(2026, 10, 1)
    assert observation.period.closing_day == date(2026, 10, 29)
    ana = observation.metrics.get(manager="Ana")
    assert (
        ana.total,
        ana.on_time,
        ana.late,
        ana.over_budget,
        ana.cost_unknown,
    ) == (2, 1, 1, 1, 1)
    saved = load_kpi_cut(observation.cut).view
    assert (
        saved.rows[0].time_cost.time_days
        == saved.rows[0].time_cost.cost_percent
        == 50
    )
    assert saved.totals.total == 3
    assert saved.totals.time_cost.cost_percent == pytest.approx(100 / 3)
    assert load_kpi_cut(date(2026, 10, 29)).observation is None
    assert EvaExtraction.objects.count() == 1


def test_saved_reports_ignore_changed_azure_data_until_explicit_update(current):
    observation = capture_current_month()
    saved = load_kpi_cut(observation.cut).view
    current[0]["fields"]["delivery_manager"] = "Reasignado"
    current[0]["eva_metrics"]["avance"] = 0
    with patch(
        "apps.portal.services.kpi_dm_sync.inventory_rows",
        side_effect=AssertionError("must read saved tables"),
    ):
        assert load_kpi_cut(observation.cut).view == saved
        history = load_kpi_history(2026).history
    assert history.months[9].view == saved
    assert all(not month.observed for month in history.months[:9])
    assert all(not month.observed for month in history.months[10:])


def test_current_day_refresh_updates_one_observation_atomically(current):
    observation = capture_current_month()
    current[0]["eva_metrics"]["avance"] = 50
    assert capture_current_month().pk == observation.pk
    assert DmKpiPeriod.objects.count() == DmKpiObservation.objects.count() == 1
    assert observation.metrics.get(manager="Ana").over_budget == 0
    old = load_kpi_cut(observation.cut).view
    with (
        patch(
            "apps.portal.services.kpi_dm_sync.DmKpiMetric.objects.bulk_create",
            side_effect=RuntimeError("rollback"),
        ),
        pytest.raises(RuntimeError),
    ):
        capture_current_month()
    assert load_kpi_cut(observation.cut).view == old


def test_next_month_gets_new_period_and_closed_month_never_changes(
    current, monkeypatch, settings
):
    day(monkeypatch, date(2026, 10, 29))
    source(date(2026, 10, 29))
    october = capture_current_month()
    saved = load_kpi_cut(october.cut).view
    settings.KPI_DM_AUTO_UPDATE_ENABLED = True
    day(monkeypatch, date(2026, 11, 2))
    source(date(2026, 11, 2))
    close_due_periods()
    october.period.refresh_from_db()
    assert october.period.status == "closed"
    current[0]["fields"]["delivery_manager"] = "Otro DM"
    november = capture_current_month()
    assert november.period_id != october.period_id
    assert DmKpiPeriod.objects.count() == 2
    assert load_kpi_cut(october.cut).view == saved
    assert not load_kpi_history(2026).history.months[9].partial


def test_missing_closing_day_becomes_pending_instead_of_fabricated(
    current, monkeypatch, settings
):
    observation = capture_current_month()
    settings.KPI_DM_AUTO_UPDATE_ENABLED = True
    day(monkeypatch, date(2026, 11, 2))
    close_due_periods()
    observation.period.refresh_from_db()
    assert observation.period.status == "pending"
    assert observation.period.latest_observation_id == observation.pk
    assert "Falta captura" in load_kpi_history(2026).notice


def test_automatic_command_and_closing_are_disabled_until_genesis(
    current, monkeypatch
):
    observation = capture_current_month()
    day(monkeypatch, date(2026, 10, 30))
    close_due_periods()
    with patch(
        "apps.portal.management.commands.sync_kpi_dm.capture_current_month"
    ) as capture:
        call_command("sync_kpi_dm", automatic=True, stdout=StringIO())
    capture.assert_not_called()
    observation.period.refresh_from_db()
    assert observation.period.status == "open"


def test_future_daily_command_updates_current_month_then_stops_at_close(
    current, monkeypatch, settings
):
    settings.KPI_DM_AUTO_UPDATE_ENABLED = True
    call_command("sync_kpi_dm", automatic=True, stdout=StringIO())
    day(monkeypatch, date(2026, 10, 29))
    source(date(2026, 10, 29))
    call_command("sync_kpi_dm", automatic=True, stdout=StringIO())
    period = DmKpiPeriod.objects.get()
    assert period.latest_observation.cut == date(2026, 10, 29)
    assert DmKpiObservation.objects.count() == 2
    day(monkeypatch, date(2026, 10, 30))
    source(date(2026, 10, 30))
    call_command("sync_kpi_dm", automatic=True, stdout=StringIO())
    period.refresh_from_db()
    assert period.status == "closed"
    assert DmKpiObservation.objects.count() == 2


def test_no_backfill_outside_current_month_and_no_changes_after_closing(
    current, monkeypatch
):
    day(monkeypatch, date(2026, 11, 2))
    with pytest.raises(ValueError, match="mes actual"):
        capture_current_month()
    assert DmKpiPeriod.objects.count() == 0
    day(monkeypatch, date(2026, 10, 30))
    with pytest.raises(ValueError, match="Terminó el corte"):
        capture_current_month()


def test_historical_daily_observation_does_not_get_rewritten(
    current, monkeypatch
):
    observation = capture_current_month()
    saved = load_kpi_cut(observation.cut).view
    day(monkeypatch, date(2026, 10, 29))
    with pytest.raises(ValueError, match="observación de hoy"):
        capture_current_month(require_today=True)
    current[0]["eva_metrics"]["avance"] = 0
    assert capture_current_month().pk == observation.pk
    assert load_kpi_cut(observation.cut).view == saved


def test_observed_zero_projects_is_distinct_from_missing_observation(current):
    current.clear()
    observation = capture_current_month()
    result = load_kpi_cut(observation.cut)
    assert result.observation is not None
    assert result.view.totals.total == 0
    assert result.view.totals.time_cost.cost_percent is None
    assert load_kpi_history(2026).history.months[9].observed


def test_kpi_api_reads_only_saved_tables(current, client, settings):
    settings.PORTAL_LOGIN_REQUIRED = False
    observation = capture_current_month()
    before = observation.captured_at
    with (
        patch(
            "requests.sessions.Session.request",
            side_effect=AssertionError("external read"),
        ),
        patch(
            "apps.portal.services.eva_inventory_view.load_inventory_eva",
            side_effect=AssertionError("EVA read"),
        ),
    ):
        response = client.get(
            "/api/v1/screens/kpis-dm/",
            {"corte": observation.cut.isoformat(), "dm": "Ana"},
        )
    assert response.status_code == 200
    payload = response.json()["data"]
    assert payload["metrics"]["basis"] == "dm_kpi_saved_reports"
    assert payload["summary"]["totals"]["total"] == 2
    assert payload["summary"]["totals"]["c"] == 50
    assert len(payload["history"]["months"]["headers"]) == 12
    assert payload["history"]["months"]["totals"][0] is None
    observation.refresh_from_db()
    assert observation.captured_at == before
