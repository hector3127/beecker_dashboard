"""Comando que crea las hojas del sistema con sus encabezados."""

from typing import Any

from django.core.management.base import BaseCommand, CommandError

from core.exceptions import DashboardError
from core.sheets.factory import build_sheet_repository
from core.sheets.sheet_schema import SHEET_HEADERS

"""BKD.004.008 - Inicializar hojas
Equivale a inicializarSistema() de Setup.gs.
Uso: python manage.py init_sheets
"""


class Command(BaseCommand):
    """Crea las hojas maestras e historicas que todavia no existen."""

    help = "Crea las hojas del sistema con sus encabezados."

    def handle(self, *args: Any, **options: Any) -> None:
        """Ejecuta la creacion de hojas."""
        try:
            repository = build_sheet_repository()
            created_sheets = [
                sheet_name
                for sheet_name, headers in SHEET_HEADERS.items()
                if repository.ensure_sheet(sheet_name, headers)
            ]
        except DashboardError as error:
            raise CommandError(error.build_message()) from error

        if created_sheets:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Se crearon {len(created_sheets)} hojas nuevas: "
                    f"{', '.join(created_sheets)}",
                ),
            )
            return

        self.stdout.write(
            self.style.SUCCESS("Todas las hojas ya existian."),
        )
