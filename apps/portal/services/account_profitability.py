"""Ranking financiero por cuenta de DataRevenue, ejercicio 2026."""

from collections import defaultdict
from decimal import Decimal, InvalidOperation
from urllib.parse import urlencode

from django.core.cache import cache
from django.urls import reverse
from django.utils.text import slugify

from apps.portal.services.revenue import REVENUE_STATUSES
from apps.portal.services.revenue_costs import key
from core.sheets.factory import build_sheet_repository
from core.utils.dates import to_datetime
from core.utils.text import normalize_name


def account_profitability(reader=None):
    """Clasifica cuentas con costos disponibles y sin horas duplicadas."""
    accounts = {}
    reader = reader or build_sheet_repository()
    for row in reader.read_values("DataRevenue")[1:]:
        if len(row) < 8 or any(
            str(c).strip().casefold()
            in {"total", "subtotal", "grand total", "total general"}
            for c in row[:7]
        ):
            continue
        if str(row[0]).strip().casefold() not in REVENUE_STATUSES:
            continue
        day = to_datetime(row[6])
        name = str(row[1] or "").strip()
        if not day or day.year != 2026 or not name:
            continue
        try:
            revenue = Decimal(
                str(row[7]).replace(",", "").replace("$", "").strip()
            )
        except InvalidOperation:
            continue
        if not revenue.is_finite():
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
        account["revenue"] += revenue
        state = str(row[0]).strip().casefold()
        if state in {"collected", "collected factoring"}:
            account["collected"] += revenue
            account["invoiced"] += revenue
        elif state in {"invoiced", "invoiced factoring"}:
            account["invoiced"] += revenue
        pid = str(row[4] or "").strip()
        if pid:
            account["ids"].add(pid.casefold())
        else:
            account["pending"] += 1
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
            + urlencode({"nombre": account["name"]}),
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
            if account["pending"] or margin is None
            else "healthy"
            if margin > 70
            else "unhealthy"
            if margin < 30
            else "intermediate"
        )
        all_accounts.append(item)
        if account["pending"] or margin is None:
            pending.append(item)
        elif margin > 70:
            healthy.append(item)
        elif margin < 30:
            unhealthy.append(item)

    def order(row):
        return (-row["revenue"], row["name"])

    return {
        "healthy": sorted(
            healthy,
            key=lambda row: (-row["margin"], -row["revenue"], row["name"]),
        )[:5],
        "unhealthy": sorted(unhealthy, key=order),
        "pending_accounts": len(pending),
        "threshold": 70,
        "year": 2026,
        "accounts": sorted(all_accounts, key=order),
    }


def load_account_profitability(refresh=False):
    """Reutiliza las cuentas de la precarga financiera cuando estan vigentes."""
    from apps.portal.services.financial_cache import (
        cached_financial_snapshot,
    )

    prepared = cached_financial_snapshot().get("accounts")
    if prepared is not None and not refresh:
        return prepared
    return account_profitability()
