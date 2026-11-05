"""Selección histórica ejecutada en manager_monthly_history original."""

import json
from datetime import date
from pathlib import Path
from types import SimpleNamespace

from apps.clockify.services import date_ranges
from apps.portal.services import operational_sources
from core.exceptions import DashboardError

PATH = Path(__file__).with_name("dm_historical_candidates.json")


def original_case(monkeypatch, case):
    reader = SimpleNamespace(
        read_as_objects=lambda name: (
            case["references"] if name == "Proyectos" else case["events"]
        ),
        sheet_exists=lambda *a: True,
        read_values=lambda *a: case["mpb"],
    )

    def resolve(pid):
        value = case["ranges"].get(pid)
        if value is None:
            raise DashboardError("Rango pendiente")
        return SimpleNamespace(
            start_date=date.fromisoformat(value[0]),
            end_date=date.fromisoformat(value[1]),
        )

    captured = []

    def investment(projects, **kwargs):
        captured.extend(vars(project) for project in projects)
        return {"complete": True, "monthly": []}

    monkeypatch.setattr(operational_sources.cache, "get", lambda *a: None)
    monkeypatch.setattr(operational_sources.cache, "set", lambda *a: None)
    monkeypatch.setattr(
        operational_sources, "build_sheet_repository", lambda: reader
    )
    monkeypatch.setattr(operational_sources, "tagged_investment", investment)
    monkeypatch.setattr(
        operational_sources.timezone,
        "localdate",
        lambda: date.fromisoformat(case["today"]),
    )
    monkeypatch.setattr(
        date_ranges,
        "ProjectDateRangeResolver",
        lambda *a: SimpleNamespace(resolve=resolve),
    )
    operational_sources.manager_monthly_history(
        case["manager"], [SimpleNamespace(**row) for row in case["current"]]
    )
    return captured


def test_original_historical_selection(monkeypatch):
    cases = json.loads(PATH.read_text(encoding="utf-8"))
    for case in cases:
        assert original_case(monkeypatch, case) == case["expected"]
