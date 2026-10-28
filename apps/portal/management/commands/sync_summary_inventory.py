"""Extract all accessible Azure Summary descriptions into local storage."""

from django.core.management.base import BaseCommand

from apps.datastore.services.locks import sync_lock
from apps.portal.services.summary_inventory import extract_summaries


class Command(BaseCommand):
    """Run the isolated Summary inventory extraction."""

    help = "Guarda todos los Summary y sus bloques, incluidos cerrados."

    def add_arguments(self, parser):
        """Allow local evidence replay without contacting providers."""
        parser.add_argument("--from-local", action="store_true")

    def handle(self, *args, **options):
        """Coordinate a single extraction across processes."""
        with sync_lock("summary_inventory", 7200) as acquired:
            if not acquired:
                self.stdout.write("Ya hay una extracción de Summary en curso.")
                return
            run = extract_summaries(from_local=options["from_local"])
            self.stdout.write(str(run.metrics))
