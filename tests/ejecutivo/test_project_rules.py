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


def test_resumed_stage_uses_its_last_run_and_closes_after_the_last_day():
    from apps.ejecutivo.services.history_stages import milestones_from_stages

    values = [["Project ID", "Status", "Start", "Finish"]]
    rows = [
        ("Discovery EST", "2026-06-19", "2026-06-25"),
        ("Development EST", "2026-06-26", "2026-07-17"),
        ("Deployment EST", "2026-07-20", "2026-07-31"),
        ("Discovery OP", "2026-06-19", "2026-06-26"),
        ("Development", "2026-06-29", "2026-07-21"),
        ("Deployment", "2026-07-22", "2026-08-24"),
        ("Suspendido", "2026-08-24", "2026-09-15"),
        ("Deployment", "2026-09-15", "2026-10-09"),
    ]
    values += [["MCC.026", status, start, end] for status, start, end in rows]
    stages = read_history_stages(values, "MCC.026")
    assert stages is not None

    on_last_day = datetime(2026, 10, 9, 11)
    last_day = milestones_from_stages(stages, {}, on_last_day.date())
    progress = estimate_stage_progress(last_day["lista"], on_last_day)

    assert [m["estado"] for m in last_day["lista"]] == [
        "Completado",
        "Completado",
        "En curso",
    ]
    assert last_day["lista"][2]["fechaInicioReal"] == "2026-09-15"
    assert 90 <= progress.pct < 100

    next_day = datetime(2026, 10, 10, 9)
    after = milestones_from_stages(stages, {}, next_day.date())

    assert estimate_stage_progress(after["lista"], next_day).pct == 100


def test_history_with_repeated_headers_reads_only_the_a_to_i_block():
    from apps.ejecutivo.services.project_dashboard import (
        ExecutiveSources,
        load_milestones,
    )
    from core.sheets.repository import build_row_object

    headers = ["Project ID", "Status", "Start", "Finish"] + [""] * 6
    headers += ["Project ID", "Stage"]
    left = [
        ("Discovery EST", "2026-06-19", "2026-06-25"),
        ("Development EST", "2026-06-26", "2026-07-17"),
        ("Deployment EST", "2026-07-20", "2026-07-31"),
        ("Discovery OP", "2026-06-19", "2026-06-26"),
        ("Development", "2026-06-29", "2026-07-21"),
        ("Deployment", "2026-07-22", "2026-08-24"),
        ("Suspendido", "2026-08-24", "2026-09-15"),
        ("Deployment", "2026-09-15", "2026-10-09"),
    ]
    values = [headers]
    values += [["MCC.026", status, start, end] for status, start, end in left]
    # Fila de otro proyecto cuya tabla de Proyectos (derecha) es MCC.026.
    values.append(
        ["AMK.008", "Development EST", "2026-09-07", "2026-09-28"]
        + [""] * 6
        + ["MCC.026", "Deployment"],
    )
    rows = [build_row_object(headers, row) for row in values[1:]]
    sources = ExecutiveSources([], [], rows, values, [], {}, [], [])
    project = {"Servicio": "IxB"}

    on_last_day = datetime(2026, 10, 9, 11)
    result = load_milestones(project, "MCC.026", sources, on_last_day)
    states = [item["estado"] for item in result["lista"]]
    progress = estimate_stage_progress(result["lista"], on_last_day)

    assert [item["nombre"] for item in result["lista"]] == [
        "Discovery",
        "Development",
        "Deployment",
    ]
    assert states == ["Completado", "Completado", "En curso"]
    assert 90 <= progress.pct < 100

    next_day = datetime(2026, 10, 10, 9)
    after = load_milestones(project, "MCC.026", sources, next_day)

    assert estimate_stage_progress(after["lista"], next_day).pct == 100


def test_open_stage_averages_days_with_closed_work_items():
    phases = [
        {"nombre": "Discovery", "estado": "Completado"},
        {"nombre": "Development", "estado": "Completado"},
        {
            "nombre": "Deployment",
            "estado": "En curso",
            "fechaInicioReal": "2026-09-15",
            "fechaFinReal": "2026-10-09",
        },
    ]
    last_day = datetime(2026, 10, 9, 11)

    plain = estimate_stage_progress(phases, last_day)
    mixed = estimate_stage_progress(
        phases,
        last_day,
        {"deployment": (6, 10)},
    )
    all_closed = estimate_stage_progress(
        phases,
        last_day,
        {"deployment": (10, 10)},
    )

    assert plain.pct == 97.8
    assert mixed.pct == 78.9
    assert all_closed.pct == 98.9
    assert mixed.current_stage_pct == 78.9
