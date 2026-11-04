"""Contrato original de etapas, avance y riesgo del Ejecutivo IXS."""

import json
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Any

import pytest

from apps.ejecutivo.services.history_stages import (
    calculate_work_item_progress,
    estimate_stage_progress,
    milestones_from_stages,
    read_history_stages,
    stage_day,
)
from apps.ejecutivo.services.project_dashboard import (
    calculate_date_risk,
    calculate_general_status,
    calculate_progress,
    current_history_status,
    progress_source,
)

DATA = Path(__file__).parent / "ejecutivo_ixs_db/casos.json"


def evaluate(case: Any) -> Any:
    now = datetime.fromisoformat(case["now"])
    stages = read_history_stages(case["history"], case["project_id"])
    milestones = (
        milestones_from_stages(stages, case["previous"], now.date())
        if stages
        else case["previous"]
    )
    phases = milestones.get("lista", [])
    progress = calculate_progress(
        case["project"],
        milestones,
        phases,
        tuple(case["consumption"]),
        now,
        {key: tuple(value) for key, value in case["work_items"].items()},
    )
    state = current_history_status(
        case["project"].get("Estado"), milestones, now
    )
    general = calculate_general_status(
        {**case["project"], "Estado": state}, case["consumption"][1], progress
    )
    return {
        "stages": asdict(stages) if stages else None,
        "milestones": milestones,
        "estimate": asdict(estimate_stage_progress(phases, now)),
        "progress": asdict(progress),
        "status": state,
        "general": list(general),
        "date_risk": calculate_date_risk(
            case["project"].get("Fecha_Fin_Estimada"), now
        ),
        "source": progress_source(progress, phases),
    }


def cases() -> Any:
    return json.loads(DATA.read_text(encoding="utf-8"))


@pytest.mark.parametrize("case", cases()["projects"], ids=lambda c: c["name"])
def test_motor_ixs_original(case: Any) -> None:
    assert evaluate(case) == case["expected"]


@pytest.mark.parametrize("case", cases()["days"])
def test_fecha_de_etapa_original(case: Any) -> None:
    result = stage_day(case["value"])
    assert (result.isoformat() if result else None) == case["expected"]


@pytest.mark.parametrize("case", cases()["items"])
def test_avance_wi_original(case: Any) -> None:
    assert calculate_work_item_progress(*case["input"]) == case["expected"]
