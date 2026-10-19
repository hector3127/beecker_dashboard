"""Render cached investment hours without querying external sources."""

import json
from collections.abc import Mapping
from typing import Any

from django import template

register = template.Library()


@register.inclusion_tag("portal/_manager_investment.html")
def manager_investment(manager: Any, investment: Any) -> dict[str, Any]:
    """Horas de inversion operativa y comercial de un Delivery Manager."""
    investment = investment if isinstance(investment, Mapping) else {}
    project_ids = getattr(manager, "project_ids", ())
    by_project = investment.get("by_project", {})
    covered = [by_project[pid] for pid in project_ids if pid in by_project]
    ready = bool(investment.get("complete") and covered)
    return {
        "project_ids": json.dumps(project_ids),
        "operational": sum(row.get("operational", 0) for row in covered)
        if ready
        else None,
        "commercial": sum(row.get("commercial", 0) for row in covered)
        if ready
        else None,
        "ready": ready,
    }


@register.simple_tag
def investment_payload(investment: Any) -> dict[str, Any]:
    """Send only the totals needed for updates, not monthly chart data."""
    investment = investment if isinstance(investment, Mapping) else {}
    return {
        "complete": bool(investment.get("complete")),
        "by_project": investment.get("by_project", {}),
    }
