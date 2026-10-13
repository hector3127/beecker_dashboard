"""Constructores de ProjectView para las pruebas del portal."""

from apps.portal.schemas import ProjectView


def make_project(**overrides):
    values = {
        "project_id": "P-1",
        "name": "Alpha",
        "client": "ACME",
        "delivery_manager": "Laura Vega",
        "service": "AER",
        "status_category": "Activo",
        "health": "A tiempo",
        "risk_level": "",
        "progress_percent": 50,
        "delay_days": 0,
        "budget_hours": 100.0,
        "burn_hours": 40.0,
        "etc_hours": 60.0,
    }
    values.update(overrides)

    return ProjectView(**values)
