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
