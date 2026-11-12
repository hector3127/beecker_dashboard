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
    cache.set(burn_key(projects[0]), {"burn": 150})
    cache.set(burn_key(projects[1]), {"burn": 900})
    with patch(
        "apps.portal.services.executive_operations.population",
        return_value=projects,
    ):
        result = operations_summary()
        assert (
            result["budget"] == 1000
            and result["advance"] == 105
            and result["etc"] == -50
        )
        assert not result["partial"]
        cache.delete(burn_key(projects[1]))
        result = operations_summary()
        assert (
            result["advance"] == 150
            and result["etc"] == -50
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
