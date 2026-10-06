"""Valores esperados obtenidos al ejecutar el getDashboardData() original
con estos mismos datos (ver tests/dashboard/sample_data.py)."""

import copy

from apps.dashboard.schemas.dashboard_filters import parse_dashboard_filters
from apps.dashboard.services.orchestrator import DashboardOrchestrator
from core.time_entries.models import TimeEntryBatch
from tests.dashboard.sample_data import NOW, SHEETS, TIME_ENTRIES
from tests.fakes import InMemorySheetRepository, StaticTimeEntryProvider


def build_dashboard(filters_payload=None, batch=None):
    repository = InMemorySheetRepository(copy.deepcopy(SHEETS))
    provider = StaticTimeEntryProvider(
        batch or TimeEntryBatch(entries=TIME_ENTRIES),
    )
    orchestrator = DashboardOrchestrator(repository, repository, provider)
    result = orchestrator.build_dashboard(
        parse_dashboard_filters(filters_payload),
        NOW,
    )
    return result, repository


def test_general_view_matches_original_kpis():
    result, _ = build_dashboard()
    kpis = result.payload["kpis"]

    assert kpis["totalProyectos"] == 5
    assert kpis["activos"] == 2
    assert kpis["enPausa"] == 1
    assert kpis["planificacion"] == 1
    assert kpis["cerrados"] == 1
    assert kpis["riesgosAltos"] == 1
    assert kpis["budgetTotal"] == 230
    assert kpis["burnTotal"] == 103
    assert kpis["etcTotal"] == 127
    assert kpis["velocityPromedio"] == 23
    assert kpis["avancePromedio"] == 28
    assert kpis["horasSemanaReal"] == 13
    assert kpis["focoRojoSemana"] == 2
    assert kpis["margenPromedio"] == -5.9
    assert kpis["burnPct"] == 45
    assert kpis["etcPct"] == 55
    assert kpis["delta"] == {
        "activos": -1,
        "avancePromedio": 8,
        "horasSemanaReal": 8,
        "riesgosAltos": -1,
        "focoRojoSemana": 1,
        "margenPromedio": -18.4,
    }


def test_general_view_matches_original_datasets():
    result, _ = build_dashboard()
    payload = result.payload

    assert payload["saludPortafolio"] == {
        "aTiempo": 1,
        "enRiesgo": 2,
        "critica": 2,
        "estadoGeneral": "Regular",
    }
    assert [item["nombre"] for item in payload["avancePorProyecto"]] == [
        "Beta",
        "Alpha",
        "P-3",
        "Delta",
        "Epsilon",
    ]
    assert payload["rentabilidad"][0]["margen"] == 40.8
    assert payload["rentabilidad"][1]["margen"] == -52.5
    assert [risk["impacto"] for risk in payload["topRiesgos"]] == [
        "Alto",
        "Medio",
        "Bajo",
    ]
    assert [alert["tipo"] for alert in payload["alertas"]] == [
        "error",
        "error",
        "warning",
    ]

    first_row = payload["tabla"][0]
    assert first_row["burn"] == 41
    assert first_row["desviacion"] == 33
    assert first_row["deliveryManager"] == "Laura"
    assert first_row["horasSemana"] == 11
    assert first_row["tendencia"] == "down"


def test_general_view_saves_snapshot_and_is_cacheable():
    result, repository = build_dashboard()

    assert result.is_cacheable
    assert len(repository.appended_rows) == 1
    sheet_name, row = repository.appended_rows[0]
    assert sheet_name == "Dashboard_Historico_KPIs"
    assert row[1:] == [2, 28, 13, 1, 2, -5.9]


def test_filtered_view_does_not_save_snapshot():
    result, repository = build_dashboard({"proyecto": "P-1"})

    assert not result.is_cacheable
    assert repository.appended_rows == []
    assert result.payload["kpis"]["totalProyectos"] == 1


def test_margin_delta_is_none_when_today_has_no_margin():
    result, _ = build_dashboard({"cliente": "Globex"})

    assert result.payload["kpis"]["delta"]["margenPromedio"] is None


def test_backup_data_adds_warning_and_skips_cache():
    batch = TimeEntryBatch(
        entries=TIME_ENTRIES,
        is_backup=True,
        backup_date="2026-10-01T10:00:00Z",
        backup_error="Timeout",
    )

    result, repository = build_dashboard(batch=batch)

    assert not result.is_cacheable
    assert repository.appended_rows == []
    assert result.payload["clockifyDatosDeRespaldo"] is True
    assert result.payload["alertas"][0]["tipo"] == "warning"
    assert "2026-10-01T10:00:00Z" in result.payload["alertas"][0]["texto"]
