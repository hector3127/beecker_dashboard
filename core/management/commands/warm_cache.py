"""Comando que precalienta la cache de las vistas del panel."""

import functools
import logging
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
lectura. Prepara Ejecutiva, Operativa, Comercial y sus componentes.
El panel anterior solo se incluye si se solicita explicitamente --legacy.
Uso: python manage.py warm_cache [--base-only] [--legacy] [--refresh]
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
    "getResumenRecursos",
    "obtenerResumenAERTYMMPB",
    "obtenerResumenIXBRaaS",
)

SHEETS_STEP = "hojas de Sheets"
RAID_STEP = "RAID de Azure por proyecto"
AER_CONSUMPTION_FUNCTION = "obtenerConsumosResumenAERTYMMPB"
AER_SUMMARY_FUNCTION = "obtenerResumenAERTYMMPB"
CONSUMPTION_BATCH_SIZE = 2
RAID_WORKERS = 4
logger = logging.getLogger(__name__)


class Command(BaseCommand):
    """Consulta las vistas principales para llenar la cache."""

    help = "Prepara Ejecutiva, Operativa y Comercial con sus componentes."

    def add_arguments(self, parser: CommandParser) -> None:
        """Agrega la opcion --refresh."""
        parser.add_argument(
            "--base-only",
            action="store_true",
            help="Prepara los proyectos de Operativa solo desde Sheets.",
        )
        parser.add_argument(
            "--legacy",
            action="store_true",
            help="Incluye tambien la precarga completa del panel anterior.",
        )
        parser.add_argument(
            "--portal-only",
            action="store_true",
            help="Prepara las tres paginas principales (opcion compatible).",
        )
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

        if options["base_only"]:
            self.run_step(
                "Operativa: proyectos y estados",
                functools.partial(warm_portal, base_only=True),
            )
            return
        self.run_step("portal", warm_portal)
        self.run_step("pantallas secundarias", warm_secondary_pages)
        if options["portal_only"] or not options["legacy"]:
            return

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


def warm_portal(base_only: bool = False) -> object:
    """Prepara los mismos cortes que consulta el navegador, sin borrar cache."""
    from django.contrib.auth.models import User
    from django.test import RequestFactory

    from apps.portal import views
    from apps.portal.services.operativa_status import block_error

    factory = RequestFactory()
    failures = []
    blocks = (
        ("",) if base_only else ("", "eva4", "eva3", "inversion", "capacidad")
    )
    for block in blocks:
        started = time.perf_counter()
        logger.info("Preparando Operativa: %s", block or "proyectos y estados")
        request = factory.get("/operativa/datos/", {"bloque": block})
        request.user = User(username="cache-warmer")
        context = views.operativa_block_context(request)
        if context.get("source_errors") or block_error(context):
            failures.append(block or "portafolio")
        logger.info(
            "Operativa %s: %.1f s",
            block or "proyectos y estados",
            time.perf_counter() - started,
        )
    if base_only:
        return {"ok": not failures, "error": ", ".join(failures)}

    started = time.perf_counter()
    logger.info("Preparando Operativa: facturabilidad")
    try:
        partial = views.operations_summary_data(refresh=True).errors
    except DashboardError:
        partial = True
    if partial:
        failures.append("facturabilidad")
    logger.info("Facturabilidad: %.1f s", time.perf_counter() - started)
    for name, path, page in (("comercial", "/comercial/", views.comercial),):
        started = time.perf_counter()
        logger.info("Preparando %s y sus componentes", name)
        request = factory.get(path, {"actualizar": "1"})
        request.portal_warmer = True  # type: ignore[attr-defined]
        request.user = User(username="cache-warmer")
        response = page(request)
        if (
            response.status_code != 200
            or b'data-portal-ready="true"' not in response.content
        ):
            failures.append(name)
        logger.info("%s: %.1f s", name, time.perf_counter() - started)
    manager_result = warm_delivery_managers()
    manager_error = read_failure(manager_result)
    if manager_error:
        failures.append("Delivery Managers: " + manager_error)
    from apps.portal.services.financial_cache import warm_financial

    started = time.perf_counter()
    logger.info("Preparando Financiera: ingresos, costos y rentabilidad")
    financial_error = read_failure(warm_financial())
    if financial_error:
        failures.append("Financiera: " + financial_error)
    logger.info("Financiera: %.1f s", time.perf_counter() - started)
    from apps.portal.services.executive_operations import warm_operations

    started = time.perf_counter()
    logger.info("Preparando Operations de Ejecutiva: Budget, avance y ETC")
    try:
        operations_error = read_failure(warm_operations())
    except (DashboardError, ValueError) as error:
        operations_error = str(error)
    if operations_error:
        failures.append("Operations de Ejecutiva: " + operations_error)
    logger.info(
        "Operations de Ejecutiva: %.1f s", time.perf_counter() - started
    )
    from apps.portal.services.executive_commercial import (
        warm_commercial_summary,
    )

    started = time.perf_counter()
    logger.info("Preparando Comercial de Ejecutiva")
    try:
        commercial_error = read_failure(warm_commercial_summary())
    except (DashboardError, ValueError) as error:
        commercial_error = str(error)
    if commercial_error:
        failures.append("Comercial de Ejecutiva: " + commercial_error)
    logger.info("Comercial de Ejecutiva: %.1f s", time.perf_counter() - started)
    return {"ok": not failures, "error": ", ".join(failures)}


def warm_secondary_pages() -> object:
    """
    Prepara las pantallas que no cubre warm_portal y tardan en su primera carga.

    KPIs de Delivery Managers (~3 s) y los proyectos cerrados de EVA 1 (~4 s,
    leen Azure DevOps). Sin esto, la primera persona tras vencer la cache
    espera esa carga. Solo lee; una pantalla que falla no detiene a las demas.
    """
    from django.contrib.auth.models import User
    from django.test import RequestFactory

    from apps.portal import views

    factory = RequestFactory()
    failures = []
    for name, path, page in (
        ("kpis", "/operativa/kpis-delivery-managers/", warm_kpis),
        ("eva1_cerrados", "/operativa/eva-1/cerrados/", views.eva1_cerrados),
    ):
        started = time.perf_counter()
        request = factory.get(path)
        request.user = User(username="cache-warmer")
        try:
            response = page(request)
        except DashboardError as error:
            failures.append(f"{name}: {error.build_message()}")
            continue
        if response.status_code != 200:
            failures.append(name)
        logger.info("%s: %.1f s", name, time.perf_counter() - started)
    return {"ok": not failures, "error": ", ".join(failures)}


def warm_kpis(request: Any) -> Any:
    """Arma el historico de KPIs de Delivery Managers para dejarlo en cache."""
    from django.http import HttpResponse

    from apps.portal import views

    views.kpi_context(request)
    return HttpResponse(status=200)


def warm_delivery_managers() -> object:
    """Prepara los detalles y el grafico de seis meses de cada manager."""
    from django.test import RequestFactory

    from apps.access.scope import AccessScope
    from apps.portal import views

    snapshot = views._operativa_snapshot(RequestFactory().get("/operativa/"))
    if not snapshot:
        return {"ok": True}
    everything = AccessScope.everything()
    failures = []
    for manager in snapshot.get("managers", []):
        started = time.perf_counter()
        logger.info("Preparando detalle y consumo mensual: %s", manager.name)
        for stage in ("base", "inv", "horas"):
            try:
                views.dm_state(manager.slug, stage, everything)
            except Exception as error:  # noqa: BLE001
                failures.append(f"{manager.name}: {stage} ({error})")
                continue
            saved = cache.get(views._dm_key(manager.slug, stage, everything))
            if saved is None:
                failures.append(manager.name + ": " + stage)
            elif stage == "horas" and not saved.get("complete"):
                failures.append(manager.name + ": consumo mensual incompleto")
            elif stage == "inv" and not saved.get("investment", {}).get(
                "complete"
            ):
                failures.append(manager.name + ": inversion incompleta")
        logger.info(
            "Detalle %s: %.1f s", manager.name, time.perf_counter() - started
        )
    return {"ok": not failures, "error": "; ".join(failures)}


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
