"""Comando que precalienta la cache de las vistas del panel."""

import functools
import time
from collections.abc import Callable
from typing import Any

from django.core.cache import cache
from django.core.management.base import BaseCommand, CommandParser

from core.exceptions import DashboardError
from core.rpc.registry import get_rpc_function

"""BKD.006.008 - Precalentar cache
Equivale a dejar un trigger en Apps Script: consulta las vistas para que
el primer usuario no espere a Clockify ni a Azure.
Uso: python manage.py warm_cache [--refresh]
"""

WARM_FUNCTIONS: tuple[str, ...] = (
    "getDashboardData",
    "obtenerTopRiesgosPortafolioAzure",
    "obtenerResumenAERTYMMPB",
    "obtenerResumenIXBRaaS",
)

AER_CONSUMPTION_FUNCTION = "obtenerConsumosResumenAERTYMMPB"
AER_SUMMARY_FUNCTION = "obtenerResumenAERTYMMPB"
CONSUMPTION_BATCH_SIZE = 2


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

        for function_name in WARM_FUNCTIONS:
            self.run_step(function_name, functools.partial(call, function_name))

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
