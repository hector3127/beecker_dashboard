from unittest.mock import Mock, patch
from datetime import datetime
from django.core.cache import cache
from apps.portal.services.executive_operations import operations_summary, burn_key, population


def test_operations_weighted_totals_and_negative_etc():
    cache.clear()
    projects=[{"id":"P1","budget":100,"start":"2026-01-01","end":"2026-09-01"},{"id":"P2","budget":900,"start":"2025-01-01","end":"2026-09-01"}]
    cache.set(burn_key(projects[0]),{"burn":150})
    cache.set(burn_key(projects[1]),{"burn":900})
    with patch("apps.portal.services.executive_operations.population",return_value=projects):
        result=operations_summary()
        assert result["budget"]==1000 and result["advance"]==105 and result["etc"]==-50
        assert not result["partial"]
        cache.delete(burn_key(projects[1]))
        result=operations_summary()
        assert result["advance"]==150 and result["etc"]==-50 and result["partial"]
        assert result["pending_ids"]==["P2"]


def test_population_deduplicates_phases_and_excludes_pre_2026():
    cache.clear()
    from tests.fakes import InMemorySheetRepository
    from tests.portal.test_kpi_sources import LEFT, MPB

    def event(pid, status, start, finish, budget):
        return ["Ana", "Acme", pid, "IxB", pid, "", status, start, finish, budget]

    header = list(LEFT)
    header[9] = "Budget (Hrs)"
    history = [header,
               event("P1", "Discovery OP", "2025-12-01", "2025-12-31", 100),
               event("P1", "Completed", "2026-01-31", "2026-01-31", 100),
               event("OLD", "Discovery OP", "2025-01-01", "2025-01-02", 200),
               event("OLD", "Completed", "2025-12-31", "2025-12-31", 200),
               event("FUTURE", "Discovery OP", "2027-01-01", "2027-12-31", 300)]
    reader = InMemorySheetRepository({"MPB": [MPB], "Historico_Proyectos": history})
    projects = population(reader)
    assert len(projects) == 1 and projects[0]["id"] == "P1"
    assert projects[0]["budget"] == 100
    assert projects[0]["start"] == "2025-12-01"
