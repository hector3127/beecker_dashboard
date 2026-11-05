"""Conteos originales AER abiertos, sin tocar hojas ni caché real."""

import json
from pathlib import Path

from apps.portal.services import operational_sources


def test_original_open_risks(monkeypatch):
    case = json.loads(
        Path(__file__).with_name("dm_risks.json").read_text(encoding="utf-8")
    )
    rows = [
        dict(zip(case["rows"][0], row, strict=False))
        for row in case["rows"][1:]
    ]
    monkeypatch.setattr(operational_sources.cache, "get", lambda *args: rows)
    assert (
        operational_sources.aer_open_risks(case["projects"]) == case["expected"]
    )
