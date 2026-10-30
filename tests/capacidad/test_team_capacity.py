"""Capacidad del equipo: Bandas/rol + Clockify, sin la hoja Recursos."""

from datetime import date

import pytest

from apps.capacidad.services import team_capacity as service
from apps.capacidad.services.sheet_table import SheetTable
from apps.datastore.models import ClockifyTimeEntry

pytestmark = pytest.mark.django_db
MONTH = "2026-10"
HEADERS = ["Nombre", "ROL", "ID Clockify", "Septiembre", "Octubre"]


def sheet(*rows):
    return SheetTable(
        headers=HEADERS, rows=[list(r) for r in rows], header_index=0
    )


def entry(index, user_id, user, project, seconds, day, billable=True, pid="p"):
    ClockifyTimeEntry.objects.create(
        entry_id=f"e{index}",
        project_id=pid,
        project_name=project,
        user_id=user_id,
        user_name=user,
        billable=billable,
        entry_date=day,
        month=date(2026, 10, 1),
        duration_seconds=seconds,
    )


@pytest.fixture
def team(monkeypatch):
    """Bandas/rol sintetica: roles, bandas vigentes, sin ID y bajas."""
    table = sheet(
        ["Ana Perez", "Dev", "u-ana", "B2", "B2"],
        ["Luis Soto", "QA", "", "B1", "B1"],
        ["Eva Ruiz", "Dev", "u-eva", "B1", "BAJA"],
        ["Raul Mena", "Ventas", "u-raul", "B1", "B1"],
        ["Zoe Diaz", "SM", "u-zoe", "B3", "B3"],
        ["Nora Paz", "BA", "u-nora", "B1", "NA"],
        ["Ivo Sanz", "Arq", "u-ivo", "B1", ""],
    )
    monkeypatch.setattr(service, "read_sheet_table", lambda *a, **k: table)

    class Info:
        def __init__(self, reader):
            pass

        def lookup(self, project_id, name):
            return (
                ("Dora DM", "Proyecto " + project_id)
                if project_id == "AER.001"
                else ("", name)
            )

        def dates(self, project_id):
            # AER.001 existe en Azure/MPB pero solo tiene fecha de inicio
            return (
                (True, "2026-09-01", "")
                if project_id == "AER.001"
                else (False, "", "")
            )

    monkeypatch.setattr(service, "ProjectInfo", Info)


def test_only_operational_roles_with_a_valid_band_are_included(team):
    people = service.read_team(object(), MONTH)

    assert [p["nombre"] for p in people] == [
        "Ana Perez",
        "Luis Soto",
        "Zoe Diaz",
    ]


def test_matches_by_id_then_by_name_and_excludes_lunch(team):
    entry(1, "u-ana", "Ana P.", "AER.001", 7200, date(2026, 10, 5))
    entry(
        2,
        "u-ana",
        "Ana P.",
        "Comida",
        3600,
        date(2026, 10, 5),
        pid=service.LUNCH_PROJECT_ID,
    )
    entry(
        3, "x", "Luis Soto", "NYB.001", 1800, date(2026, 10, 3), billable=False
    )
    entry(4, "u-raul", "Raul Mena", "AER.001", 3600, date(2026, 10, 6))

    data = service.build_team_capacity(object(), MONTH)
    ana, luis = data["personas"][0], data["personas"][1]

    assert (ana["total"], ana["facturables"]) == (2.0, 2.0)
    assert (luis["total"], luis["noFacturables"]) == (0.5, 0.5)
    assert data["resumen"]["registradas"] == 2.5


def test_weekend_hours_count_and_rows_carry_project_and_manager(team):
    entry(1, "u-ana", "Ana", "AER.001", 3600, date(2026, 10, 3))  # sabado

    data = service.build_team_capacity(object(), MONTH)
    row = next(r for r in data["filas"] if r["nombre"] == "Ana Perez")

    assert row["daily"] == {"2026-10-03": 1.0}
    assert (row["dm"], row["proyecto"]) == ("Dora DM", "Proyecto AER.001")
    assert len(data["dias"]) == 31


def test_concept_and_rules_follow_azure_ids_then_clockify_names(team):
    entry(1, "u-ana", "Ana", "AER.001", 3600, date(2026, 10, 5))
    entry(2, "u-ana", "Ana", "Pre-Ventas", 3600, date(2026, 10, 6), pid="v")
    entry(3, "u-ana", "Ana", "Vacaciones", 3600, date(2026, 10, 7), pid="w")
    entry(4, "u-ana", "Ana", "RAAS.XYZ.001", 3600, date(2026, 10, 8), pid="x")
    entry(5, "u-ana", "Ana", "TYM.NYB.009", 3600, date(2026, 10, 9), pid="y")

    rows = {
        r["idProyecto"]: r
        for r in service.build_team_capacity(object(), MONTH)["filas"]
        if r["nombre"] == "Ana Perez"
    }

    assert rows["AER.001"]["concepto"] == "Proyecto"
    assert rows["Pre-Ventas"]["concepto"] == "Pre-Ventas"
    assert rows["Pre-Ventas"]["facturable"] == "Facturable"
    assert rows["Vacaciones"]["cargabilidad"] == "No Cargable"
    assert rows["Vacaciones"]["capacidad"] == "No Afecta Capacidad"
    assert rows["RAAS.XYZ.001"]["concepto"] == ""  # ni Azure/MPB ni concepto
    assert rows["TYM.NYB.009"]["concepto"] == "Interno"  # nomenclatura NYB
    assert rows["TYM.NYB.009"]["facturable"] == "No Facturable"


def test_project_dates_fall_back_to_the_rows_first_and_last_record(team):
    entry(1, "u-ana", "Ana", "AER.001", 3600, date(2026, 10, 9))
    entry(2, "u-ana", "Ana", "AER.001", 3600, date(2026, 10, 5))
    entry(3, "u-ana", "Ana", "NYB.001", 3600, date(2026, 10, 12), pid="n")
    entry(4, "u-ana", "Ana", "NYB.001", 3600, date(2026, 10, 20), pid="n")

    rows = {
        r["idProyecto"]: r
        for r in service.build_team_capacity(object(), MONTH)["filas"]
        if r["nombre"] == "Ana Perez"
    }

    assert (rows["AER.001"]["inicio"], rows["AER.001"]["fin"]) == (
        "2026-09-01",  # fecha del proyecto
        "2026-10-09",  # le falta: ultimo registro de la fila
    )
    assert (rows["NYB.001"]["inicio"], rows["NYB.001"]["fin"]) == (
        "2026-10-12",
        "2026-10-20",
    )


def test_people_without_records_appear_with_zero_hours(team):
    data = service.build_team_capacity(object(), MONTH)
    zoe = [r for r in data["filas"] if r["nombre"] == "Zoe Diaz"]

    assert len(zoe) == 1 and zoe[0]["total"] == 0 and zoe[0]["idProyecto"] == ""
    assert data["resumen"]["personas"] == 3
    assert data["resumen"]["conHoras"] == 0


def test_indicators_use_people_days_and_workday(team):
    entry(1, "u-ana", "Ana", "AER.001", 3600 * 200, date(2026, 10, 5))

    data = service.build_team_capacity(object(), MONTH, workday=8.0)
    summary = data["resumen"]

    assert data["diasHabiles"] == 22  # octubre 2026, sin festivos de Mexico
    assert summary["base"] == 3 * 22 * 8
    assert summary["saldo"] == summary["base"] - 200
    assert summary["utilizacion"] == round(200 / 528 * 100, 2)
    assert summary["sobreJornada"] == 1
