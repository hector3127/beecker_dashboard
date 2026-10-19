"""Comando que llena la base diaria con las horas de Clockify."""

import time
from datetime import date, datetime
from typing import Any

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError, CommandParser
from django.utils import timezone

from apps.clockify.services.clockify_client import ClockifyClient
from apps.datastore.services.catalogs import build_catalogs
from apps.datastore.services.change_detection import plan_daily
from apps.datastore.services.clockify_sync import month_range, sync_months
from apps.datastore.services.sheet_sync import sync_sheets
from core.exceptions import DashboardError
from core.sheets.factory import build_sheet_repository
from core.sheets.store_read_cache import STORED_SHEETS, read_snapshot

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
        parser.add_argument(
            "--solo-hojas",
            action="store_true",
            help="Solo guarda las hojas de Sheets (rapido, para cada hora).",
        )
        parser.add_argument(
            "--sin-hojas",
            action="store_true",
            help="No guarda las hojas de Sheets.",
        )
        parser.add_argument(
            "--sin-catalogos",
            action="store_true",
            help="No reconstruye los catalogos de clientes, personas y "
            "proyectos.",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        """Guarda las hojas y las horas de Clockify; muestra el resultado."""
        failures: list[str] = []
        if not options["sin_hojas"]:
            failures.extend(self.sync_sheets())
        if not options["solo_hojas"]:
            failures.extend(self.sync_clockify(options))
        if not options["sin_catalogos"]:
            self.sync_catalogs()
        if failures:
            raise CommandError("\n".join(failures))

    def sync_sheets(self) -> list[str]:
        """
        Guarda las hojas de entrada en la base.

        Returns:
            El error si fallo; lista vacia si todo salio bien.
        """
        started = time.perf_counter()
        try:
            saved = sync_sheets(build_sheet_repository(use_store=False))
        except DashboardError as error:
            self.stdout.write(self.style.WARNING("Hojas: " + str(error)))
            return [f"Hojas: {error}"]
        self.stdout.write(
            self.style.SUCCESS(
                f"Hojas: {len(saved)} guardadas en "
                f"{time.perf_counter() - started:.0f} s"
            )
        )
        return []

    def sync_catalogs(self) -> None:
        """Reconstruye los catalogos con las hojas ya guardadas."""
        sheets = {
            name: rows
            for name in STORED_SHEETS
            if isinstance(rows := read_snapshot(name), list)
        }
        if not sheets:
            self.stdout.write(
                self.style.WARNING("Catalogos: no hay hojas guardadas.")
            )
            return
        result = build_catalogs(sheets)
        for warning in result.warnings:
            self.stdout.write(self.style.WARNING(warning))
        self.stdout.write(
            self.style.SUCCESS(
                f"Catalogos: {result.clients} clientes, {result.persons} "
                f"personas, {result.projects} proyectos "
                f"({len(result.merged_clients)} clientes y "
                f"{len(result.merged_persons)} personas con variantes unidas)"
            )
        )

    def sync_clockify(self, options: dict[str, Any]) -> list[str]:
        """
        Descarga los meses de Clockify que corresponden a las opciones.

        Args:
            options: Opciones del comando.

        Returns:
            Los errores; lista vacia si todo salio bien.
        """
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
            return []
        self.stdout.write(self.style.WARNING(f"Clockify: {summary}"))
        return [run.error]
