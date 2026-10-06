"""Comando que precalienta la cache de las vistas del panel."""

import functools
import time
from collections.abc import Callable
from typing import Any

from django.core.cache import cache
from django.core.management.base import BaseCommand, CommandParser

from core.exceptions import DashboardError
from core.rpc.registry import get_rpc_function
from core.sheets import sheet_names
from core.sheets.factory import build_sheet_repository
from core.utils.parallel import map_in_parallel

"""BKD.006.008 - Precalentar cache
Equivale a dejar un trigger en Apps Script: consulta las vistas para que
el primer usuario no espere a Clockify, Azure ni Sheets. Todo es de solo
lectura. Orden: hojas de Sheets, vistas, RAID de cada Team Project y
consumos AER; cada paso deja datos para el siguiente.
Uso: python manage.py warm_cache [--refresh]
"""

# Hojas que mas leen las vistas; la cache compartida las reutiliza.
HOT_SHEETS: tuple[str, ...] = (
    sheet_names.SHEET_PROJECTS,
    sheet_names.SHEET_PROJECTS_HISTORY,
    sheet_names.SHEET_RESOURCES,
    sheet_names.SHEET_RISKS,
    sheet_names.SHEET_SPRINTS,
    sheet_names.SHEET_SALARY_BANDS,
    sheet_names.SHEET_MASTER_RATES,
    sheet_names.SHEET_DASHBOARD_KPI_HISTORY,
    sheet_names.SHEET_MINUTES_PENDING,
    "Clockify_Vinculos",
    "MPB",
    "ROC",
)

WARM_FUNCTIONS: tuple[str, ...] = (
    "getDashboardData",
    "getResumenRecursos",
    "obtenerTopRiesgosPortafolioAzure",
    "obtenerResumenAERTYMMPB",
    "obtenerResumenIXBRaaS",
)

SHEETS_STEP = "hojas de Sheets"
RAID_STEP = "RAID de Azure por proyecto"
AER_CONSUMPTION_FUNCTION = "obtenerConsumosResumenAERTYMMPB"
AER_SUMMARY_FUNCTION = "obtenerResumenAERTYMMPB"
CONSUMPTION_BATCH_SIZE = 2
RAID_WORKERS = 4


class Command(BaseCommand):
    """Consulta las vistas principales para llenar la cache."""

    help = "Precalienta la cache del dashboard, Azure y Clockify."

    def add_arguments(self, parser: CommandParser) -> None:
        """Agrega la opcion --refresh."""
        parser.add_argument(
            "--refresh",
            action="store_true",
            help="Borra la cache antes de consultar (datos 100%% frescos).",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        """Ejecuta las consultas y muestra el tiempo de cada una."""
        if options["refresh"]:
            cache.clear()
            self.stdout.write("Cache borrada.")

        self.run_step(SHEETS_STEP, warm_sheets)

        for function_name in WARM_FUNCTIONS:
            self.run_step(function_name, functools.partial(call, function_name))

        self.run_step(RAID_STEP, warm_raid)
        self.run_step(AER_CONSUMPTION_FUNCTION, warm_aer_consumption)

    def run_step(self, label: str, step: Callable[[], object]) -> None:
        """
        Ejecuta un paso y reporta su duracion o su error.

        Args:
            label: Nombre del paso.
            step: Funcion a ejecutar.
        """
        start_time = time.perf_counter()

        try:
            result = step()
        except DashboardError as error:
            self.stdout.write(
                self.style.ERROR(f"{label}: {error.build_message()}"),
            )
            return

        elapsed_seconds = time.perf_counter() - start_time
        failure = read_failure(result)

        if failure:
            self.stdout.write(self.style.WARNING(f"{label}: {failure}"))
            return

        self.stdout.write(
            self.style.SUCCESS(f"{label}: listo en {elapsed_seconds:.1f} s"),
        )


def call(function_name: str, *args: object) -> object:
    """
    Ejecuta una funcion registrada en el RPC.

    Args:
        function_name: Nombre de la funcion en Apps Script.
        args: Argumentos de la funcion.

    Returns:
        El resultado de la funcion.

    Raises:
        DashboardError: Cuando la funcion no esta registrada.
    """
    rpc_function = get_rpc_function(function_name)

    if rpc_function is None:
        raise DashboardError(f"La funcion {function_name} no esta registrada.")

    return rpc_function(*args)


def warm_sheets() -> object:
    """
    Lee las hojas mas usadas en una sola llamada y las deja en cache.

    Returns:
        {"ok": True} cuando termina.
    """
    build_sheet_repository().prefetch(HOT_SHEETS)

    return {"ok": True}


def warm_raid() -> object:
    """
    Descarga el RAID de cada Team Project de Azure, de cuatro en cuatro.

    Returns:
        {"ok": True}, o un error con los proyectos que fallaron.

    Raises:
        DashboardError: Cuando Azure no esta configurado o no responde.
    """
    from apps.azure_devops.gateway import AzureDevOpsGateway
    from apps.azure_devops.services.portfolio_risks import (
        group_projects_by_azure,
    )

    gateway = AzureDevOpsGateway()
    project_rows = build_sheet_repository().read_as_objects(
        sheet_names.SHEET_PROJECTS,
    )
    groups = group_projects_by_azure(
        project_rows,
        gateway.list_project_names(),
    )

    def load(azure_project: str) -> str:
        try:
            gateway.list_raid(azure_project)
        except DashboardError as error:
            return f"{azure_project}: {error.detail}"

        return ""

    failures = [
        failure
        for failure in map_in_parallel(load, list(groups), RAID_WORKERS)
        if failure
    ]

    if failures:
        return {"ok": False, "error": "; ".join(failures)}

    return {"ok": True}


def warm_aer_consumption() -> object:
    """
    Calcula las horas de todos los proyectos AER/T&M, de dos en dos.

    Returns:
        El ultimo resultado, o un error si el resumen fallo.
    """
    summary = call(AER_SUMMARY_FUNCTION)

    if not isinstance(summary, dict) or not summary.get("ok"):
        return summary

    project_ids = [row["idProyecto"] for row in summary.get("filas", [])]
    result: object = {"ok": True}

    for batch_start in range(0, len(project_ids), CONSUMPTION_BATCH_SIZE):
        batch_end = batch_start + CONSUMPTION_BATCH_SIZE
        result = call(
            AER_CONSUMPTION_FUNCTION, project_ids[batch_start:batch_end]
        )

    return result


def read_failure(result: object) -> str:
    """
    Extrae el mensaje de error de una respuesta {"ok": false}.

    Args:
        result: Respuesta de la funcion.

    Returns:
        El mensaje de error, o cadena vacia si fue exitosa.
    """
    if isinstance(result, dict) and result.get("ok") is False:
        return str(result.get("error") or result.get("message") or "fallo")

    return ""
