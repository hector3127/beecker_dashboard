"""Project revenue and gross margin for the same scope as costs."""

from decimal import Decimal, InvalidOperation
from typing import Any

from apps.portal.services.executive_period import contains
from apps.portal.services.revenue import REVENUE_STATUSES
from core.sheets.protocols import SheetReader
from core.utils.dates import to_datetime
from core.utils.text import normalize_name


def add_project_revenue(
    result: dict[str, Any], reader: SheetReader, account: str | None = None
) -> dict[str, Any]:
    """Enrich cost results with revenue and margin for the selected period."""
    projects = result.get("projects", [result])
    wanted = {str(p["id"]).strip().casefold() for p in projects}
    totals: dict[str, Decimal] = {}
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

    def enrich(project: dict[str, Any]) -> dict[str, Any]:
        item = dict(project)
        revenue = totals.get(str(item["id"]).strip().casefold())
        income = float(revenue) if revenue is not None else 0.0
        item["no_revenue"] = revenue is None or income == 0
        cost = item.get("cost")
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
        return {**result, "projects": [enrich(p) for p in projects]}
    return enrich(result)
