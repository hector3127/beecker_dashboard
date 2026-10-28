"""Counts reconciled to the visible inventory rows, without provider reads."""

from collections import Counter
from typing import Any

SERVICES = ("IXB", "PoC", "RaaS", "RaaS+", "SaaS")
STATUSES = ("Sus", "Dis", "Dev", "Dep")
STATUS_NAMES = {
    "Suspended": "Sus",
    "Suspendido": "Sus",
    "Discovery": "Dis",
    "Development": "Dev",
    "Deployment": "Dep",
}


def dm_totals(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Count each displayed project/sprint/CR once in each dimension."""
    groups: dict[str, tuple[Counter[str], Counter[str]]] = {}
    services = list(SERVICES)
    statuses = list(STATUSES)
    for row in rows:
        fields = row.get("fields") or {}
        manager = fields.get("delivery_manager") or "Sin DM confirmado"
        service = str(fields.get("service") or "Pendiente").strip()
        service = next(
            (s for s in SERVICES if s.casefold() == service.casefold()), service
        )
        status = STATUS_NAMES.get(row.get("calendar_stage", ""), "Pendiente")
        if service not in services:
            services.append(service)
        if status not in statuses:
            statuses.append(status)
        svc, state = groups.setdefault(manager, (Counter(), Counter()))
        svc[service] += 1
        state[status] += 1
    result: list[dict[str, Any]] = []
    for manager, (svc, state) in sorted(
        groups.items(), key=lambda item: item[0].casefold()
    ):
        result.append(
            {
                "manager": manager,
                "services": [svc[s] for s in services],
                "statuses": [state[s] for s in statuses],
                "total": sum(svc.values()),
            }
        )
    return {
        "services": services,
        "statuses": statuses,
        "rows": result,
        "service_totals": [
            sum(r["services"][i] for r in result) for i in range(len(services))
        ],
        "status_totals": [
            sum(r["statuses"][i] for r in result) for i in range(len(statuses))
        ],
        "total": len(rows),
        "colspan": len(services) + len(statuses) + 3,
    }
