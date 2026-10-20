"""Ingresos por fecha revenue y costos por fecha real de las horas."""

from collections.abc import Sequence
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any

from django.utils import timezone

from apps.portal.services.executive_period import bounds, contains, current
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
    """Agrupa por mes el rango elegido o, sin rango, los meses cerrados.

    Sin periodo se muestran todos los meses cerrados del ejercicio 2026
    (de enero al mes anterior). Es lo mismo que ve quien elige el ano
    completo, porque ambos comparten el corte preparado.
    """
    today = timezone.localdate()
    end = today.year * 12 + today.month - 2
    months = [
        f"{index // 12:04d}-{index % 12 + 1:02d}"
        for index in range(2026 * 12, min(end + 1, 2027 * 12))
    ]
    first, last = bounds()
    # El ano completo elegido a mano equivale al ejercicio predeterminado y
    # comparte su corte preparado: se muestra igual (meses cerrados).
    if current() and (first, last) != (date(2026, 1, 1), date(2026, 12, 31)):
        months = [
            f"{i // 12:04d}-{i % 12 + 1:02d}"
            for i in range(
                first.year * 12 + first.month - 1, last.year * 12 + last.month
            )
        ]
    rows: dict[str, dict[str, Any]] = {
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
            rows[moment.strftime("%Y-%m")]["revenue"] += float(amount)
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
        item["revenue"] = round(item["revenue"], 2)
        item["partial"] = not complete
        if complete and item["cost"] is None:
            item["cost"] = 0
        if item["cost"] is not None:
            item["cost"] = round(item["cost"], 2)
        if item["cost"] is not None:
            item["gross_profit"] = round(item["revenue"] - item["cost"], 2)
            if item["revenue"] != 0:
                item["margin"] = round(
                    item["gross_profit"] / item["revenue"] * 100, 2
                )
    return {
        "months": list(rows.values()),
        "pending_projects": pending,
        "complete": complete,
        "band_month": today.strftime("%Y-%m"),
    }
