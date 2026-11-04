"""Contrato original de horas por nomenclatura del detalle IXS."""

import json
from pathlib import Path
from typing import Any

import pytest

from apps.ejecutivo.services.ixb_rules import (
    extract_nomenclature,
    project_nomenclature,
)
from apps.ejecutivo.services.project_hours import (
    hierarchy_nomenclature,
    load_hierarchy_entries,
)
from tests.contracts.test_ejecutivo_aer_contract import entry_from

DATA = Path(__file__).parent / "ejecutivo_ixs_db/horas.json"


def evaluate(case: Any) -> Any:
    entries = [entry_from(raw) for raw in case["entries"]]
    return {
        "nomenclature": hierarchy_nomenclature(case["id"], case["projects"]),
        "entries": [
            entry.entry_id
            for entry in load_hierarchy_entries(
                case["id"], case["projects"], lambda project: entries
            )
        ],
    }


def cases() -> Any:
    return json.loads(DATA.read_text(encoding="utf-8"))


@pytest.mark.parametrize("case", cases()["filters"], ids=lambda c: c["name"])
def test_filtro_de_jerarquia_original(case: Any) -> None:
    assert evaluate(case) == case["expected"]


@pytest.mark.parametrize("case", cases()["text"])
def test_extraccion_original(case: Any) -> None:
    assert extract_nomenclature(case["input"]) == case["expected"]


@pytest.mark.parametrize("case", cases()["ids"])
def test_nomenclatura_de_id_original(case: Any) -> None:
    assert project_nomenclature(case["input"]) == case["expected"]
