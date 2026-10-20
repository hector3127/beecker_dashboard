"""Ranking financiero por cuenta de DataRevenue, ejercicio 2026."""

from collections import defaultdict
from decimal import Decimal, InvalidOperation
from typing import Any
from urllib.parse import urlencode

from django.core.cache import cache
from django.urls import reverse
from django.utils.text import slugify

from apps.portal.services.executive_period import bounds, contains, query_string
from apps.portal.services.revenue import INVOICE_STATUSES
from apps.portal.services.revenue_costs import key
from core.sheets.factory import build_sheet_repository
from core.sheets.protocols import SheetReader
from core.utils.dates import to_datetime
from core.utils.text import normalize_name


def account_profitability(
    reader: SheetReader | None = None,
) -> dict[str, Any]:
    """Clasifica cuentas con costos disponibles y sin horas duplicadas."""
    accounts: dict[str, dict[str, Any]] = {}
    reader = reader or build_sheet_repository()
    for row in reader.read_values("DataRevenue")[1:]:
        if len(row) < 8 or any(
            str(c).strip().casefold()
            in {"total", "subtotal", "grand total", "total general"}
            for c in row[:7]
        ):
            continue
        if str(row[0]).strip().casefold() not in INVOICE_STATUSES:
            continue
        day = to_datetime(row[6])
        name = str(row[1] or "").strip()
        if not contains(day) or not name:
            continue
        try:
            line_revenue = Decimal(
                str(row[7]).replace(",", "").replace("$", "").strip()
            )
        except InvalidOperation:
            continue
        if not line_revenue.is_finite():
            continue
        account = accounts.setdefault(
            normalize_name(name),
            {
                "name": name,
                "revenue": Decimal(0),
                "ids": set(),
                "pending": 0,
                "entries": {},
                "collected": Decimal(0),
                "invoiced": Decimal(0),
            },
        )
        account["revenue"] += line_revenue
        state = str(row[0]).strip().casefold()
        if state in {"collected", "collected factoring"}:
            account["collected"] += line_revenue
            account["invoiced"] += line_revenue
        elif state in {"invoiced", "invoiced factoring"}:
            account["invoiced"] += line_revenue
        pid = str(row[4] or "").strip()
        if pid:
            account["ids"].add(pid.casefold())
        else:
            account["pending"] += 1
    from apps.portal.services.cost_project_inventory import inventory

    for pid, project in inventory(reader).items():
        for name in project["accounts"]:
            item = accounts.setdefault(
                normalize_name(name),
                {
                    "name": name,
                    "revenue": Decimal(0),
                    "ids": set(),
                    "pending": 0,
                    "entries": {},
                    "collected": Decimal(0),
                    "invoiced": Decimal(0),
                },
            )
            item["ids"].add(pid)
    entry_owners = defaultdict(set)
    for name, account in accounts.items():
        for pid in account["ids"]:
            result = cache.get(key(pid))
            if not result or not result["complete"]:
                account["pending"] += 1
            if result:
                for entry_id, amount in result["entries"].items():
                    account["entries"][entry_id] = amount
                    entry_owners[entry_id].add(name)
    healthy, unhealthy, pending = [], [], []
    all_accounts = []
    for account in accounts.values():
        if any(len(entry_owners[e]) > 1 for e in account["entries"]):
            account["pending"] += 1
        revenue = float(account["revenue"])
        cost = round(sum(account["entries"].values()), 2)
        profit = round(revenue - cost, 2)
        margin = round(profit / revenue * 100, 2) if revenue > 0 else None
        item = {
            "name": account["name"],
            "url": reverse(
                "portal:cuenta",
                kwargs={"slug": slugify(account["name"]) or "cuenta"},
            )
            + "?"
            + urlencode({"nombre": account["name"]})
            + ("&" + query_string() if query_string() else ""),
            "revenue": round(revenue, 2),
            "cost": cost,
            "gross_profit": profit,
            "margin": margin,
            "pending": account["pending"],
            "projects": len(account["ids"]),
            "collected": float(account["collected"]),
            "invoiced": float(account["invoiced"]),
            "collections_percent": round(
                float(account["collected"] / account["invoiced"] * 100), 2
            )
            if account["invoiced"]
            else None,
        }
        item["classification"] = (
            "pending"
            if account["pending"] or (margin is None and cost <= 0)
            else "healthy"
            if margin is not None and margin > 70
            else "unhealthy"
            if (margin is not None and margin < 30)
            or (revenue == 0 and cost > 0)
            else "intermediate"
        )
        all_accounts.append(item)
        if account["pending"] or (margin is None and cost <= 0):
            pending.append(item)
        elif margin is not None and margin > 70:
            healthy.append(item)
        elif (margin is not None and margin < 30) or (
            revenue == 0 and cost > 0
        ):
            unhealthy.append(item)

    def order(row: dict[str, Any]) -> tuple[float, str]:
        return (-row["revenue"], row["name"])

    return rank_financial_accounts(all_accounts)


def rank_financial_accounts(accounts: Any) -> dict[str, Any]:
    """Weight two normalized monetary indicators; percentages inform."""
    all_accounts = [dict(row) for row in accounts]
    eligible = all_accounts
    largest_invoice = max((row["revenue"] for row in eligible), default=0) or 1
    profit_scale = (
        max((abs(row["gross_profit"]) for row in eligible), default=0) or 1
    )
    for row in all_accounts:
        row["partial"] = bool(row.get("pending"))
        row["profit_points"] = (
            round(70 * row["gross_profit"] / profit_scale, 4)
            if row in eligible
            else None
        )
        row["invoice_points"] = (
            round(30 * row["revenue"] / largest_invoice, 4)
            if row in eligible
            else None
        )
        row["weighted_score"] = (
            round(row["profit_points"] + row["invoice_points"], 2)
            if row in eligible
            else None
        )
    ranked = sorted(
        eligible,
        key=lambda row: (
            -row["weighted_score"],
            -row["gross_profit"],
            -row["revenue"],
            row["name"],
        ),
    )
    split = (len(ranked) + 1) // 2
    return {
        "healthy": ranked[: min(5, split)],
        "unhealthy": list(reversed(ranked[split:]))[:5],
        "pending_accounts": sum(
            bool(row.get("pending")) for row in all_accounts
        ),
        "weights": {"gross_profit": 70, "invoiced": 30},
        "ranking_version": 3,
        "ranking_method": (
            "70 × utilidad / mayor utilidad absoluta"
            " + 30 × facturación / mayor facturación"
        ),
        "validation": "Base mensual pendiente de validar con Florencia",
        "year": bounds()[0].year,
        "accounts": sorted(
            all_accounts, key=lambda row: (-row["revenue"], row["name"])
        ),
    }


def load_account_profitability(refresh: bool = False) -> dict[str, Any]:
    """Reutiliza las cuentas de la precarga financiera cuando estan vigentes."""
    from apps.portal.services.financial_cache import (
        cached_financial_snapshot,
    )

    prepared: dict[str, Any] | None = cached_financial_snapshot().get(
        "accounts"
    )
    if prepared is not None and not refresh:
        return prepared
    return account_profitability()
