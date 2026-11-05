"""Contrato del lector original de asignaciones IXS sin acceso a proveedores."""

import copy
import json
from pathlib import Path

import pytest

from apps.daily.services.ixs_planning import read_resources_for

DATA = Path(__file__).parent / "asignaciones_db/casos.json"


class Store:
    def __init__(self, rows):
        self.rows = copy.deepcopy(rows)
        self.reader = self
        self.writer = self

    def sheet_exists(self, name):
        return name == "Recursos"

    def values(self, name):
        return self.rows

    def write_cell(self, name, row, column, value):
        self.rows[row - 1] += [""] * max(0, column - len(self.rows[row - 1]))
        self.rows[row - 1][column - 1] = value


def evaluate(case):
    return read_resources_for(Store(case["rows"]), case["project"])["filas"]


@pytest.mark.parametrize(
    "case",
    json.loads(DATA.read_text(encoding="utf-8")),
    ids=lambda c: c["name"],
)
def test_asignaciones_originales(case):
    before = copy.deepcopy(case)
    assert evaluate(case) == case["expected"]
    assert case == before
