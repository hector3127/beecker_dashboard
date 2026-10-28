"""Completa los catálogos y payloads que las pantallas consultaban en vivo."""

from typing import Any

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError, CommandParser

from apps.clockify.services.clockify_client import ClockifyClient
from apps.daily.services.daily_azure_client import DailyAzureClient
from apps.datastore.models import AzureProject, ClockifyProjectRecord
from apps.datastore.services import azure_panel_store, clockify_catalog
from apps.datastore.services.locks import sync_lock
from core.exceptions import DashboardError
from core.utils.parallel import map_in_parallel


def fetch_panel(name: str) -> tuple[int, list[dict[str, Any]]] | str:
    """Cada hilo usa su propia sesión HTTP y no escribe en la base."""
    client = DailyAzureClient(
        settings.AZURE_DEVOPS_ORGANIZATION, settings.AZURE_DEVOPS_PAT
    )
    try:
        return azure_panel_store.download(client, name)
    except (DashboardError, ValueError) as error:
        return (
            f"Azure {name}: {type(error).__name__}; "
            "se conserva el corte anterior"
        )


class Command(BaseCommand):
    """Sincroniza fuentes completas fuera de las peticiones web."""

    help = "Sincroniza catálogos Clockify y paneles Azure."

    def add_arguments(self, parser: CommandParser) -> None:
        """Selecciona fuentes y el alcance opcional."""
        parser.add_argument(
            "--fuente", choices=["clockify", "azure", "todas"], default="todas"
        )
        parser.add_argument(
            "--proyecto",
            help="Team Project exacto; por defecto todos los guardados.",
        )
        parser.add_argument(
            "--tasks",
            action="store_true",
            help="Incluye tareas Clockify (una petición por proyecto).",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        """Retiene el corte anterior de cada proyecto que falla."""
        with sync_lock("read-sources", 3 * 60 * 60) as acquired:
            if not acquired:
                raise CommandError(
                    "Otra sincronización de lecturas sigue en curso."
                )
            errors = []
            if options["fuente"] in ("clockify", "todas"):
                if (
                    not settings.CLOCKIFY_API_KEY
                    or not settings.CLOCKIFY_WORKSPACE_ID
                ):
                    raise CommandError("Clockify no está configurado.")
                client = ClockifyClient(settings.CLOCKIFY_API_KEY)
                workspace = settings.CLOCKIFY_WORKSPACE_ID
                self.stdout.write(
                    "Clockify: descargando catálogo de proyectos…"
                )
                self.stdout.flush()
                count = clockify_catalog.sync_catalog(client, workspace)
                self.stdout.write(f"Clockify: {count} proyectos guardados.")
                if options["tasks"]:
                    clockify_projects = ClockifyProjectRecord.objects.filter(
                        catalog__workspace_id=workspace
                    )
                    for project in clockify_projects.iterator():
                        try:
                            tasks = client.list_project_tasks(
                                workspace, project.external_id
                            )
                            clockify_catalog.save_tasks(
                                workspace, project.external_id, tasks
                            )
                        except (DashboardError, ValueError) as error:
                            errors.append(
                                f"Tasks {project.external_id}: "
                                f"{type(error).__name__}"
                            )
            if options["fuente"] in ("azure", "todas"):
                if (
                    not settings.AZURE_DEVOPS_ORGANIZATION
                    or not settings.AZURE_DEVOPS_PAT
                ):
                    raise CommandError("Azure no está configurado.")
                projects = AzureProject.objects.order_by("position")
                if options["proyecto"]:
                    projects = projects.filter(name=options["proyecto"])
                names = list(projects.values_list("name", flat=True))
                if not names:
                    raise CommandError(
                        "No hay proyectos: ejecuta primero "
                        "sync_datastore --pasos azure."
                    )
                self.stdout.write(
                    f"Azure: descargando {len(names)} proyectos "
                    "(máximo 4 conexiones)…"
                )
                self.stdout.flush()
                outcomes = map_in_parallel(fetch_panel, names, 4)
                for name, outcome in zip(names, outcomes, strict=True):
                    if isinstance(outcome, str):
                        errors.append(outcome)
                        continue
                    total, items = outcome
                    azure_panel_store.save(name, total, items)
                    self.stdout.write(
                        f"Azure {name}: {len(items)} de {total} "
                        "work items guardados."
                    )
            if errors:
                raise CommandError("\n".join(errors))
