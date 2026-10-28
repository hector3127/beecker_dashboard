"""Exact iteration dates, sibling isolation and calendar ambiguity."""

from datetime import date

from apps.portal.services.summary_iterations import (
    calendar_fields,
    iteration_blocks,
)


def stage(name, start, finish):
    return {
        "name": name,
        "identifier": name,
        "path": "root/" + name,
        "attributes": {
            "startDate": start + "T00:00:00Z",
            "finishDate": finish + "T00:00:00Z",
        },
    }


def test_exact_scopes_and_calendar_dates():
    tree = {
        "name": "AMK.012",
        "children": [
            {
                "name": "General_CR2",
                "children": [
                    stage("Discovery_CR2", "2025-12-22", "2026-01-02"),
                    stage("Development_CR2", "2026-01-05", "2026-01-27"),
                    stage("Deployment_CR2", "2026-01-28", "2026-04-24"),
                ],
            },
            {
                "name": "General_CR",
                "children": [
                    stage("Deployment_CR", "2025-11-24", "2025-11-28")
                ],
            },
            {
                "name": "General_S10",
                "children": [
                    stage("Discovery_S10", "2025-01-01", "2025-02-01")
                ],
            },
        ],
    }
    blocks = iteration_blocks(tree)
    assert set(blocks) == {"CR", "CR2", "S10"}
    result = calendar_fields(blocks["CR2"], date(2026, 1, 29))
    assert result["iteration_start"] == "2025-12-22"
    assert result["iteration_finish"] == "2026-04-24"
    assert result["calendar_stage"] == "Deployment"
    assert result["stages"][0]["identifier"] == "Discovery_CR2"
    assert (
        calendar_fields(blocks["CR2"], date(2026, 10, 28))["calendar_stage"]
        == "Fuera de rango programado"
    )


def test_overlap_missing_invalid_and_duplicate_dates():
    blocks = iteration_blocks(
        {
            "name": "General_S1",
            "children": [
                stage("Discovery_S1", "2026-01-01", "2026-02-01"),
                stage("Development_S1", "2026-02-01", "2026-03-01"),
            ],
        }
    )
    result = calendar_fields(blocks["S1"], date(2026, 2, 1))
    assert result["calendar_stage"] == "Solapamiento de etapas"
    assert result["iteration_finish"] == "2026-03-01"
    blocks["S1"][0]["start"] = "invalid"
    result = calendar_fields(blocks["S1"], date(2026, 2, 1))
    assert result["calendar_stage"] == "Development"
    assert result["iteration_start"] is None
    assert result["iteration_issues"]


def test_empty_deployment_uses_last_registered_finish():
    blocks = iteration_blocks(
        {
            "name": "General_S1",
            "children": [
                stage("Discovery_S1", "2026-05-14", "2026-05-26"),
                stage("Development_S1", "2026-05-27", "2026-06-22"),
                {"name": "Deployment_S1", "attributes": {}},
            ],
        }
    )
    result = calendar_fields(blocks["S1"], date(2026, 6, 1))
    assert result["iteration_start"] == "2026-05-14"
    assert result["iteration_finish"] == "2026-06-22"
    assert result["calendar_stage"] == "Development"


def test_explicit_suspension_period_has_priority_over_calendar():
    blocks = iteration_blocks(
        {
            "name": "General_S1",
            "children": [
                stage("Discovery_S1", "2026-01-01", "2026-01-31"),
                stage("Deployment_S1", "2026-02-01", "2026-03-01"),
                stage("Suspendido_S1", "2026-01-20", "2026-02-10"),
            ],
        }
    )
    assert (
        calendar_fields(blocks["S1"], date(2026, 1, 19))["calendar_stage"]
        == "Discovery"
    )
    assert (
        calendar_fields(blocks["S1"], date(2026, 1, 20))["calendar_stage"]
        == "Suspendido"
    )
    assert (
        calendar_fields(blocks["S1"], date(2026, 2, 10))["calendar_stage"]
        == "Suspendido"
    )
    assert (
        calendar_fields(blocks["S1"], date(2026, 2, 11))["calendar_stage"]
        == "Deployment"
    )
