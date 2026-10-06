from datetime import datetime

from apps.dashboard.schemas.dashboard_models import PortfolioCosts
from apps.dashboard.services.portfolio_costs import (
    calculate_portfolio_costs,
    calculate_project_margin,
)
from apps.dashboard.services.weekly_hours import calculate_weekly_hours
from tests.dashboard.sample_data import NOW, TIME_ENTRIES, build_entry


def test_red_flags_count_long_entries_and_excessive_days():
    entries = [
        build_entry("1", "P-1", "Ana", datetime(2026, 10, 1), 4),
        build_entry("2", "P-1", "Ana", datetime(2026, 10, 1), 3),
        build_entry("3", "P-1", "Ana", datetime(2026, 10, 1), 3.5),
        build_entry("4", "P-1", "Luis", datetime(2026, 10, 1), 1),
        build_entry("5", "P-9", "Luis", datetime(2026, 10, 1), 9),
    ]

    weekly = calculate_weekly_hours({"P-1"}, entries, NOW)

    assert weekly.red_flag_count == 3
    assert weekly.total_hours == 11.5


def test_old_entries_are_outside_the_week():
    weekly = calculate_weekly_hours({"P-1", "P-2"}, TIME_ENTRIES, NOW)

    assert weekly.hours_by_project == {"P-1": 11, "P-2": 2}


def test_costs_use_rates_by_normalized_name():
    costs = calculate_portfolio_costs(
        [
            {
                "Proyecto": "P-1",
                "Nombre del recurso": "José",
                "Horas Estimadas": 10,
            },
            {
                "Proyecto": "",
                "Nombre del recurso": "José",
                "Horas Estimadas": 99,
            },
        ],
        {"jose": 20.0},
        TIME_ENTRIES,
    )

    assert costs.estimated_cost_by_project == {"P-1": 200.0}
    assert costs.actual_cost_by_project["P-2"] == 1220.0


def test_margin_is_none_without_estimate():
    costs = PortfolioCosts({"P-1": 200.0}, {"P-1": 50.0})

    assert calculate_project_margin("P-1", costs) == 75.0
    assert calculate_project_margin("P-2", costs) is None
