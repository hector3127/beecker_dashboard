"""Contrato original del Ejecutivo AER con fuentes completas."""

import copy
import json
from datetime import date
from pathlib import Path
from typing import Any

import pytest

from apps.aer.constants import SHEET_DATE_COLUMNS
from apps.aer.services.aer_values import sheet_date
from apps.aer.services.dashboard import (
    alerts,
    build_kpis,
    health,
    unique_entries,
)
from apps.aer.services.plan import plan_summary
from apps.aer.services.risks_actions import actions_summary, risks_summary
from tests.contracts.test_ejecutivo_aer_contract import entry_from

DATA = Path(__file__).parent / "ejecutivo_aer_db/completo.json"


class Store:
    def __init__(self, sheets: Any, day: str) -> None:
        self.sheets = copy.deepcopy(sheets)
        self.day = date.fromisoformat(day)

    def read(self, name: str) -> Any:
        rows = self.sheets[name]
        return [
            {
                "_row": index,
                **{
                    key: sheet_date(value)
                    if key in SHEET_DATE_COLUMNS
                    else value
                    for key, value in zip(rows[0], row, strict=False)
                },
            }
            for index, row in enumerate(rows[1:], 2)
        ]

    def values(self, name: str) -> Any:
        return self.sheets[name]

    def delete_rows(self, name: str, numbers: Any) -> None:
        self.sheets[name] = [
            row
            for index, row in enumerate(self.sheets[name], 1)
            if index not in numbers
        ]

    def today(self) -> date:
        return self.day


def evaluate(case: Any) -> Any:
    store = Store(case["sheets"], case["today"])
    project = case["project"]
    plan = plan_summary(store, project)
    risks = risks_summary(store, project)
    actions = actions_summary(store, project)
    risks["tieneDatos"] = bool(risks["filas"])
    actions["tieneDatos"] = bool(actions["filas"])
    plan["tieneDatos"] = bool(plan["filas"])
    kpis = build_kpis(
        case["row"],
        unique_entries([entry_from(e) for e in case["entries"]]),
        store.today(),
    )
    plan["avancePlanReferencia"] = (
        plan["avancePlan"] if plan["tieneDatos"] else kpis["pctTiempo"]
    )
    result = health(kpis, risks, plan)
    kpis.update(
        healthScore=result["score"],
        healthLabel=result["label"],
        healthDimensiones=result["dimensiones"],
        healthFuentes={
            "tiempo": True,
            "esfuerzo": True,
            "costo": True,
            "riesgo": risks["tieneDatos"],
        },
    )
    return {
        "kpis": kpis,
        "plan": plan,
        "riesgos": risks,
        "acciones": actions,
        "alertas": alerts(kpis, risks, actions, plan),
    }


def cases() -> Any:
    return json.loads(DATA.read_text(encoding="utf-8"))


@pytest.mark.parametrize("case", cases(), ids=lambda c: c["name"])
def test_ejecutivo_original_con_fuentes_completas(case: Any) -> None:
    assert evaluate(case) == case["expected"]
