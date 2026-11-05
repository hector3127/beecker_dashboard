"""Distribución mensual ejecutada sobre manager_monthly_history original."""

import json
from datetime import date
from pathlib import Path
from types import SimpleNamespace

from apps.portal.services import operational_sources

PATH = Path(__file__).with_name("dm_monthly_budget.json")
INPUTS = [
    (
        "cruce_anual",
        "2026-01-15",
        [
            {
                "project_id": "P1",
                "name": "Cerrado",
                "start": "2025-08-10",
                "end": "2025-09-05",
                "budget": 270,
            },
            {
                "project_id": "P2",
                "name": "Vigente",
                "start": "2025-12-01",
                "end": "2026-02-28",
                "budget": 900,
            },
        ],
    ),
    (
        "bisiesto",
        "2024-02-29",
        [
            {
                "project_id": "P1",
                "name": "Febrero",
                "start": "01/02/24",
                "end": "29/02/24",
                "budget": 290,
            },
        ],
    ),
    (
        "sin_presupuesto",
        "2026-11-05",
        [
            {
                "project_id": f"P{n}",
                "name": f"Proyecto {n}",
                "start": "2026-10-01",
                "end": "2026-11-30",
                "budget": hours,
            }
            for n, hours in enumerate([None, 0, -30])
        ],
    ),
    (
        "fechas_invalidas",
        "2026-11-05",
        [
            {
                "project_id": "P1",
                "name": "Invertido",
                "start": "2026-11-30",
                "end": "2026-10-01",
                "budget": 60,
            },
            {
                "project_id": "P2",
                "name": "Sin fecha",
                "start": "",
                "end": "",
                "budget": 60,
            },
        ],
    ),
    (
        "un_dia",
        "2026-11-05",
        [
            {
                "project_id": "P1",
                "name": "Entrega",
                "start": "05/11/2026",
                "end": "05/11/2026",
                "budget": 2.675,
            },
        ],
    ),
    (
        "fuera_periodo",
        "2026-11-05",
        [
            {
                "project_id": "P1",
                "name": "Anterior",
                "start": "2025-01-01",
                "end": "2025-12-31",
                "budget": 365,
            },
            {
                "project_id": "P2",
                "name": "Futuro",
                "start": "2026-12-01",
                "end": "2026-12-31",
                "budget": 31,
            },
        ],
    ),
    ("sin_proyectos", "2026-11-05", []),
]


def original_cases(monkeypatch):
    """Presupuesto original sin proveedores ni caché compartida."""
    result = []
    reader = SimpleNamespace(
        read_as_objects=lambda *a: [],
        sheet_exists=lambda *a: False,
        read_values=lambda *a: [],
    )
    monkeypatch.setattr(
        operational_sources, "build_sheet_repository", lambda: reader
    )
    monkeypatch.setattr(operational_sources.cache, "get", lambda *a: None)
    monkeypatch.setattr(operational_sources.cache, "set", lambda *a: None)
    for key, today_text, projects in INPUTS:
        today = date.fromisoformat(today_text)
        index = today.year * 12 + today.month - 6
        buckets = []
        for offset in range(6):
            yy, mm = divmod(index + offset, 12)
            buckets.append(
                {
                    "label": f"{yy}-{mm + 1:02d}",
                    "projects": [],
                    "billable": 0,
                    "operational": 0,
                    "commercial": 0,
                }
            )
        monkeypatch.setattr(
            operational_sources.timezone, "localdate", lambda today=today: today
        )
        monkeypatch.setattr(
            operational_sources,
            "tagged_investment",
            lambda *a, buckets=buckets, **kw: {
                "complete": True,
                "monthly": buckets,
            },
        )
        original = operational_sources.manager_monthly_history(
            "Ana", [SimpleNamespace(**p) for p in projects]
        )
        result.append(
            {
                "case": key,
                "today": today_text,
                "projects": projects,
                "expected": original["monthly"],
            }
        )
    return result


def test_original_monthly_budgets(monkeypatch):
    assert original_cases(monkeypatch) == json.loads(
        PATH.read_text(encoding="utf-8")
    )
