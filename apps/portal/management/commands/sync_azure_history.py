"""Download retained Azure revisions for every PAT-visible project."""

from django.core.management.base import BaseCommand

from apps.datastore.services.locks import sync_lock
from apps.portal.services.azure_history import download_history


class Command(BaseCommand):
    """Download a resumable organization revision stream."""

    help = "Descarga el histórico Azure para reconstruir cortes locales."

    def handle(self, *args, **options):
        """Keep one writer and report batch progress and final duration."""
        with sync_lock("azure_history", 7200) as acquired:
            if not acquired:
                self.stdout.write("Ya hay una descarga histórica en curso.")
                return
            self.stdout.write(str(download_history(self.stdout.write)))
