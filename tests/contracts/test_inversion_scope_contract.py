"""Alcance original de inversión completa por servicio y cuenta."""

import copy
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from apps.portal.views import _scope_operativa_investment

BASE = {
    "complete": True,
    "projects": 2,
    "population": [
        {
            "project_id": "P1",
            "manager": "Ana",
            "client": "Acme",
            "service": "RaaS",
        },
        {
            "project_id": "P2",
            "manager": "Beto",
            "client": "Beta",
            "service": "AER",
        },
    ],
    "by_project": {
        "P1": {"operational": 2, "commercial": 1},
        "P2": {"operational": 3, "commercial": 4},
    },
    "records": [
        {"project": "P1", "category": "operational", "hours": 2},
        {"project": "P1", "category": "commercial", "hours": 1},
        {"project": "P2", "category": "operational", "hours": 3},
        {"project": "P2", "category": "commercial", "hours": 4},
    ],
    "totals": {"operational": 5, "commercial": 5},
}
PATH = Path(__file__).with_name("inversion_scope.json")


def cases() -> list[dict]:
    """Ejecuta las ramas de alcance de la implementación original."""
    result = []
    for service, client, complete in [
        ("", "", True),
        ("RaaS", "", True),
        ("AER", "Beta", True),
        ("RaaS", "Beta", True),
        ("RaaS", "", False),
    ]:
        source = {**copy.deepcopy(BASE), "complete": complete}
        context = {"investment": copy.deepcopy(source)}
        scope = SimpleNamespace(
            unrestricted=True,
            filter_projects=lambda projects, *args: list(projects),
        )
        with patch("apps.portal.views.scope_for", return_value=scope):
            _scope_operativa_investment(
                SimpleNamespace(GET={"servicio": service, "cuenta": client}),
                context,
            )
        result.append(
            {
                "investment": source,
                "service": service,
                "client": client,
                "expected": context["investment"],
            }
        )
    return result


def test_alcance_original() -> None:
    assert cases() == json.loads(PATH.read_text(encoding="utf-8"))
