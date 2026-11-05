"""Evaluaciones AER existentes: contrato del lector original sin escrituras."""

import json
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace

from apps.aer.constants import MANUAL_SHEETS, SHEET_EVALUATIONS
from apps.aer.services.manual_store import AerStore
from apps.aer.services.people_client import evaluations

PATH = Path(__file__).with_name("aer_evaluations.json")
HEADERS = list(MANUAL_SHEETS[SHEET_EVALUATIONS])


def original_cases():
    cases = [
        ("vacio", []),
        (
            "umbrales_y_limites",
            [
                {"UID": str(i), "Recurso": f"Persona {i}", "Score": score}
                for i, score in enumerate(
                    [0, 69.5, 70, 79.5, 80, 89.5, 90, 100, 101, -1]
                )
            ],
        ),
        (
            "promedio_dimensiones",
            [
                {
                    "Recurso": "Ana",
                    "Score": 0,
                    "Calidad": 100,
                    "Cumplimiento": 90,
                    "Comunicacion": 80,
                    "Colaboracion": 70,
                    "Autonomia": 60,
                },
                {
                    "Recurso": "Beto",
                    "Score": "",
                    "Calidad": "75.5",
                    "Cumplimiento": -10,
                    "Comunicacion": "mal",
                    "Colaboracion": None,
                    "Autonomia": 0,
                },
            ],
        ),
        (
            "categoria_y_texto",
            [
                {
                    "UID": "U1",
                    "Recurso": " Ana ",
                    "Score": "80.5",
                    "Categoria": "Personalizada",
                    "Comentario": "<texto>",
                    "Plan_Accion": "Plan",
                    "Evaluador": "DM",
                    "Periodo": "Octubre",
                }
            ],
        ),
        (
            "fechas_y_orden",
            [
                {
                    "Recurso": "Zoe",
                    "Fecha_Evaluacion": "2026-10-01",
                    "Proxima_Evaluacion": "2026-12-01",
                },
                {"Recurso": "Ána", "Fecha_Evaluacion": "2026-10-01"},
                {
                    "Recurso": "Beto",
                    "Fecha_Evaluacion": 46327,
                    "Proxima_Evaluacion": 46328,
                },
                {"Recurso": "Sin fecha", "Fecha_Evaluacion": "invalida"},
            ],
        ),
        (
            "id_exacto",
            [
                {
                    "ID_Proyecto": "AER.P.001_CR",
                    "Recurso": "Otro bloque",
                    "Score": 100,
                },
                {
                    "ID_Proyecto": " AER.P.001 ",
                    "Recurso": "Seleccionado",
                    "Score": 90,
                },
                {
                    "ID_Proyecto": "aer.p.001",
                    "Recurso": "Otra mayúscula",
                    "Score": 80,
                },
            ],
        ),
        (
            "duplicados",
            [
                {"UID": "D", "Recurso": "Ana", "Score": 80},
                {"UID": "D", "Recurso": "Ana", "Score": 90},
            ],
        ),
    ]
    result = []
    for name, items in cases:
        rows = [
            HEADERS,
            *[
                [
                    {"ID_Proyecto": "AER.P.001", **item}.get(key, "")
                    for key in HEADERS
                ]
                for item in items
            ],
        ]
        reader = SimpleNamespace(
            sheet_exists=lambda key: key == SHEET_EVALUATIONS,
            read_values=lambda key, rows=rows: rows,
        )
        store = AerStore(
            reader, SimpleNamespace(), datetime(2026, 11, 5), ensured=True
        )
        result.append(
            {
                "case": name,
                "project": "AER.P.001",
                "rows": rows,
                "expected": evaluations(store, "AER.P.001"),
            }
        )
    return result


def test_original_evaluations():
    assert original_cases() == json.loads(PATH.read_text(encoding="utf-8"))
