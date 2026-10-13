"""Capacidad instalada: filtros, capacidad base y CSV."""

from datetime import date

import pytest

from apps.portal.schemas import CapacityFilters
from apps.portal.services.capacity import (
    build_capacity_csv,
    build_capacity_view,
    count_workdays,
    format_month,
    normalize_month,
    parse_workday_hours,
)

RULE_BILLABLE = {
    "cargabilidad": "Cargable",
    "facturable": "Facturable",
    "capacidad": "Afecta Capacidad",
    "afecta": True,
}
RULE_VACATION = {
    "cargabilidad": "No Cargable",
    "facturable": "No Facturable",
    "capacidad": "No Afecta Capacidad",
    "afecta": False,
}


def make_row(**overrides):
    row = {
        "recurso": "Ana Perez",
        "banda": "B2",
        "concepto": "Proyecto",
        "tecnologia": "DEV",
        "manager": "Brandon Sotelo",
        "idProyecto": "GPO.007",
        "proyecto": "MultiProfile",
        "horasDiarias": 4,
        "horasEstimadas": 100,
        "activo": True,
        "regla": RULE_BILLABLE,
    }
    row.update(overrides)

    return row


def make_data(*rows, **extra):
    return {"ok": True, "filas": list(rows), **extra}


def make_filters(**overrides):
    values = {"month": "2026-10", "workday_hours": 8.0}
    values.update(overrides)

    return CapacityFilters(**values)


def test_normalize_month_keeps_valid_values_only():
    today = date(2026, 10, 12)

    assert normalize_month("2026-03", today) == "2026-03"
    assert normalize_month(" 2026-12 ", today) == "2026-12"
    assert normalize_month("2026-13", today) == "2026-10"
    assert normalize_month("octubre", today) == "2026-10"
    assert normalize_month("", today) == "2026-10"


@pytest.mark.parametrize(
    ("text", "expected"),
    [("8", 8.0), ("7,5", 7.5), ("", 8.0), ("0", 8.0), ("30", 8.0), ("x", 8.0)],
)
def test_parse_workday_hours(text, expected):
    assert parse_workday_hours(text) == expected


def test_workdays_and_month_label():
    assert count_workdays("2026-10") == 22
    assert count_workdays("2026-02") == 19
    assert format_month("2026-10") == "Octubre 2026"


def test_view_totals_and_base_capacity():
    data = make_data(
        make_row(),
        make_row(proyecto="Otro", idProyecto="MCC.026", horasDiarias=5),
        make_row(recurso="Luis", horasDiarias=3),
        make_row(
            recurso="Luis",
            concepto="Vacaciones",
            horasDiarias=8,
            regla=RULE_VACATION,
        ),
        make_row(recurso="Inactivo", activo=False),
        bandaColumna="x",
    )

    view = build_capacity_view(data, make_filters())

    assert view.resources == 2
    assert view.workdays == 22
    assert view.base_hours == 2 * 22 * 8
    assert view.assigned_daily_hours == 12
    assert view.over_workday == 1
    assert len(view.rows) == 4
    assert view.month_label == "Octubre 2026"


def test_unassigned_rows_without_rule_still_count_hours():
    row = make_row(concepto="Nuevo", regla=None, horasDiarias=2)

    view = build_capacity_view(make_data(row), make_filters())

    assert view.assigned_daily_hours == 2
    assert view.rows[0].has_rule is False


def test_filters_by_search_technology_and_concept():
    data = make_data(
        make_row(),
        make_row(recurso="Luis Gómez", tecnologia="QA", manager="Patricio"),
        make_row(recurso="Eva", concepto="Interno", proyecto="Casa"),
    )

    assert (
        build_capacity_view(data, make_filters(search="gomez")).resources == 1
    )
    assert (
        build_capacity_view(data, make_filters(search="patricio")).resources
        == 1
    )
    assert (
        build_capacity_view(data, make_filters(technology="QA")).resources == 1
    )
    assert (
        build_capacity_view(data, make_filters(concept="Interno")).resources
        == 1
    )
    assert build_capacity_view(data, make_filters(search="zzz")).rows == ()


def test_filter_options_use_all_rows_even_when_filtered():
    data = make_data(
        make_row(),
        make_row(recurso="Luis", tecnologia="QA", concepto="Interno"),
    )

    view = build_capacity_view(data, make_filters(technology="QA"))

    assert view.technologies == ("DEV", "QA")
    assert view.concepts == ("Interno", "Proyecto")


def test_view_with_missing_or_malformed_data():
    empty = build_capacity_view({}, make_filters())
    malformed = build_capacity_view(
        {"filas": ["x", {"horasDiarias": "abc"}, None]},
        make_filters(),
    )

    assert empty.rows == ()
    assert empty.resources == 0
    assert empty.base_hours == 0
    assert len(malformed.rows) == 1
    assert malformed.rows[0].daily_hours == 0


def test_band_notice_is_passed_through():
    data = make_data(bandasAviso="Sin columna", bandaColumna="Octubre")

    view = build_capacity_view(data, make_filters())

    assert view.band_notice == "Sin columna"
    assert view.band_column == "Octubre"


def test_csv_has_header_rules_and_blank_when_no_rule():
    data = make_data(
        make_row(),
        make_row(recurso="Luis", regla=None, concepto="Nuevo"),
    )
    view = build_capacity_view(data, make_filters())

    lines = build_capacity_csv(view.rows).splitlines()

    assert lines[0].startswith("Recurso,Banda,Concepto")
    assert lines[1].endswith(",4.0,100.0,Si,Si,Si")
    assert lines[2].endswith(",4.0,100.0,,,")


def test_mpb_notice_is_passed_through():
    data = make_data(mpbAviso="No se reconocen los encabezados de MPB.")

    view = build_capacity_view(data, make_filters())

    assert view.mpb_notice.startswith("No se reconocen")
