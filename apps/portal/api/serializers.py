"""Contrato JSON de cada pantalla, con campos explicitos."""

from datetime import date, datetime
from typing import Any

from django.conf import settings

"""BKD.120.015 - Contratos de pantalla
Cada funcion arma {"data": ..., "meta": ...} para una pantalla. Los
numeros salen como numeros y las fechas como ISO; dar formato es trabajo
del frontend. Un campo vacio es null, no una cadena vacia.
"""


def _blank(value: Any) -> Any:
    return None if value in (None, "") else value


def _day(value: date | None) -> str | None:
    return value.isoformat() if value else None


def _stamp(value: datetime | None) -> str | None:
    return value.isoformat() if value else None


def _process(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "manager": row["manager"],
        "country": row["country"],
        "client": row["client"],
        "bot": row.get("bot_label") or row["bot_id"],
        "service": row["service"],
        "process": row["process"],
        "status": row["status"],
        "status_code": row["status_code"],
        "start": _day(row["start"]),
        "finish": _day(row["finish"]),
        "average_limit": _blank(row["average_limit"]),
        "invested_hours": _blank(row["invested_hours"]),
        "hours_balance": _blank(row["hours_balance"]),
        "package_limit": _blank(row["package_limit"]),
        "package_available": _blank(row["package_available"]),
        "risk": _blank(row["risk"]),
    }


def _renewal(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "manager": row["manager"],
        "account_manager": row["account_manager"],
        "project_id": row["project_id"],
        "country": row["country"],
        "finish": _day(row["finish"]),
        "due": row["due"],
        "urgency": row["urgency"],
    }


def eva4_screen(report: dict[str, Any]) -> dict[str, Any]:
    """Resumen de EVA-04: procesos, renovaciones y clientes de un mes."""
    available = bool(report.get("available"))
    hours_origin = report.get("hours_origin", "")
    return {
        "data": {
            "available": available,
            "error": report.get("error") or "",
            "month": report.get("month"),
            "loaded_at": _stamp(report.get("loaded_at")),
            "summary": {
                "active": report.get("active", 0),
                "suspended": report.get("suspended", 0),
                "total": report.get("total", 0),
                "renewal_count": report.get("renewal_count", 0),
            },
            "processes": [
                _process(row) for row in report.get("active_processes", [])
            ],
            "renewals": [_renewal(row) for row in report.get("renewals", [])],
            "clients": {
                "services": report.get("services", []),
                "service_totals": report.get("service_totals", []),
                "rows": [
                    {
                        "name": row["name"],
                        "counts": row["counts"],
                        "total": row["total"],
                        "suspended": row["suspended"],
                        "active": row["active"],
                    }
                    for row in report.get("clients", [])
                ],
            },
            "notes": {
                "missing_columns": report.get("missing_columns", []),
                "unmatched_tasks": report.get("unmatched_tasks", 0),
                "missing_limits": report.get("missing_limits", 0),
                "hours_origin": hours_origin,
                "hours_source": report.get("hours_source", ""),
            },
        },
        "meta": {
            "sources": [
                {
                    "name": "ROC",
                    "origin": "database"
                    if settings.SHEETS_STORE_ENABLED
                    else "sheets",
                },
                {
                    "name": "Clockify",
                    "origin": hours_origin,
                    "detail": report.get("hours_source", ""),
                },
            ],
        },
    }
