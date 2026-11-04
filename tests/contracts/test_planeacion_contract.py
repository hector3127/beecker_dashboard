"""Contrato de la planeación manual AER e IXS para su integración en Genesis."""

import json
from datetime import date
from pathlib import Path
from typing import Any

import pytest

from apps.aer.constants import SHEET_DATE_COLUMNS
from apps.aer.services.aer_values import sheet_date
from apps.aer.services.people_client import vacations
from apps.aer.services.plan import plan_summary
from apps.daily.services.ixs_planning import read_plan_for

CASES = json.loads(
    (Path(__file__).parent / "planeacion_db/casos.json").read_text(
        encoding="utf-8"
    )
)


class Store:
    """Hojas y reloj del escenario sin llamadas externas ni escrituras."""

    def __init__(self, sheets: Any, day: str) -> None:
        self.sheets = sheets
        self.day = date.fromisoformat(day)
        self.writer = self

    def read(self, name: str) -> Any:
        rows = self.sheets[name]
        return [
            {
                "_row": index,
                **{
                    key: sheet_date(value)
                    if key in SHEET_DATE_COLUMNS
                    else value
                    for key, value in zip(rows[0], row, strict=False)
                },
            }
            for index, row in enumerate(rows[1:], 2)
        ]

    def values(self, name: str) -> Any:
        return self.sheets.get(name, [])

    def today(self) -> date:
        return self.day

    def ensure_sheet(self, name: str, headers: Any) -> None:
        assert self.sheets[name][0] == list(headers)


@pytest.mark.parametrize("case", CASES)
def test_planeacion_del_dashboard_permanece_igual(case: Any) -> None:
    store = Store(case["sheets"], case["day"])
    if case["family"] == "aer":
        actual = {
            "plan": plan_summary(store, case["project"]),
            "vacaciones": vacations(store, case["project"])["filas"],
        }
    else:
        actual = {
            "plan": read_plan_for(store, case["project"]),
            "vacaciones": None,
        }
    assert actual == case["expected"]
