"""Reuse prepared costs and account-scoped revenue in the audit table."""

from typing import Any

from django.core.cache import cache

from apps.portal.services.revenue_costs import key
from core.utils.text import normalize_name


def metadata_key(account: str | None) -> str:
    """Separate metadata by account, selected period and cost version."""
    return "portal:cost-audit:revenue:v1:" + key(
        "audit:" + normalize_name(account or "")
    )


def remember(result: dict[str, Any], account: str | None = None) -> None:
    """Store only revenue for project membership validated by the audit."""
    rows = result.get("projects", [result])
    values = cache.get(metadata_key(account)) or {}
    for row in rows:
        values[row["id"].casefold()] = row.get("revenue", 0)
    cache.set(metadata_key(account), values, 86400)


def prepared_detail(
    pid: str, account: str | None = None
) -> dict[str, Any] | None:
    """Read a prepared detail only within the previously verified account."""
    values = cache.get(metadata_key(account))
    if not isinstance(values, dict) or pid.casefold() not in values:
        return None
    cost = cache.get(key(pid))
    if (
        not cost
        or "sprints" not in cost
        or any("people" not in g for g in cost["sprints"])
    ):
        return None
    result = {
        k: v for k, v in cost.items() if k not in {"entries", "entry_months"}
    }
    revenue = values[pid.casefold()]
    revenue = 0 if revenue is None else revenue
    result.update(
        {
            "revenue": revenue,
            "no_revenue": revenue == 0,
            "gross_profit": round(revenue - cost["cost"], 2),
            "margin": round((revenue - cost["cost"]) / revenue * 100, 2)
            if revenue > 0
            else None,
            "margin_provisional": not cost["complete"],
        }
    )
    return result


def summary_key(account: str | None = None) -> str:
    """Identify a short-lived audit summary for one account and period."""
    return metadata_key(account) + ":summary"


def prepared_summary(account: str | None = None) -> Any:
    """Read the prepared audit without rebuilding source inventories."""
    return cache.get(summary_key(account))


def remember_summary(
    result: dict[str, Any], account: str | None = None
) -> dict[str, Any]:
    """Bundle available details with the audit for local expansion."""
    remember(result, account)
    result = dict(result)
    result["prepared_details"] = {
        row["id"].casefold(): detail
        for row in result.get("projects", [])
        if (detail := prepared_detail(row["id"], account)) is not None
    }
    cache.set(summary_key(account), result, 300)
    return result
