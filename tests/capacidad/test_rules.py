import math
from datetime import date, datetime

import pytest

from apps.capacidad.exceptions import CapacityError
from apps.capacidad.services.capacity_text import (
    find_concept_rule,
    normalize_capacity_text,
    parse_capacity_number,
    parse_js_number,
)
from apps.capacidad.services.daily_hours import (
    entry_matches_variant,
    last_day_of_month,
    parse_report_range,
    read_base_id,
)
from apps.capacidad.services.mpb_projects import format_mpb_day
from apps.capacidad.services.orchestrator import (
    load_capacity_base,
    load_project_data,
)
from apps.clockify.services.clockify_client import ClockifyProject
from apps.clockify.services.project_matcher import resolve_clockify_project
from core.exceptions import (
    ConfigurationError,
    DashboardError,
    describe_error,
)
from core.time_entries.models import TimeEntry
from tests.capacidad import sample_data
from tests.capacidad.fakes import FakeAzureSource, build_report_loader
from tests.fakes import InMemorySheetRepository


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("Investigación  y Desarrollo", "investigacion y desarrollo"),
        ("Día_Feriado!", "dia feriado"),
        (None, ""),
        (5.0, "5"),
    ],
)
def test_normalize_capacity_text(value, expected):
    assert normalize_capacity_text(value) == expected


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("", None),
        (None, None),
        (True, None),
        (" ", 0.0),
        ("1,5", 1.5),
        ("1,5,5", None),
        ("0x10", 16.0),
        ("1e1", 10.0),
        ("-1", None),
        ("Infinity", None),
        ("abc", None),
        (8, 8.0),
        (-0.0, 0.0),
    ],
)
def test_parse_capacity_number(value, expected):
    assert parse_capacity_number(value) == expected


def test_parse_js_number_special_values():
    assert parse_js_number("-Infinity") == -math.inf
    assert math.isnan(parse_js_number("0xZZ"))


@pytest.mark.parametrize(
    ("concept", "resource_type", "expected"),
    [
        ("Interno", "Empleado", ("Cargable", "No Facturable", True)),
        ("Interno", "Becario", ("No Cargable", "No Facturable", True)),
        ("Pre Ventas", "Residente", ("Cargable", "No Facturable", True)),
        ("Pre ventas", "Empleado", ("Cargable", "Facturable", True)),
        ("Vacaciones", "Empleado", ("No Cargable", "No Facturable", False)),
    ],
)
def test_find_concept_rule(concept, resource_type, expected):
    rule = find_concept_rule(concept, resource_type)

    assert rule is not None
    assert (rule["cargabilidad"], rule["facturable"], rule["afecta"]) == (
        expected
    )


def test_unknown_concept_has_no_rule():
    assert find_concept_rule("Otro", "Empleado") is None


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (46023, "2026-01-01"),
        ("2026-02-03T10:00:00", "2026-02-03"),
        ("1/15/2026", "2026-01-15"),
        ("15/01/2026", ""),
        ("texto", ""),
        ("", ""),
        (True, ""),
    ],
)
def test_format_mpb_day(value, expected):
    assert format_mpb_day(value) == expected


def build_entry(day, task):
    return TimeEntry(
        entry_id="1",
        project_id="",
        resource_name="Ana",
        entry_date=datetime.fromisoformat(day) if day else None,
        duration_hours=1,
        is_billable=True,
        costing_rate=0,
        task_name=task,
    )


@pytest.mark.parametrize(
    ("project_id", "day", "task", "expected"),
    [
        ("RAS.001", "2026-10-02", "S2", True),
        ("RAS.001_S2", "2026-10-02", "Fase S2", True),
        ("RAS.001_S2", "2026-10-02", "S2-S3", False),
        ("RAS.001_s2", "2026-10-02", "s2", True),
        ("RAS.001_CR1", "2026-10-02", "CR1 ajustes", True),
        ("RAS.001_CR1", "2026-10-02", "SCR1", False),
        ("RAS.001_S2", "2026-10-02", "No task", True),
        ("RAS.001_S2", "2026-09-30", "", False),
        ("RAS.001_S2", "", "", False),
    ],
)
def test_entry_matches_variant(project_id, day, task, expected):
    entry = build_entry(day, task)

    assert (
        entry_matches_variant(project_id, entry, "2026-10-01", "2026-10-31")
        is expected
    )


def test_month_helpers():
    assert last_day_of_month("2028-02") == "2028-02-29"
    assert read_base_id(" RAS.001_cr ") == "RAS.001"

    with pytest.raises(CapacityError):
        read_base_id("_S1")

    with pytest.raises(CapacityError, match="posterior"):
        parse_report_range("2026-10-05", "2026-10-01", "RAS.001")

    with pytest.raises(CapacityError, match="inválido"):
        parse_report_range("2026-13-45", "2026-10-01", "RAS.001")


def test_band_notice_without_band_column():
    sheets = dict(sample_data.SHEETS)
    sheets["Bandas/rol"] = [["Nombre", "Rol"], ["Ana Pérez", "QA"]]

    result = load_capacity_base(
        lambda: InMemorySheetRepository(sheets),
        "2026-05",
        date(2026, 10, 2),
    )

    assert result["bandaColumna"] == ""
    assert result["bandasAviso"].startswith(
        "Bandas/rol no tiene columna para mayo 2026.",
    )
    assert result["personas"] == []


@pytest.mark.parametrize(
    ("sheets", "message"),
    [
        ({}, "No existe la hoja Bandas/rol."),
        (
            {"Bandas/rol": [["Otra"]]},
            "No se reconocen los encabezados de Bandas/rol.",
        ),
    ],
)
def test_missing_sheets_are_reported(sheets, message):
    result = load_capacity_base(
        lambda: InMemorySheetRepository(sheets),
        "2026-10",
        date(2026, 10, 2),
    )

    assert result == {"ok": False, "error": message}


def test_force_refresh_reaches_azure():
    azure = FakeAzureSource()

    load_project_data(
        ("RAS.001_S2", "", "2026-10", True),
        lambda: InMemorySheetRepository(sample_data.SHEETS),
        lambda: azure,
        build_report_loader,
    )

    assert azure.refresh_calls == [True]


def test_reader_failure_is_reported():
    def failing_reader():
        raise ConfigurationError("Falta GOOGLE_SPREADSHEET_ID.")

    result = load_project_data(
        ("RAS.001_S2", "", "2026-10", False),
        failing_reader,
        FakeAzureSource,
        build_report_loader,
    )

    assert result == {"ok": False, "error": "Falta GOOGLE_SPREADSHEET_ID."}


def test_describe_error_hides_private_detail():
    assert (
        describe_error(DashboardError("secreto"))
        == DashboardError.public_message
    )


PROJECTS = [
    ClockifyProject("c1", "GPO.007 - MultiProfile"),
    ClockifyProject("c2", "GPO.0071"),
    ClockifyProject("c3", "AMK.008"),
    ClockifyProject("c4", "AMK.008_S2"),
    ClockifyProject("c5", "RAS.001 Fase 2"),
    ClockifyProject("c6", "RAS.001-B"),
    ClockifyProject("c7", "ÁRBOL.01"),
    ClockifyProject("c8", "XYZ.9 extra"),
    ClockifyProject("c9", "XYZ.9 - otro"),
]


@pytest.mark.parametrize(
    ("internal_id", "expected"),
    # Resultado de _resolverProyectoClockify(id, true) del original.
    [
        ("GPO.007", "c1"),
        ("AMK.008", "c3"),
        ("AMK.008_S2", "c4"),
        ("RAS.001", None),
        ("arbol.01", "c7"),
        ("XYZ.9", None),
        ("AMK", None),
        ("gpo.007 - multiprofile", "c1"),
        ("NADA", None),
    ],
)
def test_strict_clockify_match_ignores_links(internal_id, expected):
    project = resolve_clockify_project(
        internal_id,
        PROJECTS,
        {internal_id.upper(): "c3"},
        strict=True,
    )

    assert (project.project_id if project else None) == expected
