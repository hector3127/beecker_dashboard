"""Compara el detalle y el dashboard ejecutivo contra el Apps Script.

project_expected.json es la salida de getDetalleProyectoCompleto() y
getDashboardEjecutivoProyecto() del .gs original con
project_sample_data.
"""

import copy
import json
from datetime import datetime
from pathlib import Path

import pytest

from apps.clockify.exceptions import ClockifyProjectError
from apps.ejecutivo.services.project_orchestrator import (
    load_executive_dashboard,
    load_project_detail,
)
from core.time_entries.models import TimeEntry
from tests.ejecutivo import project_sample_data as sample
from tests.fakes import InMemorySheetRepository

NOW = datetime(2026, 10, 2, 12, 0)
EXPECTED = json.loads(
    (Path(__file__).parent / "project_expected.json").read_text("utf-8"),
)


def to_time_entry(index, record):
    return TimeEntry(
        entry_id=f"{record['proyecto']}{index}",
        project_id=record["proyecto"],
        resource_name=record["recurso"],
        entry_date=datetime.fromisoformat(record["fecha"]),
        duration_hours=record["duracion"],
        is_billable=record["billable"],
        costing_rate=0.0,
        tags=tuple(record["tags"]),
        task_name=record["task"],
    )


def load_project_entries(project_id):
    records = sample.PROJECT_ENTRIES.get(project_id)

    if records is None:
        raise ClockifyProjectError("Sin Clockify")

    return [
        to_time_entry(index, record) for index, record in enumerate(records)
    ]


def load_portfolio_entries():
    return tuple(
        to_time_entry(index, record)
        for index, record in enumerate(sample.PORTFOLIO)
    )


def build_reader(overrides):
    sheets = copy.deepcopy(sample.SHEETS)

    for sheet_name, rows in overrides.items():
        if rows is None:
            sheets.pop(sheet_name)
        else:
            sheets[sheet_name] = copy.deepcopy(rows)

    return InMemorySheetRepository(sheets)


@pytest.mark.parametrize(
    ("scenario", "expected"),
    list(zip(sample.SCENARIOS, EXPECTED, strict=True)),
)
def test_project_views_match_original(scenario, expected):
    function_name, project_id, overrides = scenario
    reader = build_reader(overrides)

    if function_name == "detalle":
        result = load_project_detail(
            reader,
            project_id,
            load_project_entries,
            NOW,
        )
    else:
        result = load_executive_dashboard(
            reader,
            project_id,
            (load_project_entries, load_portfolio_entries),
            NOW,
        )

    assert json.loads(json.dumps(result)) == expected
