from apps.portal.services.revenue_costs import project_ids
from tests.fakes import InMemorySheetRepository


def test_costs_exclude_completed_previous_year_mpb_projects():
    reader = InMemorySheetRepository({
        "MPB": [["ID", "INICIO", "FIN"],
                ["OLD", "2025-09-17", "2025-12-08"],
                ["CROSS", "2025-12-01", "2026-02-01"],
                ["UNKNOWN", "", ""],
                ["CURRENT", "2026-01-01", "2026-09-01"]],
        "DataRevenue": [["Status", "Account", "", "", "ID", "", "Date"],
                        *[["Collected", "Acme", "", "", pid, "", "2026-06-01"]
                          for pid in ["OLD", "CROSS", "UNKNOWN", "CURRENT", "ABSENT"]]]})
    assert project_ids(reader, "Acme") == ["ABSENT", "CROSS", "CURRENT", "UNKNOWN"]
