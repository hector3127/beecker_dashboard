"""Ingresos por fecha revenue y costos por fecha real de las horas."""

from decimal import Decimal, InvalidOperation

from django.core.cache import cache
from django.utils import timezone

from apps.portal.services.executive_period import bounds, contains, current
from apps.portal.services.revenue import REVENUE_STATUSES
from apps.portal.services.revenue_costs import key, project_ids
from core.sheets.factory import build_sheet_repository
from core.utils.dates import to_datetime


def load_monthly_profitability(reader=None, ids=None):
    """Agrupa los ultimos seis meses cerrados, marcando costos parciales."""
    today = timezone.localdate()
    end = today.year * 12 + today.month - 2
    months = [
        f"{index // 12:04d}-{index % 12 + 1:02d}"
        for index in range(max(end - 5, 2026 * 12), min(end + 1, 2027 * 12))
    ]
    if current():
        first, last = bounds()
        months = [
            f"{i // 12:04d}-{i % 12 + 1:02d}"
            for i in range(
                first.year * 12 + first.month - 1, last.year * 12 + last.month
            )
        ]
    rows = {
        month: {
            "month": month,
            "revenue": 0.0,
            "cost": None,
            "margin": None,
            "gross_profit": None,
            "partial": True,
        }
        for month in months
    }
    reader = reader or build_sheet_repository()
    for row in reader.read_values("DataRevenue")[1:]:
        if not row or str(row[0]).strip().casefold() not in REVENUE_STATUSES:
            continue
        if len(row) < 8 or any(
            str(c).strip().casefold()
            in {"total", "grand total", "subtotal", "total general"}
            for c in row[:7]
        ):
            continue
        moment = to_datetime(row[6])
        if (
            not moment
            or not contains(moment)
            or moment.strftime("%Y-%m") not in rows
        ):
            continue
        try:
            amount = Decimal(
                str(row[7]).replace(",", "").replace("$", "").strip()
            )
        except InvalidOperation:
            continue
        if amount.is_finite():
            rows[moment.strftime("%Y-%m")]["revenue"] += float(amount)
    complete = True
    pending = 0
    seen = set()
    for pid in project_ids(reader) if ids is None else ids:
        project = cache.get(key(pid))
        if not project:
            complete = False
            pending += 1
            continue
        complete = complete and project["complete"]
        for entry_id, amount in project["entries"].items():
            if entry_id in seen:
                continue
            seen.add(entry_id)
            month = project.get("entry_months", {}).get(entry_id)
            if not month:
                complete = False
            if month in rows:
                rows[month]["cost"] = (rows[month]["cost"] or 0) + amount
    for row in rows.values():
        row["revenue"] = round(row["revenue"], 2)
        row["partial"] = not complete
        if complete and row["cost"] is None:
            row["cost"] = 0
        if row["cost"] is not None:
            row["cost"] = round(row["cost"], 2)
        if row["cost"] is not None:
            row["gross_profit"] = round(row["revenue"] - row["cost"], 2)
            if row["revenue"] != 0:
                row["margin"] = round(
                    row["gross_profit"] / row["revenue"] * 100, 2
                )
    return {
        "months": list(rows.values()),
        "pending_projects": pending,
        "complete": complete,
        "band_month": today.strftime("%Y-%m"),
    }
