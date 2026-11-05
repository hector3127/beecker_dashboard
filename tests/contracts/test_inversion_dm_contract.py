"""Contrato original de inversión por DM, incluidos ceros y cobertura."""

import json
from pathlib import Path
from types import SimpleNamespace

from apps.portal.services.manager_investment import manager_investment

CASES = [
    {
        "name": "completo",
        "manager": {"name": "Ana", "project_ids": ["P1", "P2"]},
        "investment": {
            "complete": True,
            "by_project": {
                "P1": {"operational": 2.5, "commercial": 1},
                "P2": {"operational": 0, "commercial": 3},
            },
        },
    },
    {
        "name": "cero",
        "manager": {"name": "Ana", "project_ids": ["P1"]},
        "investment": {
            "complete": True,
            "by_project": {"P1": {"operational": 0, "commercial": 0}},
        },
    },
    {
        "name": "incompleto",
        "manager": {"name": "Ana", "project_ids": ["P1"]},
        "investment": {
            "complete": False,
            "by_project": {"P1": {"operational": 5}},
        },
    },
    {
        "name": "cobertura_ausente",
        "manager": {"name": "Ana", "project_ids": ["P1", "P2"]},
        "investment": {
            "complete": True,
            "by_project": {"P1": {"commercial": 5}},
        },
    },
    {
        "name": "sin_proyectos",
        "manager": {"name": "Ana", "project_ids": []},
        "investment": {"complete": True, "by_project": {}},
    },
    {
        "name": "nulo",
        "manager": {"name": "Ana", "project_ids": ["P1"]},
        "investment": None,
    },
    {
        "name": "poblacion_normalizada",
        "manager": {"name": " Ána Pérez ", "project_ids": ["Incorrecto"]},
        "investment": {
            "complete": True,
            "population": [
                {"project_id": "P1", "manager": "ana perez"},
                {"project_id": "P2", "manager": "Ana Pérez"},
                {"project_id": "P3", "manager": "Beto"},
            ],
            "by_project": {
                "P1": {"operational": 2},
                "P2": {"commercial": 3},
                "P3": {"commercial": 99},
            },
        },
    },
    {
        "name": "poblacion_duplicada",
        "manager": {"name": "Ana", "project_ids": ["P1"]},
        "investment": {
            "complete": True,
            "population": [
                {"project_id": "P1", "manager": "Ana"},
                {"project_id": "P1", "manager": "Ana"},
            ],
            "by_project": {"P1": {"operational": 5}},
        },
    },
    {
        "name": "sin_nombre",
        "manager": {"name": "", "project_ids": ["P1"]},
        "investment": {
            "complete": True,
            "population": [{"project_id": "P2", "manager": ""}],
            "by_project": {"P1": {"commercial": 5}},
        },
    },
]
PATH = Path(__file__).with_name("inversion_dm.json")


def original_cases() -> list[dict]:
    """Obtiene expectativas nuevas ejecutando el servicio original."""
    return [
        {
            **case,
            "expected": manager_investment(
                SimpleNamespace(**case["manager"]), case["investment"]
            ),
        }
        for case in CASES
    ]


def test_inversion_por_dm_original() -> None:
    assert original_cases() == json.loads(PATH.read_text(encoding="utf-8"))
