"""Comando que lista los workspaces de Clockify de la API key."""

from typing import Any

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from apps.clockify.services.clockify_client import ClockifyClient
from core.exceptions import DashboardError

"""BKD.020.012 - Workspaces de Clockify
Uso: python manage.py clockify_workspaces
Copia el ID que corresponda a CLOCKIFY_WORKSPACE_ID en el archivo .env.
"""


class Command(BaseCommand):
    """Muestra los workspaces visibles con CLOCKIFY_API_KEY."""

    help = "Lista los workspaces de Clockify disponibles."

    def handle(self, *args: Any, **options: Any) -> None:
        """Consulta y muestra los workspaces."""
        if not settings.CLOCKIFY_API_KEY:
            raise CommandError("Define CLOCKIFY_API_KEY en el archivo .env.")

        try:
            workspaces = ClockifyClient(
                settings.CLOCKIFY_API_KEY,
            ).list_workspaces()
        except DashboardError as error:
            raise CommandError(error.build_message()) from error

        for workspace in workspaces:
            self.stdout.write(f"{workspace['id']}  {workspace['nombre']}")
