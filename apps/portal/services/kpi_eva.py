"""Monthly DM compliance: EVA 1 open inventory, last Monday–Thursday cut."""

import calendar
from collections.abc import Callable, Sequence
from dataclasses import replace
from datetime import date, datetime, timedelta
from typing import Any

from apps.portal.constants import NO_DELIVERY_MANAGER
from apps.portal.schemas import (
    HealthCount,
    KpiCut,
    KpiHistory,
    KpiManagerRow,
    KpiView,
    TimeCost,
)
from apps.portal.services.kpi_history import _managers
from apps.portal.services.periods import MONTH_ABBREVIATIONS
from apps.portal.services.slugs import build_slug


def monthly_cuts(year: int, today: date) -> list[tuple[str, date, bool]]:
    """Friday/Saturday/Sunday roll back to Thursday; no future cuts.

    Current month is provisional through its latest available Mon–Thu.
    No holidays are excluded: the rule is specifically weekday based.
    """
    if year > today.year:
        return []
    result = []
    for month in range(1, (today.month if year == today.year else 12) + 1):
        end = date(year, month, calendar.monthrange(year, month)[1])
        cut = min(end, today)
        while cut.weekday() > 3:
            cut -= timedelta(days=1)
        if cut.month == month:
            result.append((f"{year}-{month:02d}", cut, today < end))
    return result


def compliance_view(rows: Sequence[dict[str, Any]]) -> KpiView:
    """T = count(deviation <= 0)/TP; C = count(advance <= 100)/TP.

    Unknown values keep TP, but leave the affected percentage pending:
    never shrink the denominator or count unknown projects as compliant.
    Time/cost failure counts are independent, not a RAID classification.
    """

    def aggregate(
        name: str, projects: Sequence[dict[str, Any]]
    ) -> KpiManagerRow:
        total = len(projects)
        known_t = [r for r in projects if r.get("desviacionDias") is not None]
        known_c = [
            r
            for r in projects
            if not r.get("budget_pending")
            and not r.get("hours_pending")
            and float(r.get("budget") or 0) > 0
        ]
        good_t = sum(r["desviacionDias"] <= 0 for r in known_t)
        good_c = sum(r["avance"] <= 100 for r in known_c)
        t = 100 * good_t / total if total and len(known_t) == total else None
        c = 100 * good_c / total if total and len(known_c) == total else None
        return KpiManagerRow(
            name,
            build_slug(name) if name != "Total" else "",
            total,
            HealthCount(good_t, len(known_t) - good_t, 0),
            round(t) if t is not None else 0,
            TimeCost(time_days=t, cost_percent=c),
            time_late=len(known_t) - good_t,
            cost_over=len(known_c) - good_c,
        )

    managers = sorted(
        {str(r.get("deliveryManager") or NO_DELIVERY_MANAGER) for r in rows}
    )
    grouped = tuple(
        aggregate(
            name,
            [
                r
                for r in rows
                if str(r.get("deliveryManager") or NO_DELIVERY_MANAGER) == name
            ],
        )
        for name in managers
    )
    ranked = sorted(
        (
            r
            for r in grouped
            if r.name not in {NO_DELIVERY_MANAGER, "Sin asignar"}
            and r.time_cost.time_days is not None
        ),
        key=lambda r: (-(r.time_cost.time_days or 0), -r.total, r.name),
    )
    return KpiView(
        grouped,
        aggregate("Total", rows),
        ranked[0] if ranked else None,
        ranked[-1] if len(ranked) > 1 else None,
    )


def build_eva_history(
    year: int,
    now: datetime,
    resolve: Callable[[date], Sequence[dict[str, Any]]],
) -> KpiHistory:
    """Use the same exact-ID cut selection as EVA 1 for each monthly cell."""
    months = tuple(
        KpiCut(
            key,
            MONTH_ABBREVIATIONS[int(key[5:7]) - 1].capitalize(),
            cut.strftime("%d/%m/%Y"),
            compliance_view(resolve(cut)),
            partial,
        )
        for key, cut, partial in monthly_cuts(year, now.date())
    )
    quarters = tuple(
        replace(
            cut,
            key=f"{year}-T{(int(cut.key[5:7]) - 1) // 3 + 1}",
            label=f"T{(int(cut.key[5:7]) - 1) // 3 + 1}",
        )
        for cut in months
        if int(cut.key[5:7]) % 3 == 0 or cut is months[-1]
    )
    return KpiHistory(months, quarters, _managers(months))
