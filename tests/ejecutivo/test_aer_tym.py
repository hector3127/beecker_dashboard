from datetime import date, datetime

import pytest

from apps.clockify.exceptions import ClockifyProjectError
from apps.ejecutivo.services.aer_tym_consumption import (
    build_consumption_items,
)
from apps.ejecutivo.services.aer_tym_summary import build_aer_tym_summary
from apps.ejecutivo.services.mpb_values import (
    parse_mpb_date,
    parse_mpb_number,
)
from core.exceptions import SheetColumnNotFoundError
from core.time_entries.models import TimeEntry

TODAY = date(2026, 10, 2)


def build_mpb_row(**values):
    row = [""] * 64
    positions = {
        "cliente": 1,
        "id": 2,
        "nombre": 4,
        "service": 5,
        "inicio": 6,
        "fin": 8,
        "estatus": 19,
        "dm": 20,
        "fte": 22,
        "dev": 23,
        "horas": 32,
        "burn": 63,
    }
    for key, value in values.items():
        row[positions[key]] = value
    return row


HEADER = build_mpb_row(
    cliente="CLIENTE",
    id="ID",
    nombre="NOMBRE",
    service="Service",
    inicio="INICIO",
    fin="FIN",
    estatus="Estatus",
    dm="Delivery Manager",
    fte="FTE",
    horas="HORAS",
    burn="Horas consumidas",
)


def build_values(*rows):
    return [["Reporte MPB"], HEADER, *rows]


@pytest.mark.parametrize(
    ("raw", "expected"),
    [("1,200 h", 1200.0), ("85%", 85.0), ("", None), ("abc", None), (7, 7.0)],
)
def test_parse_mpb_number(raw, expected):
    assert parse_mpb_number(raw) == expected


def test_parse_mpb_date_formats():
    assert parse_mpb_date("5/3/2026") == "2026-03-05"
    assert parse_mpb_date("2026-03-05T10:00") == "2026-03-05"
    assert parse_mpb_date(46023) == "2026-01-01"
    assert parse_mpb_date("sin fecha") == ""


def test_summary_keeps_only_aer_tym_in_progress():
    values = build_values(
        build_mpb_row(
            cliente="ACME",
            id="TYM.AMK.010",
            nombre="Soporte",
            service="T & M",
            inicio="01/03/2026",
            fin="2026-10-12",
            estatus="En progreso",
            dm="Laura",
            fte="1.5",
            dev=1,
            horas="1,000",
            burn=250,
        ),
        build_mpb_row(id="AER.002", service="AER", estatus="Completed"),
        build_mpb_row(id="IXB.001", service="IXB", estatus="En progreso"),
        build_mpb_row(id="AER.003", service="aer", estatus="In progress"),
    )

    summary = build_aer_tym_summary(values, TODAY)

    rows = summary["filas"]
    assert [row["idProyecto"] for row in rows] == ["TYM.AMK.010", "AER.003"]
    first_row = rows[0]
    assert first_row["servicio"] == "T&M"
    assert first_row["budget"] == 1000
    assert first_row["burn"] == 250
    assert first_row["avance"] == 25.0
    assert first_row["etc"] == 750
    assert first_row["renewalDias"] == 10
    assert first_row["ftePorRol"]["DEV"] == 1
    assert first_row["fechaInicio"] == "2026-03-01"
    assert rows[1]["deliveryManager"] == "Sin asignar"
    assert rows[1]["burn"] is None
    assert rows[1]["avance"] is None


def test_summary_requires_headers():
    with pytest.raises(SheetColumnNotFoundError):
        build_aer_tym_summary([["sin encabezados"]], TODAY)


def build_entry(entry_date, hours, billable=False):
    return TimeEntry("e", "P", "Ana", entry_date, hours, billable, 0.0)


def test_consumption_sums_all_hours_in_range():
    summary_rows = [
        {"idProyecto": "TYM.AMK.010", "fechaInicio": "2026-09-01"},
        {"idProyecto": "AER.003", "fechaInicio": ""},
    ]
    calls = []

    def load_entries(project_id, date_range):
        calls.append((project_id, date_range))
        return [
            build_entry(datetime(2026, 9, 2), 1.25),
            build_entry(datetime(2026, 9, 3), 2, billable=True),
            build_entry(datetime(2026, 8, 31), 9),
        ]

    items = build_consumption_items(
        ["tym.amk.010", "AER.003", "NO.EXISTE"],
        summary_rows,
        load_entries,
        TODAY,
    )

    assert items == [
        {"id": "TYM.AMK.010", "burn": 3.25},
        {"id": "AER.003", "error": "No hay fecha INICIO en MPB"},
    ]
    assert calls == [("TYM.AMK.010", (date(2026, 9, 1), TODAY))]


def test_consumption_reports_clockify_errors():
    def load_entries(project_id, date_range):
        raise ClockifyProjectError("No se encontro una coincidencia unica.")

    items = build_consumption_items(
        ["AER.009"],
        [{"idProyecto": "AER.009", "fechaInicio": "2026-01-01"}],
        load_entries,
        TODAY,
    )

    assert items[0]["error"] == "No se encontro una coincidencia unica."
