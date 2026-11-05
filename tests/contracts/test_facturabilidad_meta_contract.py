"""Meta y brecha mensual del motor Operations original."""

import json
from pathlib import Path
from types import SimpleNamespace

from apps.portal.api.plain import plain
from apps.portal.services.operations_summary import build_operations_summary

VALUES = [None, 0, 35.25, 70, 75.5, 156.78, 70.005]
PATH = Path(__file__).with_name("facturabilidad_meta.json")


def original_comparison() -> dict[str, object]:
    """Proyecta únicamente meta y brecha del resumen original de cada mes."""
    months = {}
    for index, value in enumerate(VALUES, 1):
        key = f"2026-{index:02}"
        row = SimpleNamespace(
            month=key,
            label=key,
            short_label=str(index),
            global_percent=value,
            fixed_percent=None,
            variable_percent=None,
            error="",
        )
        summary = build_operations_summary([row])
        months[key] = {"gap": summary.gap, "gap_abs": summary.gap_abs}
    return {"target": summary.target, "months": months}


def test_meta_y_brecha_del_original() -> None:
    expected = json.loads(PATH.read_text(encoding="utf-8"))
    assert plain(original_comparison()) == expected["expected"]
