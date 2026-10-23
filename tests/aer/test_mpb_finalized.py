from apps.aer.services.dashboard import mpb_finalized
from tests.fakes import InMemorySheetRepository

HEADER = ["", "CLIENTE", "ID", "", "NOMBRE", "SERVICE", "ESTATUS"]


def repo(*rows):
    return InMemorySheetRepository({"MPB": [HEADER, *rows]})


def test_finalized_status_in_mpb_marks_the_project_as_closed():
    reader = repo(
        ["", "Arca", "AER.SBM.003", "", "Soporte", "AER", "Finalizado"],
        ["", "Audi", "TYM.AAU.001", "", "Migracion", "T&M", "En progreso"],
    )

    assert mpb_finalized(reader, "AER.SBM.003") is True
    assert mpb_finalized(reader, "aer.sbm.003") is True
    assert mpb_finalized(reader, "TYM.AAU.001") is False


def test_missing_sheet_or_project_is_not_closed():
    assert mpb_finalized(InMemorySheetRepository({}), "AER.SBM.003") is False
    assert mpb_finalized(repo(), "AER.SBM.003") is False


FULL_HEADER = [
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


def test_closed_project_missing_from_proyectos_is_built_from_mpb():
    from apps.aer.services.dashboard import mpb_project_row

    reader = InMemorySheetRepository(
        {
            "MPB": [
                FULL_HEADER,
                [
                    "",
                    "OXXO",
                    "AER.CCO.003",
                    "",
                    "Celula",
                    "AER",
                    100,
                    0,
                    150,
                    "Finalizado",
                    "Dora",
                    2128,
                ],
                [
                    "",
                    "OXXO",
                    "AER.CCO.003",
                    "",
                    "Celula",
                    "AER",
                    151,
                    0,
                    200,
                    "Finalizado",
                    "Dora",
                    571,
                ],
                [
                    "",
                    "OXXO",
                    "TYM.CCO.001",
                    "",
                    "Otro",
                    "IxB",
                    1,
                    0,
                    2,
                    "",
                    "",
                    9,
                ],
            ]
        }
    )

    row = mpb_project_row(reader, "AER.CCO.003")

    assert row["Fecha_Inicio"] == 100 and row["Fecha_Fin_Estimada"] == 200
    assert row["Budget_Hrs"] == 2699
    assert row["Estado"] == "Finalizado"
    assert mpb_project_row(reader, "TYM.CCO.001") is None
    assert mpb_project_row(reader, "NOPE") is None
