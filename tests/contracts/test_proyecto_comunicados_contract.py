"""Contrato de lectura original de Comunicados y filtro exacto del proyecto."""

import copy
import json
from pathlib import Path
from typing import Any

import pytest

from apps.daily.services.bee_com import list_communications

DATA = Path(__file__).parent / "comunicados_db/casos.json"


class Reader:
    def __init__(self, rows: Any) -> None:
        self.rows = rows
        self.writer = self

    def ensure_sheet(self, name: str, headers: Any) -> None:
        assert name == "Comunicados"

    def values(self, name: str) -> Any:
        return self.rows

    def write_cell(self, *args: Any) -> None:
        raise AssertionError(
            "El contrato exige una copia existente con encabezados completos"
        )


def evaluate(case: Any) -> Any:
    raw = list_communications(Reader(case["rows"]))["comunicados"]
    selected = [
        row
        for row in raw
        if not row["proyecto"] or row["proyecto"] == case["project"]
    ]
    return {
        "available": True,
        "items": [
            {
                "id": row["uid"],
                "date": row["fecha"],
                "title": row["titulo"],
                "summary": row["resumen"],
                "content": row["contenido"],
                "category": row["categoria"],
                "important": row["importante"],
                "author": row["autor"],
                "key_points": row["puntosClave"],
                "general": not row["proyecto"],
            }
            for row in selected
        ],
    }


@pytest.mark.parametrize(
    "case",
    json.loads(DATA.read_text(encoding="utf-8")),
    ids=lambda c: c["name"],
)
def test_comunicados_originales_sin_modificar_la_copia(case: Any) -> None:
    before = copy.deepcopy(case)
    assert evaluate(case) == case["expected"]
    assert case == before
