"""Histórico mensual original: categorías, deduplicación y presupuesto."""

import json
from datetime import date
from pathlib import Path
from types import SimpleNamespace

from apps.portal.services import operational_sources

PATH = Path(__file__).with_name("dm_monthly_hours.json")


def original_case(monkeypatch, case):
    reader = SimpleNamespace(
        read_as_objects=lambda *a: [],
        sheet_exists=lambda *a: False,
        read_values=lambda *a: [],
    )
    entries = [
        SimpleNamespace(
            entry_id=row["id"],
            project_id="provider",
            resource_name="Persona",
            entry_date=date.fromisoformat(row["day"]),
            duration_hours=row["hours"],
            tags=row["tags"],
            task_name=row["task"],
            description=row.get("description", ""),
            is_billable=row["billable"],
        )
        for row in case["entries"]
    ]
    loader = SimpleNamespace(
        load_project=lambda pid, period: [
            row for row in entries if period[0] <= row.entry_date <= period[1]
        ]
    )
    monkeypatch.setattr(
        operational_sources, "build_sheet_repository", lambda: reader
    )
    monkeypatch.setattr(
        operational_sources, "build_clockify_loader", lambda *a: loader
    )
    monkeypatch.setattr(operational_sources.cache, "get", lambda *a: None)
    monkeypatch.setattr(operational_sources.cache, "set", lambda *a: None)
    monkeypatch.setattr(
        operational_sources.timezone,
        "localdate",
        lambda: date.fromisoformat(case["today"]),
    )
    result = operational_sources.manager_monthly_history(
        "Ana", [SimpleNamespace(**p) for p in case["projects"]]
    )
    return result["monthly"]


def test_original_monthly_hours(monkeypatch):
    for case in json.loads(PATH.read_text(encoding="utf-8")):
        assert original_case(monkeypatch, case) == case["expected"]
