"""Contrato original de selección de riesgos y pendientes del resumen IXS."""

import copy
import json
from pathlib import Path
from typing import Any

import pytest

from tests.contracts.test_ejecutivo_ixs_resumen_contract import evaluate

DATA = Path(__file__).parent / "ejecutivo_ixs_db/seguimiento.json"


def original_summary(case: Any) -> Any:
    template = json.loads(
        (DATA.parent / "resumen.json").read_text(encoding="utf-8")
    )["projects"][0]
    template = copy.deepcopy(template)
    template["risk_rows"] = case["risk_rows"]
    template["pending_rows"] = case["pending_rows"]
    result = evaluate(template)
    return {"raid": result["raid"], "risks": result["riesgosCriticos"]}


@pytest.mark.parametrize(
    "case",
    json.loads(DATA.read_text(encoding="utf-8")),
    ids=lambda c: c["name"],
)
def test_resumen_de_seguimiento_original(case: Any) -> None:
    assert original_summary(case) == case["expected"]
