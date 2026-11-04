"""Contrato original de resolución de proveedor y selección CR del Ejecutivo."""

import json
from dataclasses import asdict
from datetime import date
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from zoneinfo import ZoneInfo

import pytest

from apps.clockify.services.clockify_client import ClockifyProject
from apps.clockify.services.project_matcher import resolve_clockify_project
from apps.clockify.services.time_entry_loader import (
    ClockifyTimeEntryLoader,
    ReportPlan,
)

DATA = Path(__file__).parent / "ejecutivo_aer_db/proveedor.json"


def evaluate_match(case: Any) -> Any:
    project = resolve_clockify_project(
        case["id"],
        [ClockifyProject(**p) for p in case["projects"]],
        case["links"],
        strict=case["strict"],
    )
    return project.project_id if project else None


def evaluate_scope(case: Any) -> Any:
    fake: Any = SimpleNamespace(
        _monthly_report=lambda *args: (case["rows"], 0),
        _timezone=ZoneInfo("America/Mexico_City"),
        load_project_tasks=lambda *args: case["tasks"],
    )
    plan = ReportPlan(
        "AER.DEMO.001_CR1",
        "p1",
        date(2026, 10, 1),
        date(2026, 10, 31),
        case["scope"],
    )
    entries, count = ClockifyTimeEntryLoader._download_report(fake, plan, {})
    result = []
    for entry in entries:
        row = asdict(entry)
        for key in ("entry_date", "started_at", "ended_at"):
            row[key] = row[key].isoformat() if row[key] else None
        row["tags"] = list(row["tags"])
        result.append(row)
    assert count == 0
    return result


def cases() -> Any:
    return json.loads(DATA.read_text(encoding="utf-8"))


@pytest.mark.parametrize("case", cases()["matches"], ids=lambda c: c["name"])
def test_resolucion_original(case: Any) -> None:
    assert evaluate_match(case) == case["expected"]


@pytest.mark.parametrize("case", cases()["scopes"], ids=lambda c: c["name"])
def test_seleccion_original(case: Any) -> None:
    assert evaluate_scope(case) == case["expected"]
