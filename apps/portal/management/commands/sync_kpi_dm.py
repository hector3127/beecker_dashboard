"""Explicit KPI-only capture; daily scheduling remains deferred to Genesis."""

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from apps.datastore.services.locks import sync_lock
from apps.portal.services.kpi_dm_store import closing_day
from apps.portal.services.kpi_dm_sync import (
    capture_current_month,
    close_due_periods,
)


class Command(BaseCommand):
    """Save local current-month counts independently of the EVA page."""

    help = (
        "Guarda KPIs del mes actual; --automatic queda apagado hasta Genesis."
    )

    def add_arguments(self, parser):
        """Guard future unattended executions."""
        parser.add_argument("--automatic", action="store_true")

    def handle(self, *args, **options):
        """Never call providers; write a single coherent monthly observation."""
        if options["automatic"] and not settings.KPI_DM_AUTO_UPDATE_ENABLED:
            self.stdout.write(
                "Actualización diaria KPI desactivada hasta Genesis."
            )
            return
        with sync_lock("kpi_dm", 7200) as acquired:
            if not acquired:
                self.stdout.write("Ya hay una actualización de KPIs en curso.")
                return
            if options["automatic"]:
                close_due_periods()
                if timezone.localdate() > closing_day(timezone.localdate()):
                    self.stdout.write(
                        "Periodo terminado; se conserva sin actualizar."
                    )
                    return
            try:
                observation = capture_current_month(
                    require_today=options["automatic"]
                )
            except ValueError as error:
                raise CommandError(str(error)) from error
            self.stdout.write(
                f"KPIs guardados al {observation.cut}: "
                f"{observation.metrics.count()} DMs; "
                f"periodo {observation.period.month:%Y-%m}."
            )
