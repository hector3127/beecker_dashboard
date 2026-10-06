"""Compara Capacidad instalada contra el Apps Script original.

expected_results.json es la salida de capacidadInstaladaBase() y
capacidadInstaladaDatosProyecto() del .gs original con sample_data.
"""

import copy
import json
from datetime import date
from pathlib import Path

import pytest

from apps.capacidad.services.orchestrator import (
    load_capacity_base,
    load_project_data,
)
from tests.capacidad import sample_data
from tests.capacidad.fakes import FakeAzureSource, build_report_loader
from tests.fakes import InMemorySheetRepository

TODAY = date(2026, 10, 2)
EXPECTED = json.loads(
    (Path(__file__).parent / "expected_results.json").read_text("utf-8"),
)


def build_reader():
    return InMemorySheetRepository(copy.deepcopy(sample_data.SHEETS))


@pytest.mark.parametrize(
    ("month", "expected"),
    list(zip(sample_data.BASE_SCENARIOS, EXPECTED["base"], strict=True)),
)
def test_capacity_base_matches_original(month, expected):
    result = load_capacity_base(build_reader, month, TODAY)

    assert json.loads(json.dumps(result)) == expected


@pytest.mark.parametrize(
    ("scenario", "expected"),
    list(zip(sample_data.PROJECT_SCENARIOS, EXPECTED["projects"], strict=True)),
)
def test_project_data_matches_original(scenario, expected):
    result = load_project_data(
        (*scenario, False),
        build_reader,
        FakeAzureSource,
        build_report_loader,
    )
    result = json.loads(json.dumps(result))

    if "aviso" in expected:
        assert result.pop("aviso").startswith("Proyecto Clockify: ")
        expected = {key: value for key, value in expected.items()}
        expected.pop("aviso")

    assert result == expected
