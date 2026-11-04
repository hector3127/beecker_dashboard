"""Contrato del conteo original de WI del Resumen Ejecutivo IXS."""

import json
from pathlib import Path
from typing import Any

import pytest

from apps.ejecutivo.services.azure_stages import count_work_items, infer_sprint

DATA = Path(__file__).parent / "ejecutivo_ixs_db/azure.json"


def evaluate(case: Any) -> Any:
    sprint = infer_sprint(case["project"])
    counts = count_work_items(case["items"], [sprint])
    return {"sprint": sprint, "counts": counts}


@pytest.mark.parametrize(
    "case",
    json.loads(DATA.read_text(encoding="utf-8")),
    ids=lambda c: c["name"],
)
def test_conteos_originales_por_nomenclatura(case: Any) -> None:
    assert evaluate(case) == case["expected"]
