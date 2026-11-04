"""Contrato original del Resumen Ejecutivo IXS completo y sus hitos."""

import json
from datetime import datetime
from pathlib import Path
from typing import Any

import pytest

from apps.ejecutivo.services.additional_milestones import (
    last_column_count,
    list_milestone_types,
    read_additional_milestones,
)
from apps.ejecutivo.services.project_dashboard import (
    ExecutiveSources,
    build_executive_dashboard,
)
from core.exceptions import InvalidRequestError
from tests.contracts.test_ejecutivo_aer_contract import entry_from

DATA = Path(__file__).parent / "ejecutivo_ixs_db/resumen.json"


def evaluate(case: Any) -> Any:
    sources = ExecutiveSources(
        project_rows=case["project_rows"],
        project_values=case["project_values"],
        history_rows=case["history_rows"],
        history_values=case["history_values"],
        portfolio_entries=[entry_from(row) for row in case["entries"]],
        detail=case["detail"],
        risk_rows=case["risk_rows"],
        pending_rows=case["pending_rows"],
        stage_work_items={
            key: tuple(value) for key, value in case["items"].items()
        },
    )
    try:
        return build_executive_dashboard(
            case["project_id"], sources, datetime.fromisoformat(case["now"])
        )
    except InvalidRequestError as error:
        return {"error": str(error)}


def cases() -> Any:
    return json.loads(DATA.read_text(encoding="utf-8"))


@pytest.mark.parametrize("case", cases()["projects"], ids=lambda c: c["name"])
def test_resumen_ixs_original_completo(case: Any) -> None:
    assert evaluate(case) == case["expected"]


@pytest.mark.parametrize("case", cases()["additional"], ids=lambda c: c["name"])
def test_hitos_adicionales_originales(case: Any) -> None:
    assert (
        read_additional_milestones(case["values"], case["id"])
        == case["expected"]
    )
    assert list_milestone_types(case["values"]) == case["types"]
    assert last_column_count(case["values"]) == case["columns"]
