"""Contrato del respaldo original MPB/Histórico del Ejecutivo IXS."""

import json
from datetime import date
from pathlib import Path
from typing import Any

import pytest

from apps.ejecutivo.services.fallback_project import (
    fallback_project_row,
    history_dates,
)
from apps.ejecutivo.services.project_dashboard import build_history_block_rows
from tests.contracts.test_ejecutivo_proyectos_contract import Reader

DATA = Path(__file__).parent / "ejecutivo_ixs_db/ficha.json"


def evaluate(case: Any) -> Any:
    history = build_history_block_rows(case["history"], [])
    result = {
        "dates": history_dates(history, case["project"]),
        "row": fallback_project_row(
            Reader(case["sheets"]), case["project"], history, case["services"]
        ),
    }
    return json.loads(
        json.dumps(
            result,
            default=lambda value: (
                value.isoformat() if isinstance(value, date) else value
            ),
        )
    )


@pytest.mark.parametrize(
    "case",
    json.loads(DATA.read_text(encoding="utf-8")),
    ids=lambda c: c["name"],
)
def test_ficha_de_respaldo_original(case: Any) -> None:
    assert evaluate(case) == case["expected"]
