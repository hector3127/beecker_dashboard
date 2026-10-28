"""Comando que revisa que la base diaria este al dia."""

from datetime import datetime, timedelta
from typing import Any

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError, CommandParser
from django.db.models import Max, Min
from django.utils import timezone

from apps.datastore.models import (
    AzurePanelSnapshot,
    AzureProject,
    ClockifyCatalog,
    ClockifyMonthSync,
    SheetSnapshot,
    SyncLock,
)
from core.sheets.store_read_cache import SHEET_IDS_NAME

"""BKD.130.014 - Frescura de la base diaria
Para monitorear las tareas programadas: muestra cuando se sincronizo cada
fuente por ultima vez y termina con error si alguna pasa de su limite, de
modo que el programador (o una alerta) se entere de que se quedo atras.
Uso: python manage.py check_datastore [--hojas-horas 3] [--azure-horas 3]
     [--clockify-horas 30]
"""


class Command(BaseCommand):
    """Revisa la antiguedad de lo guardado en la base."""

    help = "Revisa que hojas, Azure y Clockify se hayan sincronizado a tiempo."

    def add_arguments(self, parser: CommandParser) -> None:
        """Agrega los limites en horas de cada fuente."""
        parser.add_argument("--hojas-horas", type=float, default=3)
        parser.add_argument("--azure-horas", type=float, default=3)
        parser.add_argument("--clockify-horas", type=float, default=30)
        parser.add_argument(
            "--lecturas",
            action="store_true",
            help="Revisa también catálogos Clockify y paneles Azure.",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        """Muestra la antiguedad de cada fuente; falla si alguna vencio."""
        now = timezone.now()
        sheets = SheetSnapshot.objects.exclude(name=SHEET_IDS_NAME).aggregate(
            oldest=Min("synced_at"), newest=Max("synced_at")
        )
        azure = AzureProject.objects.aggregate(
            oldest=Min("synced_at"), newest=Max("synced_at")
        )
        current_month = now.astimezone().date().replace(day=1)
        clockify = ClockifyMonthSync.objects.filter(
            month=current_month
        ).aggregate(newest=Max("synced_at"))
        problems: list[str] = []
        for label, oldest, limit in (
            ("hojas", sheets["oldest"], options["hojas_horas"]),
            ("azure", azure["oldest"], options["azure_horas"]),
            (
                "clockify (mes actual)",
                clockify["newest"],
                options["clockify_horas"],
            ),
        ):
            problems.extend(self.report(label, oldest, limit, now))
        for lock in SyncLock.objects.all():
            minutes = (now - lock.locked_at).total_seconds() / 60
            self.stdout.write(
                f"en curso: {lock.name} desde hace {minutes:.0f} min"
            )
        if options["lecturas"]:
            catalog = ClockifyCatalog.objects.filter(
                workspace_id=settings.CLOCKIFY_WORKSPACE_ID
            ).first()
            panels = AzurePanelSnapshot.objects.aggregate(
                oldest=Min("synced_at")
            )
            missing = AzureProject.objects.filter(
                azurepanelsnapshot__isnull=True
            ).count()
            problems.extend(
                self.report(
                    "catálogo Clockify",
                    catalog.synced_at if catalog else None,
                    options["clockify_horas"],
                    now,
                )
            )
            problems.extend(
                self.report(
                    "paneles Azure",
                    panels["oldest"],
                    options["azure_horas"],
                    now,
                )
            )
            if missing:
                problems.append(
                    f"Azure: {missing} proyectos sin panel sincronizado"
                )
        if problems:
            raise CommandError("; ".join(problems))

    def report(
        self,
        label: str,
        moment: datetime | None,
        limit_hours: float,
        now: datetime,
    ) -> list[str]:
        """
        Escribe la antiguedad de una fuente.

        Args:
            label: Nombre de la fuente.
            moment: Cuando se sincronizo por ultima vez (None: nunca).
            limit_hours: Antiguedad maxima aceptada.
            now: Momento de la revision.

        Returns:
            El problema encontrado, o lista vacia si esta al dia.
        """
        if moment is None:
            self.stdout.write(self.style.ERROR(f"{label}: nunca sincronizado"))
            return [f"{label}: nunca sincronizado"]
        age = now - moment
        hours = age.total_seconds() / 3600
        text = f"{label}: hace {hours:.1f} h (limite {limit_hours:g} h)"
        if age > timedelta(hours=limit_hours):
            self.stdout.write(self.style.ERROR(text + " - VENCIDO"))
            return [f"{label} vencido"]
        self.stdout.write(self.style.SUCCESS(text))
        return []
