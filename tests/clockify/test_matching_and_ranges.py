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
