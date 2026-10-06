"""Compara la vista de Recursos contra RecursosDetalleService.gs.

recursos_expected.json es la salida del original (harness de Node) para
las operaciones de recursos_data.json. El harness corre con TZ=UTC para
que new Date('YYYY-MM-DD') quede en el dia correcto: en Apps Script, con
zona de Mexico, el original movia esas fechas un dia atras (ver README).
"""

import json
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

from apps.recursos.services import person_detail, summary
from apps.recursos.services.resource_records import (
    position_by_person,
    to_records,
)
from core.time_entries.models import TimeEntry

HERE = Path(__file__).parent
DATA = json.loads((HERE / "recursos_data.json").read_text("utf-8"))
EXPECTED = json.loads((HERE / "recursos_expected.json").read_text("utf-8"))
TODAY = date(2026, 10, 3)
MEXICO = ZoneInfo("America/Mexico_City")


def local(text):
    if not text:
        return None

    moment = datetime.fromisoformat(text.replace("Z", "+00:00"))

    return moment.astimezone(MEXICO).replace(tzinfo=None)


def entry(row):
    return TimeEntry(
        entry_id=row["id"],
        project_id=row["proyecto"],
        resource_name=row["recurso"],
        entry_date=datetime.fromisoformat(row["fecha"]),
        duration_hours=row["duracion"],
        is_billable=row["billable"],
        costing_rate=0,
        description=row["descripcion"],
        started_at=local(row["fechaInicioCompleta"]),
        ended_at=local(row["fechaFinCompleta"]),
    )


RECORDS = to_records(entry(row) for row in DATA["REGISTROS"])
HEADERS, *ROWS = DATA["SHEETS"]["Recursos"]
RESOURCE_ROWS = [dict(zip(HEADERS, row, strict=True)) for row in ROWS]
POSITIONS = position_by_person(RESOURCE_ROWS)


def run(name, args):
    if name == "getResumenRecursos":
        return summary.build_summary(RECORDS, POSITIONS, TODAY)

    if name == "getProyectosConHoras":
        return summary.projects_with_hours(RECORDS)

    if name == "getPersonasConHoras":
        return summary.people_with_hours(RECORDS)

    if name == "obtenerProyectosAsignadosPersona":
        return person_detail.assigned_projects(args[0], RESOURCE_ROWS)

    person, grouping = (*args, None)[:2]

    return person_detail.person_detail(
        person, grouping, RECORDS, POSITIONS, TODAY
    )


@pytest.mark.parametrize("index", range(len(DATA["OPERATIONS"])))
def test_matches_original(index):
    name, args = DATA["OPERATIONS"][index]

    assert json.loads(json.dumps(run(name, args))) == EXPECTED[index]
