"""Contrato del panel Azure IXS y su avance guardado para Genesis."""

import json
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from unittest.mock import patch

import pytest

from apps.daily.services.daily_sheets import load_progress_map
from apps.daily.services.ixs_panel import (
    build_raw_item,
    filter_project_items,
    load_panel,
)

CASES = json.loads(
    (Path(__file__).parent / "azure_panel_db/casos.json").read_text(
        encoding="utf-8"
    )
)


class Progress:
    """Matriz de avance del escenario sin escritor."""

    def __init__(self, values: Any) -> None:
        self.values = values

    def rows(self, name: str, headers: Any) -> Any:
        return [
            dict(zip(self.values[0], row, strict=False))
            for row in self.values[1:]
        ]


@pytest.mark.parametrize("case", CASES)
def test_panel_azure_original_conserva_su_contrato(case: Any) -> None:
    progress = (
        load_progress_map(Progress(case["progress"]))
        if case["progress"]
        else {}
    )
    selected = filter_project_items(
        case["payloads"], case["project"], case["source"]
    )
    raw = {
        "workItems": [
            build_raw_item(item, "org-contrato", case["source"])
            for item in selected
        ],
        "limitReached": False,
        "totalTeamProject": len(case["payloads"]),
    }
    azure = SimpleNamespace(
        organization="org-contrato",
        personal_access_token="contrato-sin-red",
        resolve_project=lambda project: case["source"],
        load_progress=lambda: progress,
    )
    now_ms = int(datetime.fromisoformat(case["now"]).timestamp() * 1000)
    with patch(
        "apps.daily.services.ixs_panel.load_raw_items", return_value=(raw, "")
    ):
        actual = load_panel(azure, case["project"], False, now_ms)
    assert actual == case["expected"]
