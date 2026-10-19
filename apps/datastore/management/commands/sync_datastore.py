"""Comando que llena la base diaria con las horas de Clockify."""

from datetime import date, datetime
from typing import Any

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError, CommandParser
from django.utils import timezone

from apps.clockify.services.clockify_client import ClockifyClient
from apps.datastore.services.change_detection import plan_daily
from apps.datastore.services.clockify_sync import month_range, sync_months

"""BKD.130.005 - Sincronizar la base diaria
Sin opciones descarga los meses que aun pueden cambiar (ultimos 10 dias,
o desde la fecha de bloqueo de Clockify) y los meses guardados cuyos
totales ya no cuadran con el reporte resumido.
--desde AAAA-MM hace la carga inicial; --mes AAAA-MM recarga un mes.
Uso: python manage.py sync_datastore [--sin-verificar]
     python manage.py sync_datastore --desde AAAA-MM [--hasta AAAA-MM]
     python manage.py sync_datastore --mes AAAA-MM
"""


def parse_month(text: str) -> date:
    """
    Convierte AAAA-MM al primer dia del mes.

    Args:
        text: Mes en formato AAAA-MM.

    Returns:
        El primer dia del mes.

    Raises:
        CommandError: Cuando el formato no es valido.
    """
    try:
        return datetime.strptime(text, "%Y-%m").date()
    except ValueError as error:
        raise CommandError(f"Mes invalido: {text}. Usa AAAA-MM.") from error


class Command(BaseCommand):
    """Descarga meses completos de Clockify a la base."""

    help = "Llena la base diaria con las horas de Clockify."

    def add_arguments(self, parser: CommandParser) -> None:
        """Agrega --mes, --desde y --hasta."""
        parser.add_argument("--mes", help="Recarga un solo mes (AAAA-MM).")
        parser.add_argument("--desde", help="Carga inicial desde AAAA-MM.")
        parser.add_argument("--hasta", help="Ultimo mes de la carga inicial.")
        parser.add_argument(
            "--sin-verificar",
            action="store_true",
            help="Omite la comparacion de totales con el reporte resumido.",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        """Elige los meses, sincroniza y muestra el resultado."""
        if not settings.CLOCKIFY_API_KEY or not settings.CLOCKIFY_WORKSPACE_ID:
            raise CommandError(
                "Configura CLOCKIFY_API_KEY y CLOCKIFY_WORKSPACE_ID en .env.",
            )
        today = timezone.localdate()
        client = ClockifyClient(settings.CLOCKIFY_API_KEY)
        workspace_id = settings.CLOCKIFY_WORKSPACE_ID
        lock_seen: str | None = None
        notes: list[str] = []
        if options["mes"]:
            months, kind = [parse_month(options["mes"])], "manual_month"
        elif options["desde"]:
            last = parse_month(options["hasta"]) if options["hasta"] else today
            months = month_range(
                parse_month(options["desde"]), min(last, today)
            )
            kind = "backfill"
        else:
            plan = plan_daily(
                client, workspace_id, today, not options["sin_verificar"]
            )
            months, kind = plan.months, "daily"
            lock_seen, notes = plan.lock_seen, plan.notes
            for note in notes:
                self.stdout.write(self.style.WARNING(note))

        run = sync_months(
            months,
            client,
            workspace_id,
            kind,
            lock_seen=lock_seen,
            notes=notes,
        )
        finished = run.finished_at or timezone.now()
        seconds = (finished - run.started_at).total_seconds()
        summary = (
            f"{len(run.months)} meses, {run.entries} registros, "
            f"{run.requests} solicitudes, {seconds:.0f} s"
        )
        if run.status == "ok":
            self.stdout.write(self.style.SUCCESS(f"Clockify: {summary}"))
            return
        self.stdout.write(self.style.WARNING(f"Clockify: {summary}"))
        raise CommandError(run.error)
