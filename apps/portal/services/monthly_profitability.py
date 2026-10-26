"""Ingresos por fecha revenue y costos por fecha real de las horas."""

from collections.abc import Sequence
from decimal import Decimal, InvalidOperation
from typing import Any

from django.utils import timezone

from apps.portal.services.executive_period import bounds, contains
from apps.portal.services.revenue import INVOICE_STATUSES
from apps.portal.services.revenue_costs import (
    cached_project_cost,
    project_ids,
)
from core.sheets.factory import build_sheet_repository
from core.sheets.protocols import SheetReader
from core.utils.dates import to_datetime


def load_monthly_profitability(
    reader: SheetReader | None = None, ids: Sequence[str] | None = None
) -> dict[str, Any]:
    """Agrupa todos los meses del rango elegido, incluido el ano completo."""
    today = timezone.localdate()
    first, last = bounds()
    months = [
        f"{i // 12:04d}-{i % 12 + 1:02d}"
        for i in range(
            first.year * 12 + first.month - 1, last.year * 12 + last.month
        )
    ]
    rows: dict[str, dict[str, Any]] = {
        month: {
            "month": month,
            "revenue": None if month > today.strftime("%Y-%m") else 0.0,
            "future": month > today.strftime("%Y-%m"),
            "cost": None,
            "margin": None,
            "gross_profit": None,
            "partial": True,
        }
        for month in months
    }
    reader = reader or build_sheet_repository()
    for row in reader.read_values("DataRevenue")[1:]:
        if not row or str(row[0]).strip().casefold() not in INVOICE_STATUSES:
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
            item = rows[moment.strftime("%Y-%m")]
            item["revenue"] = (item["revenue"] or 0.0) + float(amount)
    complete = True
    pending = 0
    seen: set[str] = set()
    for pid in project_ids(reader) if ids is None else ids:
        project = cached_project_cost(pid)
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
    for item in rows.values():
        if item["revenue"] is not None:
            item["revenue"] = round(item["revenue"], 2)
        item["partial"] = not complete
        if complete and item["cost"] is None and not item["future"]:
            item["cost"] = 0
        if item["cost"] is not None:
            item["cost"] = round(item["cost"], 2)
        if item["cost"] is not None and item["revenue"] is not None:
            item["gross_profit"] = round(item["revenue"] - item["cost"], 2)
            if item["revenue"] != 0:
                item["margin"] = round(
                    item["gross_profit"] / item["revenue"] * 100, 2
                )
    return {
        "months": list(rows.values()),
        "calendar_version": 2,
        "pending_projects": pending,
        "complete": complete,
        "band_month": today.strftime("%Y-%m"),
    }
