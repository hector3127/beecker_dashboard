"""Proyectos que requieren decision."""

from apps.portal.services.decisions import (
    ACTION_BUDGET,
    ACTION_DELAY,
    ACTION_RISK,
    build_decisions,
)
from tests.portal.builders import make_project


def test_healthy_and_inactive_projects_are_left_out():
    projects = [
        make_project(project_id="1"),
        make_project(
            project_id="2", health="Crítica", status_category="Cerrado"
        ),
    ]

    assert build_decisions(projects) == []


def test_over_budget_critical_project_asks_for_budget_decision():
    decisions = build_decisions(
        [make_project(health="Crítica", burn_hours=125.0)],
    )

    assert decisions[0].is_critical
    assert decisions[0].reason == (
        "Ya usó 125% de su presupuesto: excede en 25%."
    )
    assert decisions[0].action == ACTION_BUDGET


def test_delayed_project_asks_for_recovery_plan():
    decisions = build_decisions(
        [make_project(health="En Riesgo", delay_days=18)],
    )

    assert not decisions[0].is_critical
    assert "18 días atrasado" in decisions[0].reason
    assert decisions[0].action == ACTION_DELAY


def test_high_risk_without_delay_asks_to_review_risks():
    decisions = build_decisions(
        [make_project(health="En Riesgo", risk_level="Alto")],
    )

    assert decisions[0].action == ACTION_RISK


def test_at_risk_without_other_signal_uses_generic_reason():
    decisions = build_decisions([make_project(health="En Riesgo")])

    assert "en riesgo" in decisions[0].reason
    assert decisions[0].action == ACTION_DELAY


def test_critical_first_then_more_delay_and_limited_to_five():
    projects = [
        make_project(
            project_id=str(index),
            name=f"P{index}",
            health="En Riesgo",
            delay_days=index,
        )
        for index in range(1, 7)
    ]
    projects.append(make_project(project_id="c", name="Crit", health="Crítica"))
    decisions = build_decisions(projects)

    assert len(decisions) == 5
    assert decisions[0].name == "Crit"
    assert [item.name for item in decisions[1:]] == ["P6", "P5", "P4", "P3"]


def test_project_without_budget_does_not_divide_by_zero():
    decisions = build_decisions(
        [make_project(health="Crítica", budget_hours=0.0, delay_days=3)],
    )

    assert decisions[0].action == ACTION_DELAY
