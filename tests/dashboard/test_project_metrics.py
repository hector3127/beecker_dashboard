from dataclasses import replace
from datetime import datetime

from apps.dashboard.schemas.dashboard_models import PortfolioCosts
from apps.dashboard.schemas.records import ProjectRecord, RiskRecord
from apps.dashboard.services.project_metrics import (
    build_project_metrics,
    calculate_progress_percent,
)
from apps.dashboard.services.project_status import (
    calculate_project_risk_level,
    categorize_project_status,
)

NOW = datetime(2026, 10, 2, 12, 0)

EMPTY_COSTS = PortfolioCosts({}, {})


BASE_PROJECT = ProjectRecord(
    project_id="P-1",
    display_name="Alpha",
    client="ACME",
    status="Development",
    service="",
    budget_hours=100.0,
    start_date=datetime(2026, 1, 1),
    end_date=datetime(2026, 12, 31),
)


def build_project(**overrides):
    return replace(BASE_PROJECT, **overrides)


def test_status_categories_match_original_mapping():
    assert categorize_project_status(" Discovery ") == "Planificación"
    assert categorize_project_status("Deployment") == "Activo"
    assert categorize_project_status("Suspendido") == "En Pausa"
    assert categorize_project_status("Cancelado") == "Cerrado"
    assert categorize_project_status("Desconocido") == "Activo"


def test_risk_level_uses_worst_open_risk():
    risks = [
        RiskRecord("P-1", "Bajo", "Abierto", ""),
        RiskRecord("P-1", "Alto", "Cerrado", ""),
        RiskRecord("P-1", "Medio", "Abierto", ""),
    ]

    assert calculate_project_risk_level("P-1", risks) == "Medio"
    assert calculate_project_risk_level("P-2", risks) == ""


def test_progress_is_capped_at_one_hundred():
    assert calculate_progress_percent(100, 150) == 100
    assert calculate_progress_percent(0, 10) == 0


def test_project_over_budget_is_critical():
    metrics = build_project_metrics(
        build_project(budget_hours=10.0),
        {"P-1": 12.345},
        [],
        EMPTY_COSTS,
        NOW,
    )

    assert metrics.burn_hours == 12.35
    assert metrics.etc_hours == -2.35
    assert metrics.health == "Crítica"


def test_delay_days_only_when_not_closed():
    late_project = build_project(end_date=datetime(2026, 9, 1, 12, 0))
    closed_project = build_project(
        status="Cancelado",
        end_date=datetime(2026, 9, 1, 12, 0),
    )

    late_metrics = build_project_metrics(late_project, {}, [], EMPTY_COSTS, NOW)
    closed_metrics = build_project_metrics(
        closed_project,
        {},
        [],
        EMPTY_COSTS,
        NOW,
    )

    assert late_metrics.delay_days == 31
    assert late_metrics.health == "Crítica"
    assert closed_metrics.delay_days == 0


def test_trend_down_marks_project_at_risk():
    metrics = build_project_metrics(
        build_project(),
        {"P-1": 5},
        [],
        EMPTY_COSTS,
        NOW,
    )

    assert metrics.trend == "down"
    assert metrics.health == "En Riesgo"


def test_without_dates_trend_is_up():
    metrics = build_project_metrics(
        build_project(start_date=None, end_date=None),
        {},
        [],
        EMPTY_COSTS,
        NOW,
    )

    assert metrics.trend == "up"
    assert metrics.health == "A tiempo"
