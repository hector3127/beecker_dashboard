"""Resumenes de Operativa: conteos, Delivery Managers y dona."""

from apps.portal.constants import NO_DELIVERY_MANAGER
from apps.portal.services.portfolio_summary import (
    build_donut_segments,
    build_initials,
    count_health,
    percent_of,
    summarize_delivery_managers,
    summarize_hours,
    summarize_portfolio,
)
from tests.portal.builders import make_project


def sample_projects():
    return [
        make_project(project_id="1", health="A tiempo"),
        make_project(project_id="2", health="A tiempo", risk_level="Alto"),
        make_project(project_id="3", health="En Riesgo"),
        make_project(project_id="4", health="Crítica", delivery_manager="Ana"),
        make_project(
            project_id="5",
            status_category="En Pausa",
            health="Crítica",
            delivery_manager="Ana",
        ),
        make_project(
            project_id="6",
            status_category="Cerrado",
            delivery_manager=NO_DELIVERY_MANAGER,
        ),
    ]


def test_count_health():
    health = count_health(sample_projects())

    assert (health.on_time, health.at_risk, health.critical) == (3, 1, 2)
    assert health.total == 6


def test_percent_of_handles_zero_total():
    assert percent_of(1, 0) == 0
    assert percent_of(17, 23) == 74


def test_summary_counts_only_active_for_health():
    summary = summarize_portfolio(sample_projects())

    assert summary.in_progress == 4
    assert summary.paused == 1
    assert summary.health.on_time == 2
    assert summary.health.critical == 1
    assert summary.on_time_percent == 50


def test_summary_of_empty_portfolio():
    summary = summarize_portfolio([])

    assert summary.in_progress == 0
    assert summary.on_time_percent == 0


def test_initials():
    assert build_initials("Patricio Ochoa") == "PO"
    assert build_initials("Brandon") == "BR"
    assert build_initials("  ") == "?"


def test_delivery_managers_sorted_with_unassigned_last():
    managers = summarize_delivery_managers(sample_projects())

    assert [item.name for item in managers] == [
        "Laura Vega",
        "Ana",
        NO_DELIVERY_MANAGER,
    ]
    laura = managers[0]
    assert laura.in_progress == 3
    assert laura.health.on_time == 2
    assert laura.high_risk == 1
    assert laura.on_time_width == 66.7
    assert laura.at_risk_width == 33.3
    ana = managers[1]
    assert ana.paused == 1
    assert ana.critical_width == 100.0


def test_delivery_manager_without_active_projects_has_zero_widths():
    managers = summarize_delivery_managers(
        [make_project(status_category="En Pausa")],
    )

    assert managers[0].in_progress == 0
    assert managers[0].on_time_width == 0.0


def test_donut_segments_cover_the_circle():
    summary = summarize_portfolio(sample_projects())
    segments = build_donut_segments(summary.health)

    assert [item.label for item in segments] == [
        "En tiempo",
        "En riesgo",
        "Críticos",
    ]
    assert [item.count for item in segments] == [2, 1, 1]
    assert segments[0].offset == 0.0
    assert segments[1].offset == -segments[0].dash
    assert round(sum(item.dash for item in segments), 0) == 402


def test_donut_without_projects_has_no_arcs():
    segments = build_donut_segments(count_health([]))

    assert all(item.dash == 0.0 for item in segments)
    assert all(item.percent == 0 for item in segments)


def test_hours_summary_uses_active_projects_only():
    projects = sample_projects() + [
        make_project(
            project_id="9",
            status_category="Cerrado",
            budget_hours=1000.0,
            burn_hours=1000.0,
        ),
    ]
    hours = summarize_hours(projects)

    assert hours.budget_hours == 400
    assert hours.burn_hours == 160
    assert hours.etc_hours == 240
    assert hours.progress_percent == 40


def test_hours_summary_without_budget():
    assert summarize_hours([]).progress_percent == 0
