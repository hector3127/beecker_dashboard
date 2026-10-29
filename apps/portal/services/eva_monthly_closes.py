"""Immutable monthly EVA observations; never backfill from newer Azure dates."""

import calendar
from copy import deepcopy
from datetime import date, timedelta
from typing import Any

from django.db import transaction
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from apps.datastore.models import (
    EvaExtraction,
    EvaMonthlyClose,
    EvaMonthlyClosePolicy,
)


def closing_day(month: date) -> date:
    """Last Monday–Thursday of the month, as agreed for EVA/DM KPIs."""
    cut = month.replace(day=calendar.monthrange(month.year, month.month)[1])
    while cut.weekday() > 3:
        cut -= timedelta(days=1)
    return cut


def is_closed_period(cut: date) -> bool:
    """Only a closing day whose local calendar day has finished is fixed."""
    return cut == closing_day(cut) and cut < timezone.localdate()


def read_monthly_close(
    cut: date,
) -> tuple[EvaExtraction | None, list[dict[str, Any]]] | None:
    """None means live date; (None, []) means a missing, already due close."""
    if not is_closed_period(cut):
        return None
    close = (
        EvaMonthlyClose.objects.select_related("extraction")
        .filter(cut=cut)
        .first()
    )
    return (close.extraction, deepcopy(close.rows)) if close else (None, [])


def close_due_months() -> dict[str, list[str]]:
    """Under inventory lock, seal the last successful source observation."""
    from apps.portal.services.summary_inventory import inventory_rows

    policy = EvaMonthlyClosePolicy.objects.filter(pk=1).first()
    result: dict[str, list[str]] = {"closed": [], "pending": []}
    if policy is None:
        return result
    today = timezone.localdate()
    month = policy.first_month.replace(day=1)
    while month <= today.replace(day=1):
        cut = closing_day(month)
        if (
            cut < today
            and not EvaMonthlyClose.objects.filter(month=month).exists()
        ):
            candidates = EvaExtraction.objects.filter(
                published=True,
                finished_at__isnull=False,
                cut=cut,
                metrics__kind="summary_inventory",
                metrics__eva_enriched=True,
            ).order_by("-finished_at", "-pk")
            chosen, observed = None, None
            for candidate in candidates:
                try:
                    stamp = parse_datetime(
                        candidate.metrics.get("source_observed_at", "")
                    )
                except (TypeError, ValueError):
                    continue
                if (
                    stamp
                    and timezone.is_aware(stamp)
                    and timezone.localdate(stamp) == cut
                ):
                    chosen, observed = candidate, stamp
                    break
            if chosen is None:
                result["pending"].append(cut.isoformat())
            else:
                assert observed is not None
                _, rows = inventory_rows(
                    cut=cut, source_run=chosen, use_closes=False
                )
                with transaction.atomic():
                    _, created = EvaMonthlyClose.objects.get_or_create(
                        month=month,
                        defaults={
                            "cut": cut,
                            "extraction": chosen,
                            "source_observed_at": observed,
                            "rows": rows,
                            "source_issues": chosen.issues,
                        },
                    )
                if created:
                    result["closed"].append(cut.isoformat())
        month = (month.replace(day=28) + timedelta(days=4)).replace(day=1)
    return result
