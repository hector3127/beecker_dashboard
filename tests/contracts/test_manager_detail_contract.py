"""Contrato original de resumen y orden del detalle de Delivery Manager."""

import json
from pathlib import Path

from apps.portal.api.plain import plain
from apps.portal.schemas import ProjectView
from apps.portal.services.manager_detail import build_manager_detail

PATH = Path(__file__).with_name("manager_detail.json")


def project(pid: str, **changes: object) -> dict[str, object]:
    """Proyecto de cartera sintético con variantes de estado y riesgo."""
    return {
        "project_id": pid,
        "name": pid,
        "client": "Ácme",
        "delivery_manager": "Ana Pérez",
        "service": "RaaS",
        "status_category": "Activo",
        "health": "A tiempo",
        "risk_level": "",
        "progress_percent": 50,
        "delay_days": 0,
        "budget_hours": 100,
        "burn_hours": 50,
        "etc_hours": 50,
        **changes,
    }


def cases() -> list[dict]:
    """Escenarios obtenidos únicamente con el motor del dashboard original."""
    inputs = [
        (
            "mixto",
            "Ana Pérez",
            [
                project("En tiempo"),
                project(
                    "Crítico consumo",
                    health="Crítica",
                    burn_hours=125.5,
                    etc_hours=-25.5,
                ),
                project("En riesgo", health="En Riesgo", delay_days=12),
                project(
                    "Suspendido", status_category="En Pausa", health="Crítica"
                ),
                project("Cerrado", status_category="Cerrado"),
            ],
        ),
        ("vacio", "", []),
        ("suspendidos", "Ana", [project("S", status_category="En Pausa")]),
        (
            "orden",
            "Ana",
            [
                project("B", health="Crítica", delay_days=5),
                project("A", health="Crítica", delay_days=5),
                project("Z", health="Crítica", delay_days=10),
                project("R", health="En Riesgo", delay_days=-2),
            ],
        ),
        (
            "riesgos",
            "Ana",
            [
                project("Uno", risk_level="Alto"),
                project("Dos", risk_level="Alto"),
                project("Tres", risk_level="Alto"),
                project(
                    "Suspendido", status_category="En Pausa", risk_level="Alto"
                ),
            ],
        ),
        (
            "redondeo",
            "Uno",
            [
                project("A", budget_hours=80, burn_hours=80.4, etc_hours=-0.5),
                project("B", etc_hours=0.5, progress_percent=None),
            ],
        ),
        (
            "sin_presupuesto",
            "Ana",
            [
                project(
                    "A",
                    health="En Riesgo",
                    budget_hours=0,
                    burn_hours=500,
                    delay_days=0,
                )
            ],
        ),
    ]
    return [
        {
            "case": key,
            "name": name,
            "projects": rows,
            "expected": plain(
                build_manager_detail(name, [ProjectView(**row) for row in rows])
            ),
        }
        for key, name, rows in inputs
    ]


def test_detalle_dm_original() -> None:
    assert cases() == json.loads(PATH.read_text(encoding="utf-8"))
