"""Compara horas registradas AER directamente en Clockify."""

from django.db.models import Sum

from apps.datastore.models import ClockifyTimeEntry
from apps.datastore.services.stored_base import is_synced


def aer_registered_comparison():
    """Usa la unión de proyectos con prefijo AER. de ambos meses."""
    months = ("2026-09", "2026-10")
    aer_entries = ClockifyTimeEntry.objects.filter(
        month__in=[f"{month}-01" for month in months],
        project_name__istartswith="AER.",
        duration_seconds__gt=0,
        entry_date__isnull=False,
    )
    projects = aer_entries.values("project_id").distinct()
    totals = (
        aer_entries.filter(billable=True)
        .values("month")
        .annotate(seconds=Sum("duration_seconds"))
    )
    hours = {
        row["month"].isoformat()[:7]: row["seconds"] / 3600 for row in totals
    }
    return {
        "projects": projects.count(),
        "hours": [
            hours.get(month, 0.0) if is_synced(month) else None
            for month in months
        ],
    }
