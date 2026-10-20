"""Reuse detail costs plus the account-scoped revenue already loaded by the table."""

from django.core.cache import cache
from apps.portal.services.revenue_costs import key
from core.utils.text import normalize_name


def metadata_key(account):
    return "portal:cost-audit:revenue:v1:" + key(
        "audit:" + normalize_name(account or "")
    )


def remember(result, account=None):
    rows = result.get("projects", [result])
    values = cache.get(metadata_key(account)) or {}
    for row in rows:
        values[row["id"].casefold()] = row.get("revenue", 0)
    cache.set(metadata_key(account), values, 86400)


def prepared_detail(pid, account=None):
    # Account membership was verified by the table query; never reuse another account's metadata.
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


def summary_key(account=None):
    return metadata_key(account) + ":summary"


def prepared_summary(account=None):
    return cache.get(summary_key(account))


def remember_summary(result, account=None):
    remember(result, account)
    result = dict(result)
    result["prepared_details"] = {
        row["id"].casefold(): detail
        for row in result.get("projects", [])
        if (detail := prepared_detail(row["id"], account)) is not None
    }
    cache.set(summary_key(account), result, 300)
    return result
