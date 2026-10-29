"""Close due months, or capture the source on the agreed closing day."""

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from apps.datastore.services.locks import sync_lock
from apps.portal.services.eva_monthly_closes import (
    close_due_months,
    closing_day,
)


class Command(BaseCommand):
    """Capture closing-day evidence or seal due local observations."""

    help = "Congela cierres EVA; --capture actualiza solo el día de cierre."

    def add_arguments(self, parser):
        """Expose guarded end-of-day capture."""
        parser.add_argument("--capture", action="store_true")

    def handle(self, *args, **options):
        """Use the same lock as inventory extraction."""
        if not settings.EVA_MONTHLY_CLOSES_ENABLED:
            self.stdout.write("Cierres mensuales desactivados hasta Genesis.")
            return
        if options["capture"]:
            today = timezone.localdate()
            if today != closing_day(today):
                self.stdout.write(
                    "Hoy no es día de cierre; sin peticiones externas."
                )
                return
            call_command(
                "sync_summary_inventory", stdout=self.stdout, stderr=self.stderr
            )
            call_command(
                "sync_azure_history", stdout=self.stdout, stderr=self.stderr
            )
            return
        with sync_lock("summary_inventory", 7200) as acquired:
            if not acquired:
                self.stdout.write(
                    "Extracción en curso; se reintentará el cierre."
                )
                return
            result = close_due_months()
            self.stdout.write(str(result))
            if result["pending"]:
                raise CommandError(
                    "Sin observación válida para cierres: "
                    + ", ".join(result["pending"])
                )
