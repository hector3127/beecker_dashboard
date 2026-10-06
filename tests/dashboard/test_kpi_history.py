import copy

from apps.dashboard.schemas.dashboard_models import PortfolioKpis
from apps.dashboard.services.kpi_history import (
    KpiHistoryService,
    calculate_delta,
)
from tests.dashboard.sample_data import NOW, SHEETS
from tests.fakes import InMemorySheetRepository

KPIS = PortfolioKpis(
    total_projects=1,
    active_projects=1,
    paused_projects=0,
    planning_projects=0,
    closed_projects=0,
    high_risks=0,
    budget_total=0,
    burn_total=0,
    etc_total=0,
    average_velocity=0,
    average_progress=0,
    weekly_hours=0,
    weekly_red_flags=0,
    average_margin=None,
    burn_percent=0,
    etc_percent=0,
)


def test_delta_handles_empty_and_invalid_values():
    assert calculate_delta(5, "") is None
    assert calculate_delta(5, "n/a") is None
    assert calculate_delta(None, 3) is None
    assert calculate_delta(5, "2.5") == 2.5


def test_no_history_sheet_returns_empty_delta():
    repository = InMemorySheetRepository({})

    delta = KpiHistoryService(repository, repository).calculate_weekly_delta(
        KPIS,
        NOW,
    )

    assert delta.active_projects is None


def test_snapshot_creates_sheet_and_writes_empty_margin():
    repository = InMemorySheetRepository({})

    KpiHistoryService(repository, repository).save_snapshot(KPIS, NOW)

    assert repository.sheets["Dashboard_Historico_KPIs"][0][0] == "Fecha"
    assert repository.appended_rows[0][1][-1] == ""


def test_picks_snapshot_closest_to_seven_days():
    repository = InMemorySheetRepository(copy.deepcopy(SHEETS))

    delta = KpiHistoryService(repository, repository).calculate_weekly_delta(
        KPIS,
        NOW,
    )

    assert delta.active_projects == -2
