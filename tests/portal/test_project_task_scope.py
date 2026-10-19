from datetime import date, datetime
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from django.core.cache import cache

from apps.portal.services import revenue_costs
from apps.portal.services.project_task_scope import scope_entries
from core.time_entries.models import TimeEntry


def entry(key, task, hours=1, task_id=""):
    return TimeEntry(
        key,
        "AMK.008",
        "Ana",
        datetime(2026, 5, 1),
        hours,
        True,
        0,
        task_name=task,
        task_id=task_id,
    )


def test_base_and_variants_are_disjoint_and_case_insensitive():
    rows = [
        entry("base", "Development"),
        entry("s4", "AMK.008_s4 - Development"),
        entry("s40", "S40 Design"),
        entry("s5", "S5: Test"),
    ]
    ids = ["AMK.008", "AMK.008_s4", "AMK.008_S5"]
    base = scope_entries("AMK.008", ids, rows, Mock(), "AMK.008")
    s4 = scope_entries("AMK.008_s4", ids, rows, Mock(), "AMK.008_s4")
    assert [e.entry_id for e in base] == ["base", "s40"]
    assert [e.entry_id for e in s4] == ["s4"]
    assert not {e.entry_id for e in base} & {e.entry_id for e in s4}
    assert (
        scope_entries("AMK.008", ["AMK.008"], rows, Mock(), "AMK.008") == rows
    )


def test_missing_task_names_are_resolved_before_exclusion():
    loader = Mock()
    loader.find_clockify_project.return_value = SimpleNamespace(
        project_id="clockify-id"
    )
    loader.load_project_tasks.return_value = [
        {"id": "t4", "name": "S4 - Support"}
    ]
    rows = [entry("s4", "", task_id="t4"), entry("base", "General")]
    assert [
        e.entry_id
        for e in scope_entries(
            "AMK.008", ["AMK.008", "AMK.008_S4"], rows, loader, "AMK.008"
        )
    ] == ["base"]
    loader.load_project_tasks.return_value = []
    with pytest.raises(ValueError):
        scope_entries(
            "AMK.008", ["AMK.008", "AMK.008_S4"], rows, loader, "AMK.008"
        )


def test_project_costs_do_not_duplicate_variant_hours(monkeypatch):
    cache.clear()
    loader = Mock()
    loader.load_project.return_value = [
        entry("base", "General", 10),
        entry("s4", "S4 - Development", 5),
    ]
    monkeypatch.setattr(
        revenue_costs, "build_clockify_loader", lambda reader: loader
    )
    ids = ["AMK.008", "AMK.008_S4"]
    context = SimpleNamespace(
        reader=object(),
        ids=ids,
        allowed_ids={p.casefold() for p in ids},
        today=date(2026, 10, 15),
        rates={"A2": 7},
        bands={"ana": ("A2", "Octubre")},
    )
    base = revenue_costs.calculate_project_cost(ids[0], context)
    child = revenue_costs.calculate_project_cost(ids[1], context)
    assert (base["hours"], base["cost"]) == (10, 70)
    assert (child["hours"], child["cost"]) == (5, 35)
    assert set(cache.get(revenue_costs.key(ids[0]))["entries"]).isdisjoint(
        cache.get(revenue_costs.key(ids[1]))["entries"]
    )
    cache.clear()


def test_base_revenue_covers_sprints_and_general_without_allocating_income(
    monkeypatch,
):
    cache.clear()
    loader = Mock()
    loader.load_project.return_value = [
        entry("base", "General", 2),
        entry("s1", "S1 - Discovery", 10),
        entry("s2", "CCO.002_S2 Development", 20),
        entry("s2", "CCO.002_S2 Development", 20),
    ]
    monkeypatch.setattr(
        revenue_costs, "build_clockify_loader", lambda reader: loader
    )
    context = SimpleNamespace(
        reader=object(),
        ids=["CCO.002"],
        allowed_ids={"cco.002"},
        today=date(2026, 10, 15),
        rates={"A2": 7},
        bands={"ana": ("A2", "Octubre")},
    )
    result = revenue_costs.calculate_project_cost("CCO.002", context)
    groups = {g["label"]: g for g in result["sprints"]}
    assert result["hours"] == 32 and result["cost"] == 224
    assert groups["S1"]["hours"] == 10 and groups["S1"]["cost"] == 70
    assert groups["S2"]["hours"] == 20 and groups["S2"]["cost"] == 140
    assert groups["Sin sprint"]["hours"] == 2
    assert sum(g["hours"] for g in groups.values()) == result["hours"]
    assert all("revenue" not in g for g in groups.values())
    cache.clear()
