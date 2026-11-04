"""Contratos originales de ficha y rangos para el Ejecutivo AER/T&M."""

import copy
import json
from dataclasses import asdict
from datetime import date
from pathlib import Path
from typing import Any

import pytest

from apps.aer.services.dashboard import (
    AerError,
    find_project,
    mpb_finalized,
    mpb_project_row,
)
from apps.clockify.services.date_ranges import ProjectDateRangeResolver
from apps.ejecutivo.services.fallback_project import missing_data
from core.sheets.repository import build_row_object

CASES = json.loads(
    (Path(__file__).parent / "ejecutivo_aer_db/proyectos.json").read_text(
        encoding="utf-8"
    )
)


class Reader:
    def __init__(self, sheets: Any) -> None:
        self.sheets = sheets

    def sheet_exists(self, name: str) -> bool:
        return name in self.sheets

    def read_values(self, name: str) -> Any:
        return copy.deepcopy(self.sheets[name])

    def read_as_objects(self, name: str) -> Any:
        values = self.sheets[name]
        return (
            [
                build_row_object(values[0], row)
                for row in values[1:]
                if any(c != "" and c is not None for c in row)
            ]
            if values
            else []
        )


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["name"])
def test_ficha_y_rango_originales(case: Any) -> None:
    reader = Reader(case["sheets"])
    project = case["project"]
    result = {}
    try:
        try:
            row = find_project(reader.read_as_objects("Proyectos"), project)
        except AerError:
            row = mpb_project_row(reader, project)
            if row is None:
                raise
        result.update(
            row=row,
            notes=missing_data(row),
            closed=mpb_finalized(reader, project),
        )
    except AerError as error:
        result["error"] = str(error)
    value = asdict(
        ProjectDateRangeResolver(
            reader, date.fromisoformat(case["day"])
        ).resolve(project)
    )
    result["range"] = {
        key: item.isoformat() if isinstance(item, date) else item
        for key, item in value.items()
    }
    assert result == case["expected"]
