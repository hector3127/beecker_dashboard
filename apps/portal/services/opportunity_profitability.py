"""Sold versus actual margin, joined by DataRevenue opportunity (column C)."""

from collections import defaultdict
from decimal import Decimal, InvalidOperation
from typing import Any

from django.core.cache import cache
from django.utils import timezone

from apps.portal.services.executive_period import bounds, contains
from apps.portal.services.revenue import INVOICE_STATUSES, REVENUE_STATUSES
from apps.portal.services.revenue_costs import cached_project_cost, key
from core.sheets.factory import build_sheet_repository
from core.utils.dates import to_datetime
from core.utils.text import normalize_name


def number(value: Any) -> Any:
    """Convierte una celda a numero; None si no es valida."""
    try:
        result = Decimal(str(value).replace(",", "").replace("$", "").strip())
        return result if result.is_finite() else None
    except (InvalidOperation, ValueError, TypeError):
        return None


def sold_percent(value: Any) -> Any:
    """Convierte un porcentaje vendido a fraccion; None si no es valido."""
    if value is None or str(value).strip() == "":
        return None
    text = str(value).strip()
    result = number(text.replace("%", ""))
    if result is None:
        return None
    return float(result if "%" in text or abs(result) > 1 else result * 100)


def excluded_service(value: Any) -> Any:
    """Indica si el servicio queda fuera del margen por oportunidad."""
    name = normalize_name(str(value or ""))
    return any(
        token in name
        for token in ("licens", "licenc", "saas", "specialized", "especializ")
    )


def build_opportunities(reader: Any = None) -> Any:
    """Arma el margen vendido y real de cada oportunidad."""
    reader = reader or build_sheet_repository()
    source = reader.read_values("DataRevenue")
    groups: dict[Any, Any] = {}
    # Ownership is checked against the entire source: a shared project must not
    # silently allocate its full cost to multiple commercial opportunities.
    owners = defaultdict(set)
    period_owners = defaultdict(set)
    for row in source[1:]:
        if (
            len(row) < 8
            or str(row[0]).strip().casefold() not in REVENUE_STATUSES
        ):
            continue
        account, opportunity, pid = (
            str(row[i] or "").strip() for i in (1, 2, 4)
        )
        moment = to_datetime(row[6])
        amount = number(row[7])
        if (
            opportunity
            and pid
            and amount
            and contains(moment)
            and not excluded_service(row[3])
        ):
            owner = (normalize_name(account), normalize_name(opportunity))
            period_owners[pid.casefold()].add(owner)
            if moment and moment.date() <= timezone.localdate():
                owners[pid.casefold()].add(owner)
    for pid, candidates in period_owners.items():
        if not owners[pid]:
            owners[pid] = candidates
    for row in source[1:]:
        if (
            len(row) < 8
            or str(row[0]).strip().casefold() not in REVENUE_STATUSES
        ):
            continue
        if excluded_service(row[3]) or not contains(to_datetime(row[6])):
            continue
        if any(
            str(c).strip().casefold()
            in {"total", "subtotal", "grand total", "total general"}
            for c in row[:7]
        ):
            continue
        amount = number(row[7])
        if amount is None:
            continue
        account, name, pid = (str(row[i] or "").strip() for i in (1, 2, 4))
        identity: tuple[Any, ...] = (
            normalize_name(account),
            normalize_name(name),
        )
        # Rows without an opportunity remain visible for correction, never
        # merged.
        if not name:
            identity = (*identity, len(groups))
        item = groups.setdefault(
            identity,
            {
                "account": account,
                "name": name or "Sin oportunidad",
                "ids": set(),
                "services": set(),
                "revenue": Decimal(0),
                "invoiced": Decimal(0),
                "confirmed": Decimal(0),
                "collected": Decimal(0),
                "margins": set(),
                "missing_margin": 0,
                "project_revenue": defaultdict(Decimal),
                "issues": [],
                "projects": [],
            },
        )
        item["revenue"] += amount
        state = str(row[0]).strip().casefold()
        if state in INVOICE_STATUSES:
            item["invoiced"] += amount
        else:
            item["confirmed"] += amount
        if state in {"collected", "collected factoring"}:
            item["collected"] += amount
        if pid:
            item["ids"].add(pid)
            item["project_revenue"][pid] += amount
        else:
            item["issues"].append("Fila sin Project ID")
        item["services"].add(str(row[3]))
        margin = sold_percent(row[8] if len(row) > 8 else None)
        if margin is None:
            item["missing_margin"] += 1
        else:
            item["margins"].add(margin)
    result = []
    for identity, item in groups.items():
        entries = {}
        partial = False
        for pid in sorted(item["ids"], key=str.casefold):
            project_issues = []
            shared = len(owners[pid.casefold()]) > 1 or bool(
                owners[pid.casefold()]
                and identity not in owners[pid.casefold()]
            )
            saved = cached_project_cost(pid)
            if shared:
                project_issues.append(
                    "Referencia parcial: costo total del ID compartido; "
                    "no es exclusivo de esta oportunidad ni debe sumarse "
                    "entre oportunidades"
                )
            if not saved:
                project_issues.append(
                    "Costo pendiente: "
                    + str(
                        cache.get(key(pid) + ":error") or "sin corte disponible"
                    )
                )
            elif not saved.get("complete"):
                project_issues.append(
                    "Costo parcial: faltan bandas, tarifas o registros"
                )
            if saved:
                entries.update(saved.get("entries", {}))
            partial = partial or bool(project_issues)
            project_revenue = float(item["project_revenue"][pid])
            project_cost = saved.get("cost") if saved else None
            project_profit = (
                round(project_revenue - project_cost, 2)
                if project_cost is not None
                else None
            )
            project_margin = (
                round(project_profit / project_revenue * 100, 2)
                if project_profit is not None and project_revenue
                else None
            )
            item["projects"].append(
                {
                    "id": pid,
                    "hours": saved.get("hours") if saved else None,
                    "revenue": round(project_revenue, 2),
                    "gross_profit": project_profit,
                    "margin": project_margin,
                    "partial": bool(project_issues),
                    "shared": shared,
                    "cost": saved.get("cost") if saved else None,
                    "issues": project_issues,
                    "included_ids": saved.get("included_ids", [])
                    if saved
                    else [],
                }
            )
        item["issues"] = sorted(set(item["issues"]))
        partial = partial or bool(item["issues"])
        if item["missing_margin"]:
            item["issues"].append("Margen vendido faltante en columna I")
        conflict = len(item["margins"]) > 1
        if conflict:
            item["issues"].append(
                "Columna I contiene márgenes distintos para la misma "
                "oportunidad; validar fuente"
            )
        sold = (
            next(iter(item["margins"]))
            if len(item["margins"]) == 1 and not item["missing_margin"]
            else None
        )
        cost = (
            round(sum(entries.values()), 2)
            if entries
            or all(not p["issues"] for p in item["projects"])
            and item["projects"]
            else None
        )
        revenue = float(item["revenue"])
        actual = (
            round((revenue - cost) / revenue * 100, 2)
            if revenue and cost is not None
            else None
        )
        result.append(
            {
                "account": item["account"],
                "name": item["name"],
                "revenue": round(revenue, 2),
                "invoiced": round(float(item["invoiced"]), 2),
                "confirmed": round(float(item["confirmed"]), 2),
                "collected": round(float(item["collected"]), 2),
                "cost": cost,
                "allocation_pending": any(
                    p.get("shared") for p in item["projects"]
                ),
                "available_project_cost": round(
                    sum(p["cost"] or 0 for p in item["projects"]), 2
                ),
                "sold_margin": sold,
                "actual_margin": actual,
                "deviation_pp": round(actual - sold, 2)
                if actual is not None and sold is not None
                else None,
                "partial": partial,
                "projects": item["projects"],
                "issues": item["issues"],
                "services": sorted(item["services"]),
                "ids": sorted(item["ids"]),
            }
        )
    return {
        "opportunities": sorted(
            result,
            key=lambda r: (r["account"].casefold(), r["name"].casefold()),
        ),
        "start": bounds()[0].isoformat(),
        "end": bounds()[1].isoformat(),
        "version": 5,
        "excluded": "Licencias, SaaS y servicios especializados",
    }


def opportunity_summary(rows: Any) -> Any:
    """Arithmetic means of known margins; compare deviation on matched pairs."""
    total = len(rows)
    complete = sum(not r["partial"] and r["cost"] is not None for r in rows)
    sold = [r["sold_margin"] for r in rows if r["sold_margin"] is not None]
    actual = [
        r["actual_margin"]
        for r in rows
        if r["actual_margin"] is not None and not r.get("allocation_pending")
    ]
    deviations = [
        r["deviation_pp"]
        for r in rows
        if r["deviation_pp"] is not None and not r.get("allocation_pending")
    ]

    def mean(values: list[float]) -> float | None:
        return round(sum(values) / len(values), 2) if values else None

    return {
        "total": total,
        "complete": complete,
        "pending": total - complete,
        "complete_pct": round(complete / total * 100, 1) if total else 0,
        "pending_pct": round((total - complete) / total * 100, 1)
        if total
        else 0,
        "sold": mean(sold),
        "sold_count": len(sold),
        "actual": mean(actual),
        "actual_count": len(actual),
        "deviation": mean(deviations),
        "deviation_count": len(deviations),
    }
