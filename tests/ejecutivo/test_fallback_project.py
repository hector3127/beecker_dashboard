from datetime import date

from apps.clockify.services.date_ranges import ProjectDateRangeResolver
from apps.ejecutivo.services.fallback_project import (
    fallback_project_row,
    missing_data,
)
from tests.fakes import InMemorySheetRepository

HEADER = [
    "",
    "CLIENTE",
    "ID",
    "",
    "NOMBRE",
    "SERVICE",
    "INICIO",
    "FIN ORIGINAL",
    "FIN",
    "ESTATUS",
    "Delivery Manager",
    "HORAS",
]
HISTORY = [
    [
        "Delivery Manager",
        "Account",
        "Project ID",
        "Service",
        "Status",
        "Start",
        "Finish",
    ],
    ["", "ACME", "XYZ.001", "XYZ.001", "Discovery", "01/02/2026", "01/03/2026"],
    [
        "",
        "ACME",
        "XYZ.001",
        "XYZ.001",
        "Deployment",
        "01/04/2026",
        "30/04/2026",
    ],
]


def repo(mpb_rows, history=None):
    sheets = {"MPB": [HEADER, *mpb_rows]}
    if history:
        sheets["Historico_Proyectos"] = history
    return InMemorySheetRepository(sheets)


def test_ixb_project_only_in_mpb_gets_a_row_and_notes():
    reader = repo(
        [
            [
                "",
                "AB",
                "ABI.004",
                "",
                "MJE",
                "IxB",
                44502,
                0,
                44565,
                "Finalizado",
                "Ana",
                "",
            ]
        ]
    )

    row = fallback_project_row(reader, "ABI.004", [])

    assert row["Nombre"] == "MJE" and row["Servicio"] == "IxB"
    assert row["Fecha_Inicio"] == 44502 and row["Fecha_Fin_Estimada"] == 44565
    notes = missing_data(row)
    assert any("no está en la hoja Proyectos" in n for n in notes)
    assert any("presupuesto" in n for n in notes)
    assert not any("fecha" in n.lower() for n in notes)


def test_missing_dates_name_the_sources_to_fill():
    reader = repo(
        [["", "AB", "ABI.005", "", "Sin fechas", "SaaS", "", 0, "", "", "", 10]]
    )

    notes = missing_data(fallback_project_row(reader, "ABI.005", []))

    assert any("Falta la fecha de inicio" in n for n in notes)
    assert any("Falta la fecha de fin" in n for n in notes)


def test_history_fills_missing_mpb_dates_and_unknown_project_is_none():
    history_rows = [
        dict(zip(HISTORY[0], row, strict=False)) for row in HISTORY[1:]
    ]
    history_rows = [
        {
            "Project ID": r["Project ID"],
            "Start": r["Start"],
            "Finish": r["Finish"],
        }
        for r in history_rows
    ]
    reader = repo([])

    row = fallback_project_row(reader, "XYZ.001", history_rows)

    assert row["Fecha_Inicio"] == date(2026, 2, 1)
    assert row["Fecha_Fin_Estimada"] == date(2026, 4, 30)
    assert fallback_project_row(reader, "NOPE", history_rows) is None


def test_resolver_uses_mpb_range_for_ixb_without_history_stages():
    reader = repo(
        [
            [
                "",
                "AB",
                "ABI.004",
                "",
                "MJE",
                "IxB",
                44502,
                0,
                44565,
                "Finalizado",
                "Ana",
                5,
            ]
        ],
        history=HISTORY,
    )

    found = ProjectDateRangeResolver(reader, date(2026, 10, 2)).resolve(
        "ABI.004"
    )

    assert found.start_date == date(2021, 11, 2)
    assert found.end_date == date(2022, 1, 4)
