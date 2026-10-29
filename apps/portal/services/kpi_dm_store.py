"""KPI page reads only its own saved daily observations and monthly periods."""

import calendar
from dataclasses import dataclass, replace
from datetime import date, timedelta

from django.utils import timezone

from apps.datastore.models import DmKpiObservation, DmKpiPeriod
from apps.portal.schemas import (
    HealthCount,
    KpiCut,
    KpiHistory,
    KpiManagerRow,
    KpiView,
    TimeCost,
)
from apps.portal.services.kpi_eva import eva_manager_view, select_managers
from apps.portal.services.kpi_history import _managers
from apps.portal.services.kpi_history_loader import KpiHistoryLoad
from apps.portal.services.periods import MONTH_ABBREVIATIONS


def closing_day(month: date) -> date:
    """Independent KPI closing day: last Monday–Thursday of its month."""
    end = month.replace(day=calendar.monthrange(month.year, month.month)[1])
    while end.weekday() > 3:
        end -= timedelta(days=1)
    return end


def observation_view(observation: DmKpiObservation | None) -> KpiView:
    """Derive T/C from saved counts, never from providers or EVA projections."""
    empty = eva_manager_view([])
    if observation is None:
        return empty
    rows = tuple(
        KpiManagerRow(
            item.manager,
            item.slug,
            item.total,
            HealthCount(item.on_time, item.late, 0),
            round(100 * item.on_time / item.total) if item.total else 0,
            TimeCost(
                time_days=100 * item.on_time / item.total
                if item.total
                else None,
                cost_percent=100 * item.over_budget / item.total
                if item.total
                else None,
            ),
            time_late=item.late,
            cost_over=item.over_budget,
        )
        for item in observation.metrics.all()
    )
    if not rows:
        return empty
    return select_managers(
        replace(empty, rows=rows), [row.name for row in rows]
    )


@dataclass(frozen=True)
class StoredKpiCut:
    """Exact saved date, or an explicit missing observation."""

    view: KpiView
    observation: DmKpiObservation | None


def latest_kpi_cut() -> date | None:
    """Default to the latest available date without inventing today's data."""
    return (
        DmKpiObservation.objects.filter(cut__lte=timezone.localdate())
        .order_by("-cut")
        .values_list("cut", flat=True)
        .first()
    )


def monthly_kpi_cut(month: date) -> date:
    """Resolve the month's saved pointer, leaving missing months explicit."""
    cut = DmKpiPeriod.objects.filter(month=month).values_list(
        "latest_observation__cut", flat=True
    ).first()
    return cut or closing_day(month)


def load_kpi_cut(cut: date) -> StoredKpiCut:
    """Read an exact daily observation; do not substitute another date."""
    observation = (
        DmKpiObservation.objects.select_related("period")
        .prefetch_related("metrics")
        .filter(cut=cut)
        .first()
    )
    return StoredKpiCut(observation_view(observation), observation)


def load_kpi_history(year: int | None = None) -> KpiHistoryLoad:
    """Twelve saved monthly pointers; missing history stays pending."""
    today = timezone.localdate()
    chosen = year or today.year
    periods = {
        p.month.month: p
        for p in DmKpiPeriod.objects.filter(
            month__gte=date(chosen, 1, 1),
            month__lt=date(chosen + 1, 1, 1),
        )
        .select_related("latest_observation")
        .prefetch_related("latest_observation__metrics")
    }
    months = []
    missing = []
    pending = []
    for number in range(1, 13):
        period = periods.get(number)
        observation = period.latest_observation if period else None
        future = date(chosen, number, 1) > today.replace(day=1)
        if future or observation and observation.cut > today:
            observation = None
        if observation is None and not future:
            missing.append(f"{chosen}-{number:02d}")
        if period and period.status == "pending":
            pending.append(f"{chosen}-{number:02d}")
        cut = (
            observation.cut
            if observation
            else closing_day(date(chosen, number, 1))
        )
        months.append(
            KpiCut(
                f"{chosen}-{number:02d}",
                MONTH_ABBREVIATIONS[number - 1].capitalize(),
                cut.strftime("%d/%m/%Y"),
                observation_view(observation),
                bool(observation and period and period.status != "closed"),
                observation is not None,
            )
        )
    notice = ""
    if missing:
        notice = (
            "Meses sin datos KPI guardados, pendientes de carga: "
            + ", ".join(missing)
            + "."
        )
    if pending:
        notice += (
            " Falta captura del día de cierre en: " + ", ".join(pending) + "."
        )
    history = KpiHistory(tuple(months), (), _managers(months))
    return KpiHistoryLoad(history, notice=notice)
