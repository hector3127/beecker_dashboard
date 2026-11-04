"""Contrato original del coordinador de recursos IXS con fuentes completas."""

import json
from datetime import datetime
from pathlib import Path
from typing import Any

import pytest

from apps.ejecutivo.services.project_orchestrator import load_project_detail
from tests.contracts.test_ejecutivo_aer_contract import entry_from

DATA = Path(__file__).parent / "ejecutivo_ixs_db/fuentes.json"


class Reader:
    def __init__(self, values: dict[str, Any]) -> None:
        self.values = values

    def sheet_exists(self, name: str) -> bool:
        return name in self.values

    def read_values(self, name: str) -> Any:
        return self.values[name]

    def read_as_objects(self, name: str) -> Any:
        values = self.values[name]
        if len(values) < 2:
            return []
        return [dict(zip(values[0], row, strict=True)) for row in values[1:]]


def evaluate(case: Any) -> Any:
    return load_project_detail(
        Reader(case["sheets"]),
        case["id"],
        lambda _: [entry_from(row) for row in case["entries"]],
        datetime.fromisoformat(case["now"]),
        case["extra_project_row"],
    )


@pytest.mark.parametrize(
    "case",
    json.loads(DATA.read_text(encoding="utf-8")),
    ids=lambda c: c["name"],
)
def test_fuentes_completas_del_detalle_original(case: Any) -> None:
    assert evaluate(case) == case["expected"]
