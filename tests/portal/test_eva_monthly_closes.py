"""Month-end reports cannot drift when Azure, hours or staff change later."""

from copy import deepcopy
from datetime import UTC, date, datetime
from io import StringIO
from unittest.mock import patch

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db.models.deletion import ProtectedError

from apps.datastore.models import (
    EvaAzureSource,
    EvaExtraction,
    EvaMonthlyClose,
    EvaMonthlyClosePolicy,
    EvaScopeSnapshot,
)
from apps.portal.services.eva_inventory_view import load_inventory_eva
from apps.portal.services.eva_monthly_closes import (
    close_due_months,
    closing_day,
)
from apps.portal.services.summary_inventory import inventory_rows
from tests.portal.test_eva_native import entry, row

pytestmark = pytest.mark.django_db
CUT = date(2026, 10, 29)


def today(monkeypatch, day):
    monkeypatch.setattr(
        "django.utils.timezone.now",
        lambda: datetime.combine(day, datetime.min.time(), tzinfo=UTC).replace(
            hour=18
        ),
    )


def observed(day=CUT, name="Ana", finish="2026-10-31", stamp=None):
    moment = datetime.combine(day, datetime.min.time(), tzinfo=UTC).replace(
        hour=18
    )
    run = EvaExtraction.objects.create(
        cut=day,
        started_at=moment,
        finished_at=moment,
        published=True,
        metrics={
            "kind": "summary_inventory",
            "eva_enriched": True,
            "source_observed_at": (stamp or moment).isoformat(),
        },
    )
    metric = row()
    metric.update(
        clockify_project_id="provider", fechaFin=finish, deliveryManager=name
    )
    source = EvaAzureSource.objects.create(
        extraction=run,
        azure_id="a",
        name="AMK.012",
        payload={
            "summary": {
                "eva_evidence": {
                    "observed_date": day.isoformat(),
                    "clockify": {"provider": [entry()]},
                }
            }
        },
    )
    frozen = {
        "scope": "S1",
        "project_id": "AMK.012_S1",
        "fields": {
            "delivery_manager": name,
            "service": "IXB",
            "project_name": "Demo",
            "client": "Acme",
        },
        "budget": "10",
        "iteration_start": "2026-10-01",
        "iteration_finish": finish,
        "stages": [
            {"stage": "Discovery", "start": "2026-10-01", "finish": finish}
        ],
        "eva_metrics": metric,
        "metrics_observed_date": day.isoformat(),
        "issues": [],
    }
    EvaScopeSnapshot.objects.create(
        source=source, project_id="AMK.012_S1", scope="S1", row=frozen
    )
    return run


@pytest.fixture(autouse=True)
def policy(settings):
    settings.EVA_MONTHLY_CLOSES_ENABLED = True
    EvaMonthlyClosePolicy.objects.update_or_create(
        pk=1, defaults={"first_month": date(2026, 10, 1)}
    )


def test_closing_day_skips_friday_saturday_sunday():
    assert closing_day(date(2026, 1, 1)) == date(2026, 1, 29)
    assert closing_day(CUT) == CUT
    assert closing_day(date(2026, 8, 1)) == date(2026, 8, 31)


def test_no_close_until_cut_day_has_ended(monkeypatch):
    today(monkeypatch, CUT)
    observed()
    assert close_due_months() == {"closed": [], "pending": []}
    assert load_inventory_eva(CUT)["monthly_close_state"] == "live"
    assert not EvaMonthlyClose.objects.exists()


def test_freezes_once_and_preserves_dates_people_hours_wi_and_risks(
    monkeypatch,
):
    original = observed()
    today(monkeypatch, date(2026, 10, 30))
    assert close_due_months()["closed"] == [CUT.isoformat()]
    close = EvaMonthlyClose.objects.get()
    saved = deepcopy(close.rows)
    assert close.extraction == original
    newer = observed(date(2026, 10, 30), "Otro DM", "2027-01-01")
    source = EvaAzureSource.objects.get(extraction=original)
    source.payload = {"summary": {"eva_evidence": {}}}
    source.save()
    assert close_due_months()["closed"] == []
    with patch(
        "apps.portal.services.summary_inventory.attach_history",
        side_effect=AssertionError("must not reproject frozen rows"),
    ):
        result = load_inventory_eva(CUT)
    assert result["inventory_rows"] == saved
    assert result["eva"].projects[0].manager == "Ana"
    assert result["eva"].projects[0].end == "31/10/26"
    assert result["eva"].projects[0].burn == 1
    assert result["monthly_close_state"] == "fixed"
    assert load_inventory_eva(date(2026, 10, 30))["extraction"] == newer
    with pytest.raises(ProtectedError):
        original.delete()
    with pytest.raises(ValueError):
        close.save()


def test_latest_successful_closing_day_source_wins(monkeypatch):
    observed(name="Primero")
    last = observed(name="Último")
    today(monkeypatch, date(2026, 10, 30))
    close_due_months()
    assert EvaMonthlyClose.objects.get().extraction == last


def test_missing_close_not_reconstructed_from_newer_source(monkeypatch):
    observed(date(2026, 10, 30))
    today(monkeypatch, date(2026, 10, 30))
    assert close_due_months()["pending"] == [CUT.isoformat()]
    result = load_inventory_eva(CUT)
    assert result["monthly_close_state"] == "pending"
    assert result["extraction"] is None
    assert result["projected_rows"] == []
    assert "Azure actual" in result["error"]
    assert not EvaMonthlyClose.objects.exists()
    with pytest.raises(CommandError, match="Sin observación válida"):
        call_command("close_eva_month", stdout=StringIO())


def test_reprocessed_older_source_cannot_pretend_to_be_closing_observation(
    monkeypatch,
):
    stamp = datetime(2026, 10, 28, 18, tzinfo=UTC)
    observed(stamp=stamp)
    today(monkeypatch, date(2026, 10, 30))
    assert close_due_months()["pending"] == [CUT.isoformat()]


def test_no_backfill_before_policy_and_search_keeps_frozen_identity(
    monkeypatch,
):
    observed(date(2026, 9, 30))
    observed()
    today(monkeypatch, date(2026, 10, 30))
    close_due_months()
    assert EvaMonthlyClose.objects.count() == 1
    assert len(inventory_rows("Ana", CUT)[1]) == 1
    assert inventory_rows("Other", CUT)[1] == []
    assert (
        load_inventory_eva(date(2026, 9, 30))["monthly_close_state"]
        == "pending"
    )


def test_capture_command_has_no_external_calls_on_other_days(monkeypatch):
    today(monkeypatch, date(2026, 10, 28))
    with patch(
        "apps.portal.management.commands.close_eva_month.call_command"
    ) as command:
        call_command("close_eva_month", capture=True, stdout=StringIO())
    command.assert_not_called()


def test_capture_command_observes_summary_before_midnight_can_roll_over(
    monkeypatch,
):
    today(monkeypatch, CUT)
    with patch(
        "apps.portal.management.commands.close_eva_month.call_command"
    ) as command:
        call_command("close_eva_month", capture=True, stdout=StringIO())
    assert [call.args[0] for call in command.call_args_list] == [
        "sync_summary_inventory",
        "sync_azure_history",
    ]


@pytest.mark.parametrize("unfinished", [True, False])
def test_unfinished_or_invalid_observation_cannot_be_frozen(
    monkeypatch, unfinished
):
    run = observed()
    if unfinished:
        run.finished_at = None
    else:
        run.metrics["source_observed_at"] = "2026-99-99"
    run.save()
    today(monkeypatch, date(2026, 10, 30))
    assert close_due_months()["pending"] == [CUT.isoformat()]
    assert not EvaMonthlyClose.objects.exists()


def test_monthly_kpis_use_close_and_stop_marking_it_provisional(monkeypatch):
    from apps.portal.services.kpi_inventory_history import load_kpi_history

    observed()
    today(monkeypatch, date(2026, 10, 30))
    close_due_months()
    observed(date(2026, 10, 30), "Otro")
    history = load_kpi_history(2026).history
    month = history.months[9]
    assert not month.partial
    assert month.observed
    assert month.view.rows[0].name == "Ana"
    assert not history.months[8].observed
    assert history.months[8].view.totals.total == 0
    assert len(history.months) == 12


def test_deferred_feature_reads_normal_inventory_and_keeps_saved_closes(
    monkeypatch, settings
):
    observed()
    today(monkeypatch, date(2026, 10, 30))
    close_due_months()
    latest = observed(date(2026, 10, 30), "DM actualizado")
    settings.EVA_MONTHLY_CLOSES_ENABLED = False
    result = load_inventory_eva(CUT)
    assert result["extraction"] == latest
    assert result["eva"].projects[0].manager == "DM actualizado"
    assert result["monthly_close_state"] == "disabled"
    assert close_due_months() == {"closed": [], "pending": []}
    assert EvaMonthlyClose.objects.count() == 1


def test_disabled_capture_is_a_noop_even_on_closing_day(monkeypatch, settings):
    today(monkeypatch, CUT)
    settings.EVA_MONTHLY_CLOSES_ENABLED = False
    with patch(
        "apps.portal.management.commands.close_eva_month.call_command"
    ) as command:
        call_command("close_eva_month", capture=True, stdout=StringIO())
    command.assert_not_called()
    assert not EvaMonthlyClose.objects.exists()
