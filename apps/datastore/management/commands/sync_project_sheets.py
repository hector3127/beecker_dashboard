"""Prepara copias manuales de proyectos para Genesis."""

import logging
import time
from typing import Any

from django.core.management.base import BaseCommand, CommandError, CommandParser

from apps.datastore.models import SheetSnapshot
from apps.datastore.services.locks import sync_lock
from apps.datastore.services.project_sheets import (
    ALLOWED_PROJECT_SHEETS,
    PROJECT_SHEETS,
    selected_sheets,
    sync_project_sheets,
)
from core.exceptions import DashboardError
from core.sheets.factory import build_sheet_repository
from core.sheets.store_read_cache import SHEET_IDS_NAME

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    """Inspección local por defecto; descarga solo con --aplicar."""

    help = (
        "Inspecciona las copias manuales de proyectos; "
        "usa --aplicar para descargarlas."
    )

    def add_arguments(self, parser: CommandParser) -> None:
        """Selecciona hojas y exige una opción explícita para aplicar."""
        parser.add_argument(
            "--hoja", action="append", choices=list(ALLOWED_PROJECT_SHEETS)
        )
        parser.add_argument(
            "--aplicar",
            action="store_true",
            help="Consulta Google y guarda el conjunto validado.",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        """Inspecciona sin red o carga bajo el candado de hojas."""
        wanted = selected_sheets(options["hoja"] or PROJECT_SHEETS)
        if not options["aplicar"]:
            self.show_plan(wanted)
            return
        started = time.perf_counter()
        try:
            with sync_lock("hojas", 15 * 60) as acquired:
                if not acquired:
                    raise CommandError(
                        "Otra sincronización de hojas sigue en curso."
                    )
                result = sync_project_sheets(
                    build_sheet_repository(use_store=False), wanted
                )
        except DashboardError as error:
            logger.warning(
                "project_sheets_sync_failed",
                extra={"error_type": type(error).__name__},
            )
            raise CommandError(error.build_message()) from error
        for name, count in result.items():
            self.stdout.write(f"{name}: {count} registros guardados.")
        self.stdout.write(
            f"Carga terminada en {time.perf_counter() - started:.2f} s."
        )

    def show_plan(self, wanted: list[str]) -> None:
        """Inventario local sin credenciales, red ni escrituras."""
        rows = SheetSnapshot.objects.filter(name__in=wanted).values(
            "name", "row_count", "synced_at"
        )
        copies = {row["name"]: row for row in rows}
        ids = (
            SheetSnapshot.objects.filter(name=SHEET_IDS_NAME)
            .values_list("rows", flat=True)
            .first()
        )
        self.stdout.write(
            "Inspección local: sin conexión a Google ni cambios en la base."
        )
        for name in wanted:
            copy = copies.get(name)
            status = (
                f"copia guardada {copy['synced_at'].isoformat()}"
                if copy
                else "sin copia local"
            )
            declared = (
                "declarada en el catálogo"
                if isinstance(ids, dict) and name in ids
                else "origen sin confirmar"
            )
            self.stdout.write(f"{name}: {status}; {declared}.")
        self.stdout.write(
            "Para descargar y guardar este alcance usa --aplicar."
        )
