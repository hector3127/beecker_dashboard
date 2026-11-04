"""Contrato del motor de indicadores ejecutivos AER/T&M."""

import copy
import json
from datetime import date, datetime
from pathlib import Path
from typing import Any

import pytest

from apps.aer.services.dashboard import (
    alerts,
    build_kpis,
    health,
    unique_entries,
)
from core.time_entries.models import TimeEntry

CASES = json.loads(
    (Path(__file__).parent / "ejecutivo_aer_db/casos.json").read_text(
        encoding="utf-8"
    )
)


def entry_from(raw: Any) -> TimeEntry:
    values = dict(raw)
    for key in ("entry_date", "started_at", "ended_at"):
        values[key] = (
            datetime.fromisoformat(values[key]) if values[key] else None
        )
    values["tags"] = tuple(values["tags"])
    return TimeEntry(**values)


@pytest.mark.parametrize("case", CASES, ids=lambda case: case["name"])
def test_motor_ejecutivo_aer_conserva_el_contrato(case: Any) -> None:
    entries = [entry_from(row) for row in case["entries"]]
    plan = copy.deepcopy(case["plan"])
    kpis = build_kpis(
        case["row"], unique_entries(entries), date.fromisoformat(case["today"])
    )
    plan["tieneDatos"] = bool(plan["filas"])
    plan["avancePlanReferencia"] = (
        plan["avancePlan"] if plan["tieneDatos"] else kpis["pctTiempo"]
    )
    result = health(kpis, case["risks"], plan)
    kpis.update(
        healthScore=result["score"],
        healthLabel=result["label"],
        healthDimensiones=result["dimensiones"],
        healthFuentes={
            "tiempo": True,
            "esfuerzo": True,
            "costo": True,
            "riesgo": bool(case["risks"]["filas"]),
        },
    )
    actual = {
        "kpis": kpis,
        "alertas": alerts(kpis, case["risks"], case["actions"], plan),
        "plan": plan,
    }
    assert actual == case["expected"]
