"""Contratos sintéticos de cartera Operativa obtenidos del motor original."""

import json
import os
from datetime import date
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from unittest.mock import patch

import pytest

from apps.portal.api.plain import plain
from apps.portal.services.filters import (
    filter_projects,
    list_clients,
    list_services,
)
from apps.portal.services.operational_sources import eva_projects
from apps.portal.services.portfolio_summary import (
    service_distribution,
    summarize_delivery_managers,
    summarize_portfolio,
)

PATH = Path(__file__).with_name("cartera_operativa.json")
TODAY = date(2026, 11, 4)


def project(pid: str, **changes: object) -> dict[str, Any]:
    """Fila EVA mínima con variantes de calendario y consumo."""
    return {
        "project_id": pid,
        "name": pid,
        "manager": "Álvaro Pérez",
        "client": "Acme",
        "service": "RaaS",
        "status_code": "dev",
        "end": "31/12/26",
        "progress": 50,
        "budget": 100,
        "burn": 50,
        "etc": 50,
        **changes,
    }


def cases() -> list[dict[str, Any]]:
    """Escenarios independientes de bases, usuarios y proveedores."""
    population = [
        project("A_S1"),
        project("A_CR1", burn=101, progress=101),
        project(
            "B", manager="Beatriz", service="AER", client="Beta", end="03/11/26"
        ),
        project(
            "C", manager="Beatriz", service="AER", end="2026-12-04", burn=90
        ),
        project(
            "D", manager="Sin Delivery Manager", status_code="sus", burn=150
        ),
        project("E", manager="", end="sin fecha", renewal_days=None),
        project(
            "F",
            manager="Álvaro Pérez",
            service="",
            client="",
            end="2026-12-05",
            burn=100,
        ),
        project(
            "G",
            manager="Beto",
            service="IXB",
            budget=0,
            burn=300,
            end="04/11/2026",
        ),
        project("H", manager="Beatriz", end="sin fecha", renewal_days=31),
        project("I", manager="Beatriz", end="2026-12-04", burn=89.99),
        project(
            "J",
            manager="Beatriz",
            end="2026-11-05",
            burn=None,
            progress=None,
            etc=None,
        ),
        project("K", manager="Sin Delivery Manager", end="2026-12-31"),
        project(
            "L",
            manager="Beatriz",
            service="SaaS",
            end="2026-11-05",
            budget=-1,
            burn=20,
        ),
    ]
    return [
        {"name": "mixto", "projects": population, "service": "", "client": ""},
        {"name": "vacio", "projects": [], "service": "", "client": ""},
        {
            "name": "servicio",
            "projects": population,
            "service": "AER",
            "client": "",
        },
        {
            "name": "cuenta",
            "projects": population,
            "service": "",
            "client": "Acme",
        },
        {
            "name": "interseccion",
            "projects": population,
            "service": "AER",
            "client": "Beta",
        },
        {
            "name": "sin_coincidencias",
            "projects": population,
            "service": "raas",
            "client": "Acme",
        },
        {
            "name": "solo_suspendidos",
            "projects": [project("S", status_code="sus")],
            "service": "",
            "client": "",
        },
        {
            "name": "redondeo_mitad",
            "projects": [
                project(str(n), burn=101 if n else 1) for n in range(8)
            ],
            "service": "",
            "client": "",
        },
    ]


@pytest.mark.parametrize("case", cases(), ids=lambda case: case["name"])
def test_cartera_original(case: dict[str, Any]) -> None:
    ixb = SimpleNamespace(
        view=SimpleNamespace(
            projects=[SimpleNamespace(**row) for row in case["projects"]]
        )
    )
    aer = SimpleNamespace(view=SimpleNamespace(projects=[]))
    with patch(
        "apps.portal.services.operational_sources.timezone.localdate",
        return_value=TODAY,
    ):
        population = eva_projects(ixb, aer)
    selected = filter_projects(population, case["service"], case["client"])
    result = plain(
        {
            "projects": selected,
            "summary": summarize_portfolio(selected),
            "managers": summarize_delivery_managers(selected),
            "service_distribution": service_distribution(selected),
            "services": list_services(population),
            "clients": list_clients(population),
            "portfolio_total": len(selected),
        }
    )
    if os.environ.get("UPDATE_CARTERA_CONTRACT") == "1":
        saved = (
            json.loads(PATH.read_text(encoding="utf-8"))
            if PATH.exists()
            else {}
        )
        saved[case["name"]] = {
            "input": {**case, "today": TODAY.isoformat()},
            "expected": result,
        }
        PATH.write_text(
            json.dumps(saved, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    assert (
        result
        == json.loads(PATH.read_text(encoding="utf-8"))[case["name"]][
            "expected"
        ]
    )
