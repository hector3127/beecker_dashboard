"""Project revenue and gross margin for the same scope as costs."""

from collections import defaultdict
from decimal import Decimal, InvalidOperation
from typing import Any

from django.utils import timezone

from apps.portal.services.executive_period import contains
from apps.portal.services.revenue import REVENUE_STATUSES
from core.utils.dates import to_datetime
from core.utils.text import normalize_name


def add_project_revenue(result: Any, reader: Any, account: Any = None) -> Any:
    """Enrich cost results with revenue and margin for the selected period."""
    projects = result.get("projects", [result])
    wanted = {str(p["id"]).strip().casefold() for p in projects}
    totals: dict[str, Decimal] = {}
    dates = defaultdict(list)
    for row in reader.read_values("DataRevenue")[1:]:
        if (
            len(row) < 8
            or str(row[0]).strip().casefold() not in REVENUE_STATUSES
        ):
            continue
        pid = str(row[4] or "").strip().casefold()
        if pid not in wanted or not contains(to_datetime(row[6])):
            continue
        if account and normalize_name(str(row[1] or "")) != normalize_name(
            account
        ):
            continue
        try:
            amount = Decimal(
                str(row[7]).replace(",", "").replace("$", "").strip()
            )
        except InvalidOperation:
            continue
        if amount.is_finite():
            totals[pid] = totals.get(pid, Decimal(0)) + amount
            moment = to_datetime(row[6])
            if moment is not None:
                dates[pid].append(moment.date())

    def enrich(project: Any) -> Any:
        item = dict(project)
        revenue = totals.get(str(item["id"]).strip().casefold())
        income = float(revenue) if revenue is not None else 0.0
        item["no_revenue"] = revenue is None or income == 0
        cost = item.get("cost")
        project_dates = dates.get(str(item["id"]).strip().casefold(), [])
        today = timezone.localdate()
        if (
            not item.get("hours")
            and project_dates
            and all(
                (d.year, d.month) > (today.year, today.month)
                for d in project_dates
            )
        ):
            item.update({"future": True, "status": "future", "error": None})
        item["revenue"] = round(income, 2) if income is not None else None
        item["gross_profit"] = (
            round(income - cost, 2)
            if income is not None and cost is not None
            else None
        )
        item["margin"] = (
            round((income - cost) / income * 100, 2)
            if income is not None and income > 0 and cost is not None
            else None
        )
        item["margin_provisional"] = cost is not None and not item.get(
            "complete", False
        )
        return item

    if "projects" in result:
        enriched = [enrich(p) for p in projects]
        future_count = sum(bool(p.get("future")) for p in enriched)
        pending = sum(
            p.get("cost") is None and not p.get("future") for p in enriched
        )
        return {
            **result,
            "projects": enriched,
            "future": future_count,
            "pending": pending,
            "consulted": len(enriched) - pending - future_count,
        }
    return enrich(result)
