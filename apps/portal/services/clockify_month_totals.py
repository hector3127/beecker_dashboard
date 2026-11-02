"""Totales completos del mes, separados de las asignaciones de capacidad."""

from datetime import date

from django.conf import settings
from django.db import transaction
from django.db.models import Count, Q, Sum

from apps.datastore.models import ClockifyMonthSync, ClockifyTimeEntry


def clockify_month_totals(month: str):
    """No filtra por Recursos, proyecto, facturable o día de la semana."""
    if not settings.CLOCKIFY_STORE_ENABLED:
        return None
    return _stored_month_totals(month)


@transaction.atomic
def _stored_month_totals(month):
    """Una lectura consistente del corte mensual publicado."""
    first = date.fromisoformat(month + "-01")
    sync = ClockifyMonthSync.objects.filter(month=first).first()
    if sync is None:
        return {"available": False, "month": month}
    rows = ClockifyTimeEntry.objects.filter(month=first)
    totals = rows.aggregate(
        seconds=Sum("duration_seconds"),
        billable=Sum("duration_seconds", filter=Q(billable=True)),
        entries=Count("entry_id"),
        people=Count("user_id", distinct=True),
    )
    return {
        "available": True,
        "month": month,
        "consumed": round((totals["seconds"] or 0) / 3600, 2),
        "billable": round((totals["billable"] or 0) / 3600, 2),
        "entries": totals["entries"],
        "people": totals["people"],
        "synced_at": sync.synced_at.isoformat(),
    }
