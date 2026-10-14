"""Regression checks for the operational sources used by EVA cards."""

import warnings
from types import SimpleNamespace
from unittest.mock import patch

from django.core.cache import cache
from django.core.cache.backends.base import CacheKeyWarning

from apps.portal.services.eva1 import build_eva1_view
from apps.portal.services.eva2 import build_eva2_view
from apps.portal.services.eva_loader import Eva1Load, Eva2Load, build_eva1_card
from apps.portal.services.operational_sources import (
    eva_projects,
    legacy_capacity,
    manager_monthly_history,
    tagged_investment,
)
from apps.portal.services.portfolio_summary import summarize_portfolio
from core.time_entries.models import TimeEntry


def test_investment_cache_accepts_long_ids_and_tracks_project_dates():
    cache.clear()
    project = SimpleNamespace(
        project_id="Proyecto con espacios " * 20,
        start="2026-01-01",
        end="2026-12-31",
    )
    with (
        warnings.catch_warnings(),
        patch(
            "apps.portal.services.operational_sources.build_sheet_repository"
        ),
        patch(
            "apps.portal.services.operational_sources.build_clockify_loader"
        ) as loader,
    ):
        warnings.simplefilter("error", CacheKeyWarning)
        loader.return_value.load_project.return_value = []
        first = tagged_investment([project])
        assert tagged_investment([project]) == first
        assert loader.return_value.load_project.call_count == 1
        project.end = "2026-11-30"
        tagged_investment([project])
        assert loader.return_value.load_project.call_count == 2


def test_manager_cache_accepts_spaces_and_keeps_managers_separate():
    cache.clear()
    with (
        warnings.catch_warnings(),
        patch(
            "apps.portal.services.operational_sources.build_sheet_repository"
        ) as repository,
        patch(
            "apps.portal.services.operational_sources.tagged_investment",
            side_effect=[
                {"complete": True, "monthly": [], "marker": "first"},
                {"complete": True, "monthly": [], "marker": "second"},
            ],
        ) as investment,
    ):
        warnings.simplefilter("error", CacheKeyWarning)
        repository.return_value.read_as_objects.return_value = []
        repository.return_value.read_values.return_value = []
        repository.return_value.sheet_exists.return_value = False
        manager = "Alberto Carlos Rodríguez Veloz"
        first = manager_monthly_history(manager, [])
        assert manager_monthly_history(manager, []) == first
        assert (
            manager_monthly_history("Otro Delivery Manager", [])["marker"]
            == "second"
        )
        assert investment.call_count == 2


def test_eva_renewal_and_health_population():
    aer = Eva1Load(
        build_eva1_view(
            [
                {
                    "idProyecto": "A",
                    "renewalDias": 10,
                    "budget": 100,
                    "burn": 95,
                    "avance": 95,
                }
            ]
        ),
        "",
    )
    ixb = Eva2Load(
        build_eva2_view(
            [
                {
                    "idProyecto": "I",
                    "status": "Deployment",
                    "fechaFin": "2027-12-31",
                    "desviacionDias": 50,
                    "budget": 100,
                    "avance": 50,
                },
                {
                    "idProyecto": "P",
                    "status": "Suspendido",
                    "desviacionDias": -5,
                },
            ]
        ),
        "",
    )
    assert build_eva1_card(aer).time_cost.time_days == 10
    summary = summarize_portfolio(eva_projects(ixb, aer))
    assert summary.in_progress == 2 and summary.paused == 1
    assert summary.health.on_time == 1 and summary.health.at_risk == 1


def test_tagged_hours_are_deduplicated():
    cache.clear()
    entry = TimeEntry(
        "same",
        "IXB.A",
        "Test",
        None,
        3,
        False,
        0,
        tags=("INV_OPERATIVA", "INV_COMERCIAL"),
    )
    projects = build_eva2_view(
        [{"idProyecto": "IXB.A", "status": "Discovery"}]
    ).projects
    with (
        patch(
            "apps.portal.services.operational_sources.build_sheet_repository"
        ),
        patch(
            "apps.portal.services.operational_sources.build_clockify_loader"
        ) as loader,
    ):
        loader.return_value.load_project.return_value = [entry, entry]
        assert tagged_investment(projects)["totals"] == {
            "operational": 3,
            "commercial": 3,
        }


def test_daily_capacity_excess_does_not_reduce_another_days_capacity():
    cache.clear()
    with (
        patch(
            "apps.portal.services.operational_sources.get_capacity_base",
            return_value={
                "ok": True,
                "filas": [
                    {
                        "recurso": "Test",
                        "idProyecto": "X",
                        "regla": {"afecta": True, "facturable": "Facturable"},
                    }
                ],
            },
        ),
        patch(
            "apps.portal.services.operational_sources.get_capacity_project_data",
            return_value={"ok": True, "daily": {"test": {"2026-10-01": 10}}},
        ),
    ):
        value = legacy_capacity("2026-10")
        assert value["billable"] == 10 and value["over"] == 1
        assert value["available"] == value["base"] - 8


def test_clockify_mpb_dates_use_full_eva_layout():
    from datetime import date

    from apps.clockify.services.date_ranges import ProjectDateRangeResolver

    class Reader:
        def sheet_exists(self, name):
            return True

        def read_values(self, name):
            headers = [""] * 64
            row = [""] * 64
            for index, value in [
                (1, "CLIENTE"),
                (2, "ID"),
                (5, "SERVICE"),
                (19, "ESTATUS"),
                (40, "INICIO"),
                (41, "FIN"),
            ]:
                headers[index] = value
            for index, value in [
                (2, "AER.AWN.001"),
                (5, "AER"),
                (40, "06/10/2025"),
                (41, "06/10/2026"),
            ]:
                row[index] = value
            return [headers, row]

    result = ProjectDateRangeResolver(Reader(), date(2026, 10, 13)).resolve(
        "AER.AWN.001"
    )
    assert result.start_date == date(2025, 10, 6)
    assert result.end_date == date(2026, 10, 6)


def test_capacity_estimates_only_resources_with_records():
    cache.clear()
    base = {
        "ok": True,
        "filas": [
            {
                "recurso": "Recorded",
                "idProyecto": "X",
                "horasEstimadas": 40,
                "regla": {"afecta": True, "facturable": "Facturable"},
            },
            {
                "recurso": "No records",
                "idProyecto": "X",
                "horasEstimadas": 100,
                "regla": {"afecta": True, "facturable": "Facturable"},
            },
        ],
    }
    with (
        patch(
            "apps.portal.services.operational_sources.get_capacity_base",
            return_value=base,
        ),
        patch(
            "apps.portal.services.operational_sources.get_capacity_project_data",
            return_value={"ok": True, "daily": {"recorded": {"2026-10-01": 6}}},
        ),
    ):
        result = legacy_capacity("2026-10")
        assert result["estimated"] == 40
        assert result["consumed"] == 6
        assert result["registered_people"] == 1


def test_health_requires_short_time_and_low_remaining_hours():
    from datetime import date
    from types import SimpleNamespace

    from apps.portal.services.operational_sources import remaining_days

    projects = build_eva2_view(
        [
            {
                "idProyecto": "TIME",
                "fechaFin": "2026-10-20",
                "budget": 100,
                "burn": 20,
                "avance": 20,
            },
            {
                "idProyecto": "RISK",
                "fechaFin": "2026-10-20",
                "budget": 100,
                "burn": 95,
                "avance": 95,
            },
            {
                "idProyecto": "HOURS",
                "fechaFin": "2026-12-31",
                "budget": 100,
                "burn": 101,
                "avance": 101,
            },
            {
                "idProyecto": "DATE",
                "fechaFin": "2026-10-12",
                "budget": 100,
                "burn": 20,
                "avance": 20,
            },
            {
                "idProyecto": "LOW",
                "fechaFin": "2026-12-31",
                "budget": 100,
                "burn": 95,
                "avance": 95,
            },
        ]
    )
    with patch(
        "apps.portal.services.operational_sources.timezone.localdate",
        return_value=date(2026, 10, 13),
    ):
        rows = eva_projects(
            SimpleNamespace(view=projects),
            SimpleNamespace(view=SimpleNamespace(projects=[])),
        )
        assert {row.project_id: row.health for row in rows} == {
            "TIME": "A tiempo",
            "RISK": "En Riesgo",
            "HOURS": "Cr\u00edtica",
            "DATE": "Cr\u00edtica",
            "LOW": "A tiempo",
        }
        assert (
            remaining_days(
                next(p for p in projects.projects if p.project_id == "TIME")
            )
            == 7
        )


def test_risks_use_azure_titles_and_dashboard_open_rows():
    from apps.portal.services.operational_sources import aer_open_risks

    cache.clear()
    assert build_eva2_view(
        [{"idProyecto": "I", "riesgos": ["Azure risk"]}]
    ).projects[0].risk_titles == ("Azure risk",)
    with patch(
        "apps.portal.services.operational_sources.build_sheet_repository"
    ) as repository:
        repository.return_value.read_as_objects.return_value = [
            {"ID_Proyecto": "A", "Riesgo": "Open risk", "Estado": "Abierto"},
            {"ID_Proyecto": "A", "Riesgo": "Closed risk", "Estado": "Cerrado"},
            {"ID_Proyecto": "B", "Riesgo": "Other risk", "Estado": "Abierto"},
        ]
        assert aer_open_risks(["A", "Z"]) == {"A": 1, "Z": 0}
