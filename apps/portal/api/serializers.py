"""Contrato JSON de cada pantalla, con campos explicitos."""

from datetime import date, datetime
from typing import Any

from django.conf import settings

from apps.portal.services.manager_investment import manager_investment
from apps.portal.services.operativa_status import block_error

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


# ---------- Operativa ----------


def _health(health: Any) -> dict[str, int]:
    return {
        "on_time": health.on_time,
        "at_risk": health.at_risk,
        "critical": health.critical,
    }


def _eva_card(card: Any) -> dict[str, Any]:
    """Tarjeta EVA 1 o 3: proyectos, desviacion en dias y avance en horas."""
    cost = card.time_cost
    return {
        "available": bool(card.available),
        "total_projects": card.total_projects,
        "time_days": cost.time_days,
        "cost_percent": cost.cost_percent,
    }


def _manager(manager: Any, investment: Any) -> dict[str, Any]:
    ready = manager_investment(manager, investment)
    return {
        "name": manager.name,
        "slug": manager.slug,
        "initials": manager.initials,
        "in_progress": manager.in_progress,
        "paused": manager.paused,
        "health": _health(manager.health),
        "shares": {
            "on_time": manager.on_time_width,
            "at_risk": manager.at_risk_width,
            "critical": manager.critical_width,
        },
        "investment": {
            "ready": ready["ready"],
            "operational": ready["operational"],
            "commercial": ready["commercial"],
        },
    }


def _investment(investment: Any) -> dict[str, Any]:
    """Totales de inversion; el detalle por proyecto no sale de aqui."""
    data = investment if isinstance(investment, dict) else {}
    complete = bool(data.get("complete"))
    totals = data.get("totals") or {}
    return {
        "complete": complete,
        "loading": bool(data.get("loading")),
        "error": data.get("error") or "",
        "operational": totals.get("operational") if complete else None,
        "commercial": totals.get("commercial") if complete else None,
    }


_CAPACITY_FIELDS = (
    "month",
    "registered_people",
    "available",
    "estimated",
    "consumed",
    "billable",
    "base",
    "days",
    "over",
    "pending",
)


def _capacity(capacity: Any) -> dict[str, Any]:
    data = capacity if isinstance(capacity, dict) else {}
    return {
        "loading": bool(data.get("loading")),
        "error": data.get("error") or "",
        **{name: data.get(name) for name in _CAPACITY_FIELDS},
    }


def _eva4_card(report: Any) -> dict[str, Any]:
    data = report if isinstance(report, dict) else {}
    available = bool(data.get("available"))
    return {
        "available": available,
        "active": data.get("active") if available else None,
        "suspended": data.get("suspended") if available else None,
        "renewal_count": data.get("renewal_count") if available else None,
    }


def operativa_screen(
    context: dict[str, Any], *, unrestricted: bool, snapshot: bool = False
) -> dict[str, Any]:
    """Operativa: indicadores, salud, Delivery Managers, EVA y capacidad.

    Con un alcance limitado no salen las cifras que son del equipo completo
    (tarjetas EVA 1 y 3, capacidad): no se pueden recortar por cuenta.
    """
    summary = context["summary"]
    investment = context.get("investment")
    donut = context["donut"]
    data = {
        "filters": {
            "service": context.get("selected_service", ""),
            "client": context.get("selected_client", ""),
        },
        "options": {
            "services": list(context.get("services", ())),
            "clients": list(context.get("clients", ())),
        },
        "loaded_at": _stamp(context.get("loaded_at")),
        "loading": bool(context.get("loading")),
        "consumption_pending": bool(context.get("consumption_pending")),
        "portfolio_unavailable": bool(context.get("portfolio_unavailable")),
        "stale": bool(context.get("stale")),
        "error": context.get("error") or "",
        "source_errors": list(context.get("source_errors", ())),
        "block_error": block_error(context),
        "has_projects": bool(context.get("has_projects")),
        "summary": {
            "in_progress": summary.in_progress,
            "paused": summary.paused,
            "on_time_percent": summary.on_time_percent,
            "health": _health(summary.health),
        },
        "health_states": [
            {
                "state": state,
                "label": segment.label,
                "count": segment.count,
                "percent": segment.percent,
            }
            for state, segment in zip(
                ("on_time", "at_risk", "critical"), donut, strict=True
            )
        ],
        "managers": [
            _manager(manager, investment)
            for manager in context.get("managers", ())
        ],
        "investment": _investment(investment),
        "eva": {
            "eva1": _eva_card(context["eva1_card"]) if unrestricted else None,
            "eva3": _eva_card(context["eva3_card"]) if unrestricted else None,
            "eva4": _eva4_card(context.get("eva4")),
        },
        "capacity": _capacity(context.get("capacity_live"))
        if unrestricted
        else None,
        "restricted": not unrestricted,
    }
    if snapshot:
        pending = context.get("pending_blocks") or ""
        data["pending_blocks"] = [b for b in pending.split(",") if b]
        data["async"] = bool(context.get("async_operativa"))
        data["billing_fresh"] = bool(context.get("summary_fresh"))
        # El ultimo corte de facturabilidad se pinta de inmediato; la
        # actualizacion decide aparte si ya caduco.
        saved = context.get("operations_summary")
        data["billing"] = (
            billing_screen(saved)["data"] if saved and unrestricted else None
        )
    return {"data": data, "meta": {}}


def billing_screen(summary: Any) -> dict[str, Any]:
    """Facturabilidad global por mes: el mes destacado y las barras."""
    selected = summary.selected
    return {
        "data": {
            "target": summary.target,
            "month": selected.month if selected else None,
            "month_label": summary.month_label,
            "month_closed": summary.month_closed,
            "partial": bool(summary.errors),
            "errors": list(summary.errors),
            "gap": summary.gap,
            "selected": {
                "global_percent": selected.global_percent,
                "fixed_percent": selected.fixed_percent,
                "variable_percent": selected.variable_percent,
            }
            if selected
            else None,
            "months": [
                {
                    "month": bar.month,
                    "label": bar.label,
                    "month_label": bar.month_label,
                    "global_percent": bar.global_percent,
                    "fixed_percent": bar.fixed_percent,
                    "variable_percent": bar.variable_percent,
                }
                for bar in summary.bars
            ],
        },
        "meta": {},
    }


# La tarifa de costo vendida no se calcula ni se sustituye por la de banda
# hasta que Finanzas confirme fuente, unidad y asignacion.
SOLD_COST_RATE = {"value": None, "status": "pending_validation"}


def _margin_project(project: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": project["id"],
        "hours": project["hours"],
        "cost": project["cost"],
        "period_revenue": project["revenue"],
        "gross_profit": project["gross_profit"],
        "margin": project["margin"],
        "partial": project["partial"],
        "shared": project["shared"],
        "issues": project["issues"],
    }


def _opportunity(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "account": row["account"],
        "name": row["name"],
        "services": row["services"],
        "ids": row["ids"],
        "bookings": row["bookings"],
        "period_revenue": row["revenue"],
        "operated_revenue": row["operated_revenue"],
        "operated_revenue_status": row["operated_revenue_status"],
        "invoiced": row["invoiced"],
        "collected": row["collected"],
        "cost": row["cost"],
        "sold_cost_rate": SOLD_COST_RATE,
        "sold_margin": row["sold_margin"],
        "actual_margin": row["actual_margin"],
        "deviation_pp": row["deviation_pp"],
        "partial": row["partial"],
        "allocation_pending": row["allocation_pending"],
        "issues": row["issues"],
        "projects": [_margin_project(p) for p in row["projects"]],
    }


def margins_screen(result: dict[str, Any], account: str) -> dict[str, Any]:
    """Comparativa de margenes vendido y real por oportunidad."""
    return {
        "data": {
            "opportunities": [_opportunity(o) for o in result["opportunities"]],
            "summary": result["summary"],
        },
        "meta": {
            "account": account or None,
            "start": result["start"],
            "end": result["end"],
            "excluded": result["excluded"],
            "preparing": result["preparing"],
        },
    }


def _account_project(project: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": project["id"],
        "name": project.get("nombre"),
        "service": project.get("servicio"),
        "stage": project.get("etapa"),
        "state": project.get("estado"),
        "manager": project.get("deliveryManager"),
        "budget": project.get("budget"),
        "burn": project.get("burn"),
        "nps": project.get("nps"),
        "clockify_pending": bool(project.get("clockifyPending")),
        "exceeded": bool(project.get("excedido")),
        "late": bool(project.get("atrasado")),
    }


def account_screen(result: dict[str, Any], client: str) -> dict[str, Any]:
    """Cuenta: indicadores de origen, proyectos, procesos ROC y backlog."""
    if not result.get("ok"):
        return {
            "data": {
                "available": False,
                "error": result.get("error") or "No se pudo leer la cuenta.",
            },
            "meta": {"client": client},
        }
    return {
        "data": {
            "available": True,
            "error": "",
            "warning": result.get("warning") or "",
            "stale": bool(result.get("stale")),
            "nps": result.get("nps"),
            "nps_sample": result.get("npsMuestra", 0),
            "roc_active": result.get("rocActivos", 0),
            "consumption_pending": result.get("mpbPendientes", 0),
            "projects": [_account_project(p) for p in result["proyectos"]],
            "roc": [
                {
                    "process": r.get("proceso"),
                    "id": r.get("id") or r.get("botId"),
                    "service": r.get("servicio"),
                    "bot_id": r.get("botId"),
                    "state": r.get("estado"),
                }
                for r in result.get("roc", [])
            ],
            "opportunities": [
                {
                    "account": o.get("account"),
                    "name": o.get("name"),
                    "manager": o.get("manager"),
                    "stage": o.get("stage"),
                    "close": o.get("close"),
                    "hours": o.get("hours"),
                }
                for o in result.get("oportunidades", [])
            ],
        },
        "meta": {"client": client, "cutoff": result.get("fechaCorte")},
    }


def account_consumption(result: dict[str, Any]) -> dict[str, Any]:
    """Un lote de horas: [{id, burn, error}] y desde donde sigue."""
    return {
        "data": {
            "ok": bool(result.get("ok")),
            "items": [
                {
                    "id": i.get("id"),
                    "burn": i.get("burn"),
                    "error": i.get("error") or "",
                }
                for i in result.get("items", [])
            ],
            "next": result.get("next"),
            "total": result.get("total"),
        },
        "meta": {},
    }


def account_finance(account: dict[str, Any] | None) -> dict[str, Any]:
    """Facturacion, margen y cobranza de la cuenta; null sin registros."""
    keys = (
        "revenue",
        "margin",
        "cost",
        "pending",
        "projects",
        "collected",
        "invoiced",
        "collections_percent",
    )
    data = {key: account.get(key) for key in keys} if account else None
    return {"data": {"account": data}, "meta": {"year": 2026}}
