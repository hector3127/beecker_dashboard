"""Contratos originales de las entradas y tarifas del Ejecutivo AER."""

import json
from dataclasses import asdict
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import pytest

from apps.clockify.services.report_mapper import build_time_entry_from_report
from core.time_entries.resource_rates import (
    normalize_band,
    read_band_by_name,
    read_rate_by_band,
)

CASES = json.loads(
    (Path(__file__).parent / "ejecutivo_aer_db/clockify.json").read_text(
        encoding="utf-8"
    )
)


@pytest.mark.parametrize("case", CASES["reports"], ids=lambda c: c["name"])
def test_reporte_ejecutivo_original(case: Any) -> None:
    actual = asdict(
        build_time_entry_from_report(
            case["raw"],
            "AER.DEMO.001",
            case["rates"],
            ZoneInfo("America/Mexico_City"),
        )
    )
    for key in ("entry_date", "started_at", "ended_at"):
        actual[key] = actual[key].isoformat() if actual[key] else None
    actual["tags"] = list(actual["tags"])
    assert actual == case["expected"]


@pytest.mark.parametrize("case", CASES["rates"], ids=lambda c: c["name"])
def test_tarifas_ejecutivo_original(case: Any) -> None:
    bands = read_band_by_name(case["bands"])
    rates = read_rate_by_band(case["values"])
    assert {
        name: rates.get(normalize_band(band), 0.0)
        for name, band in bands.items()
    } == case["expected"]
