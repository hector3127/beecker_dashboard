"""Reuse detail costs plus the account-scoped revenue already loaded by the table."""

from django.core.cache import cache
from apps.portal.services.revenue_costs import key, cached_project_cost
from core.utils.text import normalize_name


def metadata_key(account):
    return "portal:cost-audit:revenue:v4:" + key(
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
    cost = cached_project_cost(pid)
    if (
        not cost
        or cost.get("financial_grouping_version") != 3
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
    saved = cache.get(summary_key(account))
    if not saved:
        return None
    return _coherent_summary(saved, account)


def _coherent_summary(saved, account):
    """Rows, counters and total always come from the same deduplicated cut."""
    result = dict(saved)
    cuts = dict(saved.get("_project_cuts", {}))
    rows, entries, details = [], {}, {}
    pending = future = consulted = 0
    complete = True
    for original in saved.get("projects", []):
        row = dict(original)
        if row.get("future"):
            future += 1
            rows.append(row)
            continue
        cost = cached_project_cost(row["id"]) or cuts.get(row["id"].casefold())
        if cost:
            cuts[row["id"].casefold()] = cost
            consulted += 1
            entries.update(cost.get("entries", {}))
            complete = complete and bool(cost.get("complete"))
            row.update(
                {
                    "cost": cost.get("cost"),
                    "hours": cost.get("hours"),
                    "complete": bool(cost.get("complete")),
                    "error": None,
                    "missing_hours": cost.get("missing_hours", 0),
                }
            )
            revenue = row.get("revenue")
            if revenue is not None and cost.get("cost") is not None:
                row["gross_profit"] = round(revenue - cost["cost"], 2)
                row["margin"] = (
                    round(row["gross_profit"] / revenue * 100, 2)
                    if revenue > 0
                    else None
                )
                row["margin_provisional"] = not cost.get("complete")
            detail = {
                k: v
                for k, v in cost.items()
                if k not in {"entries", "entry_months"}
            }
            detail.update(
                {
                    k: row[k]
                    for k in [
                        "revenue",
                        "gross_profit",
                        "margin",
                        "margin_provisional",
                    ]
                    if k in row
                }
            )
            details[row["id"].casefold()] = detail
        else:
            pending += 1
            complete = False
            row.update(
                {
                    "cost": None,
                    "hours": None,
                    "complete": False,
                    "gross_profit": None,
                    "margin": None,
                }
            )
        rows.append(row)
    result.update(
        {
            "projects": rows,
            "prepared_details": details,
            "pending": pending,
            "future": future,
            "consulted": consulted,
            "cost": round(sum(entries.values()), 2),
            "deduplicated_entries": len(entries),
            "complete": complete and not pending,
        }
    )
    cache.set(summary_key(account), {**result, "_project_cuts": cuts}, 86400)
    result.pop("_project_cuts", None)
    return result


def remember_summary(result, account=None):
    remember(result, account)
    return _coherent_summary(result, account)
