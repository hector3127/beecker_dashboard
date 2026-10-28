"""Comando que llena la base diaria con las horas de Clockify."""

import time
from datetime import date, datetime
from typing import Any

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError, CommandParser
from django.utils import timezone

from apps.azure_devops.exceptions import AzureDevOpsConfigurationError
from apps.azure_devops.gateway import AzureDevOpsGateway
from apps.clockify.services.clockify_client import ClockifyClient
from apps.datastore.services.azure_sync import sync_azure
from apps.datastore.services.catalogs import build_catalogs
from apps.datastore.services.change_detection import plan_daily
from apps.datastore.services.clockify_sync import month_range, sync_months
from apps.datastore.services.locks import sync_lock
from apps.datastore.services.sheet_sync import sync_sheets
from core.exceptions import DashboardError
from core.sheets.factory import build_sheet_repository
from core.sheets.store_read_cache import STORED_SHEETS, read_snapshot

"""BKD.130.005 - Sincronizar la base diaria
Pasos: hojas (Sheets), azure (Azure DevOps), clockify (horas) y catalogos
(clientes, personas y proyectos). Sin opciones corre todos. En Clockify
descarga los meses que aun pueden cambiar (ultimos 10 dias, o desde la
fecha de bloqueo) y los guardados cuyos totales ya no cuadran con el
reporte resumido. Cada paso toma un candado: si otra ejecucion lo tiene,
se omite.
Uso programado (ver docs/ejecucion-programada.md):
     cada hora:  sync_datastore --pasos hojas,azure,catalogos
     cada dia:   sync_datastore --pasos clockify,catalogos
Otros: sync_datastore --desde AAAA-MM [--hasta AAAA-MM]  (carga inicial)
       sync_datastore --mes AAAA-MM                       (recarga un mes)
       sync_datastore --sin-verificar                     (sin comparar totales)
"""

STEPS = ("hojas", "azure", "clockify", "lecturas", "catalogos")
# Despues de este tiempo un candado se considera abandonado (el proceso
# murio). Clockify admite la carga inicial, que tarda cerca de una hora.
LOCK_SECONDS = {
    "hojas": 15 * 60,
    "azure": 30 * 60,
    "clockify": 3 * 60 * 60,
    "catalogos": 15 * 60,
    "lecturas": 3 * 60 * 60,
}


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
            "--solo-azure",
            action="store_true",
            help="Solo guarda Azure DevOps (work items, RAID, iteraciones).",
        )
        parser.add_argument(
            "--sin-azure",
            action="store_true",
            help="No guarda Azure DevOps.",
        )
        parser.add_argument(
            "--sin-catalogos",
            action="store_true",
            help="No reconstruye los catalogos de clientes, personas y "
            "proyectos.",
        )
        parser.add_argument(
            "--pasos",
            help="Pasos a correr, separados por coma: "
            + ", ".join(STEPS)
            + ". Por defecto todos.",
        )

    def selected_steps(self, options: dict[str, Any]) -> list[str]:
        """
        Pasos que corresponden a las opciones, en su orden de ejecucion.

        Args:
            options: Opciones del comando.

        Returns:
            Los pasos a correr.

        Raises:
            CommandError: Cuando --pasos trae un paso que no existe.
        """
        if options["pasos"]:
            chosen = {
                p.strip() for p in options["pasos"].split(",") if p.strip()
            }
            unknown = chosen - set(STEPS)
            if unknown:
                raise CommandError(
                    f"Paso desconocido: {', '.join(sorted(unknown))}. "
                    f"Usa: {', '.join(STEPS)}."
                )
        elif options["solo_hojas"]:
            chosen = {"hojas", "catalogos"}
        elif options["solo_azure"]:
            chosen = {"azure"}
        else:
            chosen = set(STEPS)
        for flag, step in (
            ("sin_hojas", "hojas"),
            ("sin_azure", "azure"),
            ("sin_catalogos", "catalogos"),
        ):
            if options[flag]:
                chosen.discard(step)
        return [step for step in STEPS if step in chosen]

    def handle(self, *args: Any, **options: Any) -> None:
        """Corre los pasos elegidos, cada uno con su candado."""
        runners = {
            "hojas": lambda: self.sync_sheets(),
            "azure": lambda: self.sync_azure_projects(),
            "clockify": lambda: self.sync_clockify(options),
            "catalogos": lambda: self.sync_catalogs(),
            "lecturas": lambda: self.sync_read_sources(options),
        }
        failures: list[str] = []
        for step in self.selected_steps(options):
            with sync_lock(step, LOCK_SECONDS[step]) as acquired:
                if not acquired:
                    self.stdout.write(
                        self.style.WARNING(
                            f"{step}: otra sincronizacion sigue en curso; "
                            "se omite."
                        )
                    )
                    continue
                failures.extend(runners[step]())
        if failures:
            raise CommandError("\n".join(failures))

    def sync_read_sources(self, options: dict[str, Any]) -> list[str]:
        """Guarda fuentes completas sin ignorar --sin-azure."""
        try:
            call_command(
                "sync_read_sources",
                fuente="clockify" if options["sin_azure"] else "todas",
                stdout=self.stdout,
                stderr=self.stderr,
            )
        except (CommandError, DashboardError) as error:
            return [f"Lecturas: {error}"]
        return []

    def sync_azure_projects(self) -> list[str]:
        """
        Guarda los Team Projects de Azure DevOps en la base.

        Returns:
            Los errores; lista vacia si todo salio bien o si Azure no esta
            configurado (se avisa y se omite).
        """
        try:
            result = sync_azure(AzureDevOpsGateway())
        except AzureDevOpsConfigurationError as error:
            self.stdout.write(self.style.WARNING(f"Azure: omitido ({error})"))
            return []
        except DashboardError as error:
            self.stdout.write(self.style.WARNING(f"Azure: {error}"))
            return [f"Azure: {error}"]
        for failure in result.failed:
            self.stdout.write(
                self.style.WARNING(
                    f"Azure: se conserva la copia anterior de {failure}"
                )
            )
        self.stdout.write(
            self.style.SUCCESS(
                f"Azure: {result.projects} proyectos, "
                f"{result.work_items} work items, "
                f"{result.iterations} iteraciones en {result.seconds:.0f} s"
            )
        )
        if result.projects == 0 and result.failed:
            return ["Azure: no se pudo leer ningun proyecto"]
        return []

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

    def sync_catalogs(self) -> list[str]:
        """
        Reconstruye los catalogos con las hojas ya guardadas.

        Returns:
            Siempre vacia: sin hojas guardadas solo avisa.
        """
        sheets = {
            name: rows
            for name in STORED_SHEETS
            if isinstance(rows := read_snapshot(name), list)
        }
        if not sheets:
            self.stdout.write(
                self.style.WARNING("Catalogos: no hay hojas guardadas.")
            )
            return []
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
        return []

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
