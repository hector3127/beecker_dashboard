"""Contrato original del detalle de recursos y costos IXS."""

import json
from datetime import datetime
from pathlib import Path
from typing import Any

import pytest

from apps.ejecutivo.services.project_detail import (
    ProjectDetailSources,
    build_error_detail,
    build_project_detail,
    resource_status,
)
from core.time_entries.resource_rates import load_band_info_by_resource
from tests.contracts.test_ejecutivo_aer_contract import entry_from

DATA = Path(__file__).parent / "ejecutivo_ixs_db/recursos.json"


class Reader:
    def __init__(self, bands: Any, rates: Any) -> None:
        self.sheets = {"Banda salarial": bands, "Master rates": rates}

    def sheet_exists(self, name: str) -> bool:
        return name in self.sheets

    def read_values(self, name: str) -> Any:
        return self.sheets[name]


def evaluate(case: Any) -> Any:
    sources = ProjectDetailSources(
        project_rows=case["project_rows"],
        resource_rows=case["resource_rows"],
        entries=[entry_from(row) for row in case["entries"]],
        band_info=load_band_info_by_resource(
            Reader(case["bands"], case["rates"])
        ),
        include_unassigned=case["include_unassigned"],
    )
    return build_project_detail(
        case["id"], sources, datetime.fromisoformat(case["now"])
    )


def cases() -> Any:
    return json.loads(DATA.read_text(encoding="utf-8"))


@pytest.mark.parametrize("case", cases()["detail"], ids=lambda c: c["name"])
def test_detalle_ixs_original(case: Any) -> None:
    assert evaluate(case) == case["expected"]


@pytest.mark.parametrize("case", cases()["bands"], ids=lambda c: c["name"])
def test_bandas_ixs_originales(case: Any) -> None:
    actual = load_band_info_by_resource(Reader(case["bands"], case["rates"]))
    assert {key: list(value) for key, value in actual.items()} == case[
        "expected"
    ]


@pytest.mark.parametrize("case", cases()["states"])
def test_estado_recurso_original(case: Any) -> None:
    assert resource_status(*case["input"]) == case["expected"]


def test_formato_error_original() -> None:
    assert (
        build_error_detail("AMK.001_S1", "Fuente faltante") == cases()["error"]
    )
