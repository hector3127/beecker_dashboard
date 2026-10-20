from apps.portal.services.cost_project_inventory import inventory
from tests.fakes import InMemorySheetRepository
from tests.portal.test_kpi_sources import MPB


def test_financial_inventory_uses_service_specific_sources():
    reader = InMemorySheetRepository(
        {
            "DataRevenue": [
                ["Status", "Account", "", "", "ID", "", "Date", "Amount"],
                [
                    "Confirmed",
                    "Cadena Comercial Oxxo",
                    "",
                    "",
                    "CCO.002",
                    "",
                    "2026-10-01",
                    100,
                ],
            ],
            "MPB": [
                MPB,
                [
                    "OXXO",
                    "AER.1",
                    "Cell",
                    "AER",
                    "2026-01-01",
                    "2026-12-31",
                    "Active",
                ],
                [
                    "OXXO",
                    "TYM.1",
                    "Service",
                    "T&M",
                    "2026-01-01",
                    "2026-12-31",
                    "Active",
                ],
                [
                    "OXXO",
                    "IXB.MPB.ONLY",
                    "Wrong source",
                    "IxB",
                    "2026-01-01",
                    "2026-12-31",
                    "Active",
                ],
            ],
            "Historico_Proyectos": [
                [],
                [
                    "Ana",
                    "OXXO",
                    "CCO.002_S1",
                    "IxB",
                    "Migration",
                    "",
                    "Development",
                    "2026-05-01",
                    "2026-06-01",
                ],
                [
                    "Ana",
                    "OXXO",
                    "RAAS.1",
                    "RaaS",
                    "Bot",
                    "",
                    "Development",
                    "2026-01-01",
                    "2026-12-31",
                ],
                [
                    "Ana",
                    "OXXO",
                    "SAAS.1",
                    "SaaS",
                    "App",
                    "",
                    "Development",
                    "2026-01-01",
                    "2026-12-31",
                ],
                [
                    "Ana",
                    "OXXO",
                    "AER.HISTORY.ONLY",
                    "AER",
                    "Wrong source",
                    "",
                    "Development",
                    "2026-01-01",
                    "2026-12-31",
                ],
            ],
        }
    )
    projects = inventory(reader)
    assert set(projects) == {"aer.1", "tym.1", "cco.002", "raas.1", "saas.1"}
    assert all(
        p["accounts"] == {"Cadena Comercial Oxxo"} for p in projects.values()
    )


def test_unregistered_cr_is_grouped_under_pure_id():
    reader = InMemorySheetRepository(
        {
            "DataRevenue": [
                ["Status", "Account", "", "", "ID"],
                ["Collected", "Heineken Mexico", "", "", "MCC.014"],
            ],
            "Historico_Proyectos": [
                [],
                [
                    "Ana",
                    "Heineken",
                    "MCC.014_CR2",
                    "RaaS",
                    "Change",
                    "",
                    "Development",
                    "2026-01-01",
                    "2026-10-01",
                ],
            ],
        }
    )
    assert set(inventory(reader)) == {"mcc.014"}


def test_explicit_revenue_link_overrides_old_mpb_period_for_detail_membership():
    from apps.portal.services.revenue_costs import project_ids

    reader = InMemorySheetRepository(
        {
            "DataRevenue": [
                ["Status", "Account", "", "", "ID", "", "Date", "Amount"],
                [
                    "Collected",
                    "Arca Continental México",
                    "ARC-MX-IXB-001",
                    "RPA Bots",
                    "SBM.012",
                    "",
                    "2026-08-18",
                    2000,
                ],
            ],
            "MPB": [
                MPB,
                [
                    "Arca Continental México",
                    "SBM.012",
                    "Old contract",
                    "IxB",
                    "2025-01-01",
                    "2025-12-31",
                    "Finalizado",
                ],
            ],
        }
    )
    assert project_ids(reader, "Arca Continental México") == ["SBM.012"]
    assert project_ids(reader, "Other account") == []
