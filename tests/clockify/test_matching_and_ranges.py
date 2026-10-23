from datetime import date

import pytest

from apps.clockify.exceptions import ClockifyRequestError
from apps.clockify.services.clockify_client import ClockifyProject
from apps.clockify.services.date_ranges import (
    ProjectDateRangeResolver,
    parse_sheet_date,
)
from apps.clockify.services.duration_parser import parse_duration_hours
from apps.clockify.services.project_matcher import resolve_clockify_project
from tests.fakes import InMemorySheetRepository

PROJECTS = [
    ClockifyProject("c1", "AMK.008"),
    ClockifyProject("c2", "GPO.007 - MultiProfile"),
    ClockifyProject("c3", "Ánalisis Ventas"),
    ClockifyProject("c4", "XYZ.001 - A"),
    ClockifyProject("c5", "XYZ.001 - B"),
]


@pytest.mark.parametrize(
    ("internal_id", "expected"),
    [
        ("AMK.008_S4", "c1"),
        ("GPO.007", "c2"),
        ("analisis  ventas", "c3"),
        ("XYZ.001", None),
        ("NO.EXISTE", None),
    ],
)
def test_resolve_clockify_project(internal_id, expected):
    project = resolve_clockify_project(internal_id, PROJECTS, {})

    assert (project.project_id if project else None) == expected


def test_manual_link_wins_over_name():
    project = resolve_clockify_project("XYZ.001", PROJECTS, {"XYZ.001": "c5"})

    assert project is not None
    assert project.project_id == "c5"


@pytest.mark.parametrize(
    ("raw_duration", "expected"),
    [(5400, 1.5), ("PT1H30M", 1.5), ("PT45S", 0.0125), ("PT2H", 2.0)],
)
def test_parse_duration_hours(raw_duration, expected):
    assert parse_duration_hours(raw_duration, "e1") == pytest.approx(expected)


def test_invalid_duration_raises():
    with pytest.raises(ClockifyRequestError):
        parse_duration_hours(None, "e1")


def test_parse_sheet_date_formats():
    assert parse_sheet_date("5/3/26") == date(2026, 3, 5)
    assert parse_sheet_date("15/03/2026") == date(2026, 3, 15)
    assert parse_sheet_date(46023) == date(2026, 1, 1)
    assert parse_sheet_date("31/02/2026") is None


HISTORY = [
    ["Reporte de etapas"],
    ["Project ID", "Status", "x", "Start", "Finish"],
    ["AMK.008", "Discovery EST", "", "01/01/2026", "15/01/2026"],
    ["AMK.008", "Discovery", "", "05/01/2026", "20/01/2026"],
    ["AMK.008", "Deployment OP", "", "01/05/2026", "30/06/2026"],
    ["IXB.002", "Discovery", "", "01/02/2026", ""],
]

MPB = [
    ["ID", "Service", "Inicio", "Fin"],
    ["TYM.AMK.010", "T&M", "01/03/2026", ""],
    ["AER.001", "IXB", "01/03/2026", "01/04/2026"],
]


def build_resolver():
    repository = InMemorySheetRepository(
        {"Historico_Proyectos": HISTORY, "MPB": MPB},
    )
    return ProjectDateRangeResolver(repository, date(2026, 10, 2))


def test_history_range_prefers_real_stage():
    date_range = build_resolver().resolve("AMK.008_S1".split("_")[0])

    assert date_range.start_date == date(2026, 1, 5)
    assert date_range.end_date == date(2026, 6, 30)


def test_history_without_deployment_ends_today():
    date_range = build_resolver().resolve("IXB.002")

    assert date_range.end_date == date(2026, 10, 2)


def test_mpb_range_for_tym_projects():
    resolver = build_resolver()

    tym_range = resolver.resolve("TYM.AMK.010")
    wrong_service = resolver.resolve("AER.001")

    assert tym_range.start_date == date(2026, 3, 1)
    assert tym_range.end_date == date(2026, 10, 2)
    assert wrong_service.start_date is None


def test_mpb_without_fin_header_uses_column_i():
    current_mpb = [
        ["Reporte MPB"],
        [
            "#",
            "CLIENTE",
            "ID",
            "ID Planilla",
            "NOMBRE",
            "SERVICE ",
            "INICIO",
            "FIN ORIGINAL",
            "n ",
        ],
        [
            1,
            "ACME",
            "AER.AWN.001",
            "",
            "Soporte",
            "AER",
            "01/03/2026",
            "01/04/2026",
            "30/09/2026",
        ],
    ]
    resolver = ProjectDateRangeResolver(
        InMemorySheetRepository({"MPB": current_mpb}),
        date(2026, 10, 2),
    )

    date_range = resolver.resolve("AER.AWN.001")

    assert date_range.start_date == date(2026, 3, 1)
    assert date_range.end_date == date(2026, 9, 30)


@pytest.mark.parametrize("reverse", [False, True])
def test_repeated_deployment_uses_extended_finish_without_losing_start(reverse):
    rows = [
        ["AMK.004_CR", "Discovery OP", "", "07/05/2026", "14/05/2026"],
        ["AMK.004_CR", "Discovery", "", "09/06/2026", "16/06/2026"],
        ["AMK.004_CR", "Deployment", "", "11/09/2026", "25/09/2026"],
        ["AMK.004_CR", "Deployment", "", "15/10/2026", "20/10/2026"],
        ["AMK.004_CR", "Deployment EST", "", "15/10/2026", "30/10/2026"],
    ]
    reader = InMemorySheetRepository(
        {
            "Historico_Proyectos": [HISTORY[1]]
            + (list(reversed(rows)) if reverse else rows)
        }
    )
    result = ProjectDateRangeResolver(reader, date(2026, 10, 16)).resolve(
        "AMK.004_CR"
    )
    assert result.start_date == date(2026, 5, 7)
    assert result.end_date == date(2026, 10, 20)


def test_full_range_spans_repeated_mpb_rows():
    mpb = [
        ["ID", "Service", "Inicio", "Fin"],
        ["AER.CCO.008", "AER", "18/05/2026", "20/05/2026"],
        ["AER.CCO.008", "AER", "11/05/2026", "31/12/2026"],
    ]
    resolver = ProjectDateRangeResolver(
        InMemorySheetRepository({"MPB": mpb}), date(2026, 10, 2)
    )

    first = resolver.resolve("AER.CCO.008")
    full = resolver.resolve_full("AER.CCO.008")

    assert (first.start_date, first.end_date) == (
        date(2026, 5, 18),
        date(2026, 5, 20),
    )
    assert (full.start_date, full.end_date) == (
        date(2026, 5, 11),
        date(2026, 12, 31),
    )
    assert resolver.resolve_full("TYM.NONE").start_date is None
