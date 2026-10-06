"""Comando que escanea la carpeta de minutas de Drive."""

from typing import Any

from django.core.management.base import BaseCommand

from apps.minutas.scanner_factory import run_minutes_scan

"""BKD.060.010 - Comando scan_minutes
Sustituye al activador de tiempo de escanearMinutasNuevas(). Se programa
con el Programador de tareas igual que warm_cache.
"""


class Command(BaseCommand):
    """Procesa las minutas de Google Meet creadas hoy."""

    help = "Escanea la carpeta de minutas de Drive y procesa las de hoy."

    def handle(self, *args: Any, **options: Any) -> None:
        """Ejecuta el escaneo e informa cuantas minutas se procesaron."""
        processed = run_minutes_scan()
        self.stdout.write(f"{processed} minutas nuevas procesadas")
