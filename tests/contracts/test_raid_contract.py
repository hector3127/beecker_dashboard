"""Contrato de selección y detalle RAID del dashboard para Genesis."""

import copy
import json
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from apps.aer.constants import SHEET_DATE_COLUMNS
from apps.aer.services.aer_values import sheet_date
from apps.aer.services.risks_actions import risks_summary
from apps.daily.services.ixs_panel import (
    build_raw_item,
    filter_project_items,
    merge_progress,
)
from apps.daily.services.ixs_raid import build_raid_row

CASES = json.loads(
    (Path(__file__).parent / "raid_db/casos.json").read_text(encoding="utf-8")
)


class Store:
    """Matriz privada del escenario, con limpieza solo en memoria."""

    def __init__(self, rows: Any) -> None:
        self.rows = copy.deepcopy(rows)

    def values(self, name: str) -> Any:
        return self.rows

    def read(self, name: str) -> Any:
        return [
            {
                "_row": index,
                **{
                    key: sheet_date(value)
                    if key in SHEET_DATE_COLUMNS
                    else value
                    for key, value in zip(self.rows[0], row, strict=False)
                },
            }
            for index, row in enumerate(self.rows[1:], 2)
        ]

    def delete_rows(self, name: str, numbers: Any) -> None:
        self.rows = [
            row
            for index, row in enumerate(self.rows, 1)
            if index not in numbers
        ]


@pytest.mark.parametrize("case", CASES)
def test_raid_del_dashboard_permanece_igual(case: Any) -> None:
    if case["family"] == "aer":
        assert (
            risks_summary(Store(case["rows"]), case["project"])
            == case["expected"]
        )
        return
    now_ms = int(datetime.fromisoformat(case["now"]).timestamp() * 1000)
    context = SimpleNamespace(
        organization=case["organization"], azure_project=case["azure"]
    )
    selected = filter_project_items(
        case["payloads"], case["project"], case["azure"]
    )
    actual = []
    for item in selected:
        raw = merge_progress(
            build_raw_item(item, case["organization"], case["azure"]),
            None,
            now_ms,
        )
        if str(raw["tipo"]).upper() in {"RISK", "ISSUE", "OPPORTUNITY"}:
            actual.append(build_raid_row(raw, item, context))
    assert actual == case["expected"]
