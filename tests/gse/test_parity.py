"""Compara GSE contra el Apps Script original.

expected_results.json es la salida de gseObtenerAreas(), gseObtenerMes(),
gseObtenerLoteBase() y gseObtenerAnoBase() del .gs original con
sample_data (el lote se corrio con bloques de 4 filas).
"""

import copy
import json
from datetime import UTC, date, datetime
from pathlib import Path

import pytest

from apps.gse.services import batch_read
from apps.gse.services.base_store import BaseStore, Connection
from apps.gse.services.batch_read import get_batch
from apps.gse.services.month_report import GseContext, get_month
from apps.gse.services.roster import list_areas
from apps.gse.services.year_base import get_year
from core.exceptions import DashboardError, describe_error
from tests.fakes import InMemorySheetRepository
from tests.gse import sample_data

NOW = datetime(2026, 10, 2, 18, 0, tzinfo=UTC)
TODAY = date(2026, 10, 2)
EXPECTED = json.loads(
    (Path(__file__).parent / "expected_results.json").read_text("utf-8"),
)


def build_context(dataset):
    reader = InMemorySheetRepository(
        copy.deepcopy(sample_data.build_datasets()[dataset]),
    )
    connection = Connection(sample_data.WORKSPACE, sample_data.CONNECTION)

    def no_api(month, force, user_ids):
        raise AssertionError("La fuente sheet no debe llamar a Clockify")

    return GseContext(reader, BaseStore(reader, connection, NOW), no_api)


@pytest.fixture(autouse=True)
def small_batches(monkeypatch):
    monkeypatch.setattr(batch_read, "BATCH_SIZE", sample_data.BATCH_SIZE)


@pytest.mark.parametrize(
    ("dataset", "expected"), list(EXPECTED["areas"].items())
)
def test_areas_match_original(dataset, expected):
    reader = build_context(dataset).reader

    try:
        result = {"ok": True, "areas": list_areas(reader)}
    except DashboardError as error:
        result = {"ok": False, "error": describe_error(error)}

    assert result == expected


@pytest.mark.parametrize(
    ("scenario", "expected"),
    list(zip(sample_data.MONTH_SCENARIOS, EXPECTED["months"], strict=True)),
)
def test_month_matches_original(scenario, expected):
    dataset, month, source, force, area = scenario

    result = get_month(build_context(dataset), (month, source, force, area))

    assert json.loads(json.dumps(result)) == expected


@pytest.mark.parametrize(
    ("scenario", "expected"),
    list(zip(sample_data.BATCH_SCENARIOS, EXPECTED["batches"], strict=True)),
)
def test_batch_matches_original(scenario, expected):
    dataset, year, area, cursor, expected_rows = scenario

    result = get_batch(
        build_context(dataset),
        (year, area, cursor, expected_rows),
    )
    result.pop("milliseconds", None)

    assert json.loads(json.dumps(result)) == expected


@pytest.mark.parametrize(
    ("scenario", "expected"),
    list(zip(sample_data.YEAR_SCENARIOS, EXPECTED["years"], strict=True)),
)
def test_year_matches_original(scenario, expected):
    dataset, year, area = scenario

    result = get_year(build_context(dataset), (year, area), TODAY)
    result.pop("milliseconds", None)

    assert json.loads(json.dumps(result)) == expected
