"""Inversion operativa y comercial de un Delivery Manager."""

from collections.abc import Mapping
from typing import Any

"""BKD.120.027 - Inversion por Delivery Manager
Suma las horas de inversion de los proyectos de una persona a partir del
total por proyecto que ya esta calculado. Un dato faltante o incompleto
no se reporta como cero.
"""


def manager_investment(manager: Any, investment: Any) -> dict[str, Any]:
    """Horas de inversion operativa y comercial de un Delivery Manager."""
    investment = investment if isinstance(investment, Mapping) else {}
    project_ids = getattr(manager, "project_ids", ())
    if "population" in investment and getattr(manager, "name", None):
        from apps.portal.services.operational_sources import norm

        project_ids = tuple(
            p["project_id"]
            for p in investment["population"]
            if norm(p.get("manager")) == norm(manager.name)
        )
    by_project = investment.get("by_project", {})
    covered = [by_project[pid] for pid in project_ids if pid in by_project]
    ready = bool(
        investment.get("complete")
        and project_ids
        and len(covered) == len(set(project_ids))
    )
    return {
        "operational": sum(row.get("operational", 0) for row in covered)
        if ready
        else None,
        "commercial": sum(row.get("commercial", 0) for row in covered)
        if ready
        else None,
        "ready": ready,
    }
