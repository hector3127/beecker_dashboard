from datetime import datetime

from apps.ejecutivo.services.additional_milestones import (
    read_additional_milestones,
)
from apps.ejecutivo.services.history_stages import (
    estimate_stage_progress,
    read_history_stages,
    stage_day,
)
from apps.ejecutivo.services.project_dashboard import build_extra_kpis
from apps.ejecutivo.services.project_detail import (
    build_error_detail,
    categorize_role,
    format_js_number,
    resource_status,
)


def test_stage_day_formats():
    assert stage_day("2026-02-30") == datetime(2026, 3, 2)
    assert stage_day("05/10/2026") == datetime(2026, 10, 5)
    assert stage_day("2026-10-05T06:00:00.000Z") == datetime(2026, 10, 5)
    assert stage_day("texto") is None
    assert stage_day("") is None


def test_stage_progress_with_last_stage_open():
    phases = [
        {"estado": "Completado"},
        {
            "estado": "En curso",
            "fechaInicioReal": "2026-10-01",
            "fechaFinPlan": "2026-10-04",
        },
    ]

    progress = estimate_stage_progress(phases, datetime(2026, 10, 2, 12))

    assert progress.current_stage_pct == 37.5
    assert progress.pct == 50
    assert estimate_stage_progress([], datetime(2026, 1, 1)).pct is None


def test_history_without_discovery_has_no_stages():
    values = [
        ["Project ID", "Status", "Start", "Finish"],
        ["A.1", "Development EST", "01/01/2026", ""],
    ]

    assert read_history_stages(values, "A.1") is None
    assert read_history_stages(values, " ") is None
    assert read_history_stages([["Otra"]], "A.1") is None


def test_additional_milestones_edge_cases():
    assert read_additional_milestones([], "A") == []
    assert read_additional_milestones([["Otro"], ["A"]], "A") == []
    assert read_additional_milestones([["ID_Proyecto"], ["B"]], "A") == []


def test_extra_kpis_follow_detail_shape():
    error_detail = build_error_detail("A", "falla")

    assert "horasNoFact" not in build_extra_kpis([], error_detail)
    assert build_extra_kpis([], {})["costoReal"] == 0


def test_small_helpers():
    assert resource_status(95, 100) == "En riesgo"
    assert resource_status(101, 100) == "Excedido"
    assert categorize_role("Scrum Master") == "Soporte"
    assert categorize_role(None) == "Otros"
    assert format_js_number(45.3) == "45.3"
    assert format_js_number(733.0) == "733"
