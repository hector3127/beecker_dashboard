"""Población original de inversión en portada y detalle DM."""

from datetime import date
from types import SimpleNamespace

import pytest

from apps.portal.services import operational_sources


@pytest.mark.parametrize(
    ("include_suspended", "expected"),
    [
        (False, {"operational": 2.5, "commercial": 0}),
        (True, {"operational": 3.75, "commercial": 1.25}),
    ],
)
def test_original_includes_paused_only_for_dm(
    monkeypatch, include_suspended, expected
):
    projects = [
        SimpleNamespace(
            project_id=f"AMK.012_S{n}",
            name=f"Bloque {n}",
            start="01/10/26",
            end="31/10/26",
            status_code=status,
        )
        for n, status in [(1, ""), (2, "sus")]
    ]
    entries = [
        SimpleNamespace(
            entry_id=eid,
            project_id="AMK.012",
            task_name=task,
            description="",
            tags=tags,
            resource_name="Persona",
            entry_date=date(2026, 10, 5),
            duration_hours=1.25,
            is_billable=False,
        )
        for eid, task, tags in [
            ("a", "General S1", ["INV_OPERATIVA"]),
            ("b", "General S2", ["INV_OPERATIVA", "INV_COMERCIAL"]),
            ("c", "", ["INV_OPERATIVA"]),
        ]
    ]
    loader = SimpleNamespace(load_project=lambda *args: entries)
    monkeypatch.setattr(
        operational_sources, "build_sheet_repository", lambda: None
    )
    monkeypatch.setattr(
        operational_sources, "build_clockify_loader", lambda *args: loader
    )
    monkeypatch.setattr(operational_sources.cache, "get", lambda *args: None)
    monkeypatch.setattr(operational_sources.cache, "set", lambda *args: None)
    result = operational_sources.tagged_investment(
        projects, include_suspended=include_suspended
    )
    assert result["complete"]
    assert result["totals"] == expected
    assert result["projects"] == (2 if include_suspended else 1)
