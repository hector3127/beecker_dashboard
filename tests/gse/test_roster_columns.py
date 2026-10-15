"""GSE reconoce ROL e ID Clockify aunque cambie el orden de columnas."""

from apps.gse.services.batch_read import get_batch
from apps.gse.services.clockify_ids import write_ids
from apps.gse.services.month_report import get_month
from apps.gse.services.roster import list_areas
from tests.gse.test_parity import build_context


def reordered_context():
    context = build_context("main")
    rows = context.reader.sheets["Bandas/rol"]
    # Nombre, ROL, ID Clockify, Correo; se conservan todas las bandas.
    context.reader.sheets["Bandas/rol"] = [
        [(row[i] if i < len(row) else "") for i in [0, 2, 3, 1, 4, 5]]
        for row in rows
    ]
    return context


def test_areas_and_monthly_hours_are_independent_of_role_column_position():
    original = build_context("main")
    moved = reordered_context()
    assert list_areas(moved.reader) == list_areas(original.reader)
    args = ("2026-09", "sheet", False, "Desarrollo")
    assert get_month(moved, args) == get_month(original, args)


def test_batch_hours_and_bands_use_role_header_in_column_b():
    args = ("2026", "Desarrollo", 0, 0)
    original = get_batch(build_context("main"), args)
    moved = get_batch(reordered_context(), args)
    original.pop("milliseconds", None)
    moved.pop("milliseconds", None)
    assert moved == original


def test_ids_use_existing_column_c_and_preserve_other_columns():
    reader = reordered_context().reader
    before = [row[:] for row in reader.sheets["Bandas/rol"]]
    result = write_ids(reader, [("Pedro Ruiz", "new-id")])
    assert result["guardados"] == 1
    after = reader.sheets["Bandas/rol"]
    assert len(after[2]) == len(before[2])
    pedro = next(row for row in after if row[0] == "Pedro Ruiz")
    assert pedro[2] == "new-id"
    assert pedro[3:] == next(
        row[3:] for row in before if row[0] == "Pedro Ruiz"
    )
