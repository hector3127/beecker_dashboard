from unittest.mock import patch

from django.core.cache import cache

from apps.portal.services.executive_operations import (
    burn_key,
    operations_summary,
    population,
)


def test_operations_weighted_totals_and_negative_etc():
    cache.clear()
    projects = [
        {"id": "P1", "budget": 100, "start": "2026-01-01", "end": "2026-09-01"},
        {"id": "P2", "budget": 900, "start": "2025-01-01", "end": "2026-09-01"},
    ]
    for project, hours in zip(projects, (150, 900), strict=True):
        cache.set(
            burn_key(project),
            {
                "burn": hours,
                "metric_entries": {
                    project["id"]: {
                        "hours": hours,
                        "month": "2026-08",
                        "billable": True,
                        "operational": False,
                    },
                    "uncovered": {
                        "hours": 20,
                        "month": "2026-09",
                        "billable": True,
                        "operational": False,
                    },
                },
            },
        )
    with (
        patch(
            "apps.portal.services.executive_operations.population",
            return_value=projects,
        ),
        patch(
            "apps.portal.services.executive_operations.installed_capacity_metrics",
            return_value={
                "facturability_capacity": 800,
                "facturability_consumed_hours": 1050,
                "facturability": 131.25,
                "facturability_pending_months": [],
                "facturability_partial": True,
            },
        ),
        patch(
            "apps.portal.services.executive_operations.global_facturability",
            return_value={"facturability_capacity": 400},
        ),
    ):
        result = operations_summary()
        assert (
            result["budget"] == 1000
            and result["advance"] == 131.25
            and result["etc"] == -250
        )
        assert not result["partial"]
        assert result["capacity_base"] == 800
        assert result["facturability_capacity"] == 400
        cache.delete(burn_key(projects[1]))
        result = operations_summary()
        assert (
            result["advance"] == 131.25
            and result["etc"] == -250
            and result["partial"]
        )
        assert result["pending_ids"] == ["P2"]


def test_population_excludes_azure_scopes_outside_period(monkeypatch):
    cache.clear()
    from tests.fakes import InMemorySheetRepository
    from tests.portal.test_kpi_sources import MPB

    monkeypatch.setattr(
        "apps.portal.services.executive_population.azure_scopes",
        lambda: [
            {
                "project_id": pid,
                "fields": {"service": "IxB"},
                "iteration_start": start,
                "iteration_finish": finish,
                "budget": "100",
            }
            for pid, start, finish in (
                ("P1", "2025-12-01", "2026-01-31"),
                ("OLD", "2025-01-01", "2025-12-31"),
                ("FUTURE", "2027-01-01", "2027-12-31"),
            )
        ],
    )
    reader = InMemorySheetRepository({"MPB": [MPB]})
    projects = population(reader)
    assert len(projects) == 1 and projects[0]["id"] == "P1"
    assert projects[0]["budget"] == 100
    assert projects[0]["start"] == "2025-12-01"
