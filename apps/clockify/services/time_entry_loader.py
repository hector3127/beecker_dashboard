"""Extraccion de las horas de todo el portafolio desde Clockify."""

import calendar
import hashlib
import logging
import threading
from collections.abc import Callable
from dataclasses import dataclass, replace
from datetime import date, timedelta
from zoneinfo import ZoneInfo

from django.conf import settings

from apps.clockify.constants import (
    MAX_PARALLEL_REPORTS,
    PROJECTS_CACHE_SECONDS,
    REPORT_TIMEZONE,
    SHEET_PROJECT_LINKS,
    TASKS_CACHE_SECONDS,
)
from apps.clockify.exceptions import ClockifyProjectError
from apps.clockify.services.clockify_client import (
    ClockifyClient,
    ClockifyProject,
    JsonObject,
)
from apps.clockify.services.cr_hours import cr_nomenclature, matches_cr_task
from apps.clockify.services.date_ranges import (
    ProjectDateRange,
    ProjectDateRangeResolver,
)
from apps.clockify.services.project_matcher import (
    normalize_link_key,
    resolve_clockify_project,
)
from apps.clockify.services.report_cache import (
    monthly_cache_seconds,
    report_cache_seconds,
)
from apps.clockify.services.report_mapper import (
    build_time_entry_from_report,
    parse_entry_day,
)
from core.exceptions import SheetNotFoundError, TimeEntrySourceError
from core.sheets import sheet_names
from core.sheets.protocols import SheetReader
from core.time_entries.models import TimeEntry
from core.time_entries.resource_rates import load_costing_rate_by_resource
from core.utils.cache_store import CacheStore
from core.utils.parallel import map_in_parallel
from core.utils.text import get_flexible_value, to_text

"""BKD.020.008 - Horas del portafolio desde Clockify
Equivale a leerRegistrosTiempo() + obtenerHorasClockifyPorProyecto():
consulta cada proyecto con su rango de fechas y junta todo en una sola
lista sin registros repetidos. Las hojas se leen en el hilo principal y
solo las descargas de Clockify se hacen en paralelo.
"""

logger = logging.getLogger(__name__)

# Striped locks coalesce identical report downloads within each worker.
_REPORT_LOCKS = [threading.RLock() for _ in range(64)]


@dataclass(frozen=True, slots=True)
class ReportPlan:
    """Descarga pendiente: proyecto interno, proyecto de Clockify y rango."""

    internal_id: str
    clockify_project_id: str
    start_date: date
    end_date: date
    task_nomenclature: str = ""
    empty_range: bool = False


@dataclass(frozen=True, slots=True)
class ProjectReport:
    """Reporte de un proyecto con el proyecto de Clockify consultado."""

    project: ClockifyProject
    entries: list[TimeEntry]
    request_count: int


@dataclass(frozen=True, slots=True)
class ProjectHours:
    """Horas de un proyecto con el proyecto de Clockify y el rango usado."""

    entries: list[TimeEntry]
    project_name: str
    date_range: ProjectDateRange
    project_id: str = ""


ProjectLookups = tuple[list[ClockifyProject], dict[str, str]]


class ClockifyTimeEntryLoader:
    """Descarga y combina las horas de todos los proyectos."""

    def __init__(
        self,
        reader: SheetReader,
        client_factory: Callable[[], ClockifyClient],
        workspace_id: str,
        today: date,
        cache_store: CacheStore,
        cache_prefix: str,
    ) -> None:
        self._reader = reader
        self._client_factory = client_factory
        self._workspace_id = workspace_id
        self._today = today
        self._cache_store = cache_store
        self._cache_prefix = cache_prefix
        self._timezone = ZoneInfo(REPORT_TIMEZONE)
        self._projects: list[ClockifyProject] | None = None
        # Se calcula aqui (hilo principal): cambia con cada sincronizacion
        # y deja vencidos los cortes guardados con la base anterior.
        self._store_stamp = ""
        self._synced_months: frozenset[date] = frozenset()
        if settings.CLOCKIFY_STORE_ENABLED:
            from apps.datastore.services.clockify_store import store_state

            self._store_stamp, self._synced_months = store_state()

    def load_all(self) -> tuple[TimeEntry, ...]:
        """
        Descarga las horas de todos los proyectos del panel.

        Returns:
            Los registros sin duplicados.

        Raises:
            ClockifyProjectError: Cuando algun proyecto falla; nunca se
                calculan indicadores con datos incompletos.
        """
        lookups = self._load_lookups()
        rates = load_costing_rate_by_resource(self._reader)
        range_resolver = ProjectDateRangeResolver(self._reader, self._today)
        plans: list[ReportPlan] = []
        errors: list[str] = []

        for internal_id in collect_project_ids(self._reader):
            try:
                plans.append(
                    self._plan_report(
                        internal_id,
                        range_resolver.resolve(internal_id),
                        lookups,
                    ),
                )
            except TimeEntrySourceError as error:
                errors.append(f"{internal_id}: {error.detail}")

        entries_by_key: dict[str, TimeEntry] = {}

        outcomes = list(zip(plans, self._fetch_many(plans, rates), strict=True))
        # Los CR compartidos reclaman primero sus registros. Asi el proyecto
        # base no absorbe esas horas ni se cuentan dos veces en el portafolio.
        outcomes.sort(
            key=lambda item: bool(item[0].task_nomenclature), reverse=True
        )
        for plan, outcome in outcomes:
            if isinstance(outcome, TimeEntrySourceError):
                errors.append(f"{plan.internal_id}: {outcome.detail}")
                continue

            for time_entry in outcome:
                # Varios IDs internos (S1/S2/CR1) pueden apuntar al mismo
                # proyecto de Clockify; cada registro cuenta una vez.
                entries_by_key.setdefault(
                    f"id:{time_entry.entry_id}",
                    time_entry,
                )

        if errors:
            raise ClockifyProjectError(
                "No se completo Clockify. " + "; ".join(errors),
            )

        return tuple(entries_by_key.values())

    def load_project(
        self,
        internal_id: str,
        custom_range: tuple[date, date] | None = None,
    ) -> list[TimeEntry]:
        """
        Descarga las horas de un solo proyecto.

        Equivale a obtenerHorasClockifyPorProyecto(id, rangoPersonalizado).

        Args:
            internal_id: ID interno del proyecto.
            custom_range: Inicio y fin; si no se da, se usa el rango del
                proyecto (MPB o Historico_Proyectos).

        Returns:
            Los registros del proyecto en el rango.

        Raises:
            ClockifyProjectError: Cuando falta el rango o el proyecto.
        """
        if custom_range is None:
            date_range = ProjectDateRangeResolver(
                self._reader,
                self._today,
            ).resolve(internal_id)
        else:
            date_range = ProjectDateRange(
                custom_range[0],
                custom_range[1],
                "Rango solicitado",
            )

        plan = self._plan_report(internal_id, date_range, self._load_lookups())

        return self._fetch_report(
            plan,
            load_costing_rate_by_resource(self._reader),
        )

    def load_project_hours(self, internal_id: str) -> ProjectHours:
        """
        Horas del proyecto en su rango con el nombre en Clockify.

        Equivale a obtenerHorasClockifyPorProyecto(id) cuando el panel
        tambien muestra proyectoClockify y rango.

        Args:
            internal_id: ID interno del proyecto.

        Returns:
            Los registros, el proyecto de Clockify y el rango.

        Raises:
            ClockifyProjectError: Cuando falta el rango o el proyecto.
        """
        date_range = ProjectDateRangeResolver(
            self._reader,
            self._today,
        ).resolve(internal_id)
        lookups = self._load_lookups()
        plan = self._plan_report(internal_id, date_range, lookups)
        project = next(
            (
                item
                for item in lookups[0]
                if item.project_id == plan.clockify_project_id
            ),
            None,
        )

        return ProjectHours(
            entries=self._fetch_report(
                plan,
                load_costing_rate_by_resource(self._reader),
            ),
            project_name=project.name if project else "",
            date_range=self._effective_range(plan, date_range),
            project_id=plan.clockify_project_id,
        )

    def load_fresh_project_hours(
        self,
        internal_id: str,
    ) -> tuple[ProjectHours, int]:
        """
        Horas del proyecto sin usar la cache (forzarActualizacion).

        Vuelve a listar los proyectos de Clockify, descarga el reporte y
        deja el resultado en la cache para las siguientes consultas.

        Args:
            internal_id: ID interno del proyecto.

        Returns:
            Las horas y el numero de solicitudes al reporte.
        """
        date_range = ProjectDateRangeResolver(
            self._reader,
            self._today,
        ).resolve(internal_id)
        projects = self._load_clockify_projects(force_refresh=True)
        plan = self._plan_report(
            internal_id,
            date_range,
            (projects, load_project_links(self._reader)),
        )
        entries, request_count = self._download_report(
            plan,
            load_costing_rate_by_resource(self._reader),
        )
        cache_key = (
            f"{self._cache_prefix}:report:{plan.clockify_project_id}:"
            f"{plan.internal_id}:{plan.start_date}:{plan.end_date}:cr-v2"
            f"{self._store_stamp}"
        )
        self._cache_store.set(
            cache_key,
            entries,
            report_cache_seconds(bool(entries), plan.end_date, self._today),
        )
        project = next(
            (
                item
                for item in projects
                if item.project_id == plan.clockify_project_id
            ),
            None,
        )
        hours = ProjectHours(
            entries=entries,
            project_name=project.name if project else "",
            date_range=self._effective_range(plan, date_range),
            project_id=plan.clockify_project_id,
        )

        return hours, request_count

    @property
    def workspace_id(self) -> str:
        """ID del workspace configurado."""
        return self._workspace_id

    def create_client(self) -> ClockifyClient:
        """Cliente HTTP nuevo con la API key configurada."""
        return self._client_factory()

    def resolve_range(self, internal_id: str) -> ProjectDateRange:
        """Rango del proyecto (_obtenerRangoDiscoveryDeployment)."""
        return ProjectDateRangeResolver(self._reader, self._today).resolve(
            internal_id,
        )

    def resolve_history_range(self, internal_id: str) -> ProjectDateRange:
        """Rango Discovery -> Deployment de Historico_Proyectos A:I."""
        return ProjectDateRangeResolver(
            self._reader,
            self._today,
        ).resolve_from_history(internal_id)

    def list_clockify_projects(self) -> list[ClockifyProject]:
        """Proyectos del workspace, con cache de una hora."""
        return self._load_clockify_projects()

    def find_clockify_project(
        self,
        internal_id: str,
    ) -> ClockifyProject | None:
        """Proyecto de Clockify del ID interno (_resolverProyectoClockify)."""
        projects, linked_ids = self._load_lookups()

        return resolve_clockify_project(internal_id, projects, linked_ids)

    def load_project_tasks(self, clockify_project_id: str) -> list[JsonObject]:
        """
        Tasks del proyecto de Clockify, con cache de una hora.

        Equivale a _obtenerTasksClockifyProyecto().

        Args:
            clockify_project_id: ID del proyecto en Clockify.

        Returns:
            Tasks con id, name y status.
        """
        cache_key = f"{self._cache_prefix}:tasks:{clockify_project_id}"
        cached_tasks = self._cache_store.get(cache_key)

        if isinstance(cached_tasks, list):
            return cached_tasks

        tasks = self._client_factory().list_project_tasks(
            self._workspace_id,
            clockify_project_id,
        )
        self._cache_store.set(cache_key, tasks, TASKS_CACHE_SECONDS)

        return tasks

    def load_strict_project_report(
        self,
        internal_id: str,
        date_range: tuple[date, date],
        force_refresh: bool,
    ) -> ProjectReport:
        """
        Descarga un proyecto con la coincidencia estricta de Clockify.

        Equivale a obtenerHorasClockifyPorProyecto(id, rango, forzar,
        true), que usa Capacidad instalada. Tiene su propia cache.

        Args:
            internal_id: ID interno del proyecto.
            date_range: Inicio y fin a consultar.
            force_refresh: Ignora la cache de proyectos y del reporte.

        Returns:
            Los registros, el proyecto de Clockify y las solicitudes.

        Raises:
            ClockifyProjectError: Cuando no hay coincidencia unica.
            TimeEntrySourceError: Cuando falla la descarga; el mensaje
                incluye el proyecto de Clockify.
        """
        lookups = (
            self._load_clockify_projects(force_refresh),
            load_project_links(self._reader),
        )
        start_date, end_date = date_range
        plan = self._plan_report(
            internal_id,
            ProjectDateRange(start_date, end_date, "Rango solicitado"),
            lookups,
            strict=True,
        )
        project = next(
            item
            for item in lookups[0]
            if item.project_id == plan.clockify_project_id
        )
        cache_key = (
            f"{self._cache_prefix}:strict_report:{plan.clockify_project_id}"
            f":{plan.internal_id}:{plan.start_date}:{plan.end_date}:cr-v2"
            f"{self._store_stamp}"
        )
        cached_report = self._cache_store.get(cache_key)

        if isinstance(cached_report, ProjectReport) and not force_refresh:
            return cached_report

        try:
            entries, request_count = self._download_report(
                plan,
                load_costing_rate_by_resource(self._reader),
                use_raw_cache=not force_refresh,
            )
        except TimeEntrySourceError as error:
            raise type(error)(
                f"{error.detail} Proyecto: {project.name} "
                f"[{project.project_id}].",
            ) from error

        report = ProjectReport(project, entries, request_count)
        self._cache_store.set(
            cache_key,
            report,
            report_cache_seconds(bool(entries), plan.end_date, self._today),
        )

        return report

    def prefetch_projects(self, internal_ids: list[str]) -> None:
        """
        Descarga en paralelo los proyectos y deja el resultado en cache.

        Los proyectos con error se omiten; el error vuelve a aparecer
        cuando se consulten uno por uno con load_project().

        Args:
            internal_ids: IDs internos a precargar con su rango propio.
        """
        lookups = self._load_lookups()
        range_resolver = ProjectDateRangeResolver(self._reader, self._today)
        plans: list[ReportPlan] = []

        for internal_id in dict.fromkeys(internal_ids):
            try:
                plans.append(
                    self._plan_report(
                        internal_id,
                        range_resolver.resolve(internal_id),
                        lookups,
                    ),
                )
            except TimeEntrySourceError as error:
                logger.info(
                    "Precarga omitida de %s: %s",
                    internal_id,
                    error.detail,
                )

        self._fetch_many(plans, load_costing_rate_by_resource(self._reader))

    def _plan_report(
        self,
        internal_id: str,
        date_range: ProjectDateRange,
        lookups: ProjectLookups,
        strict: bool = False,
    ) -> ReportPlan:
        """Limita los CR compartidos al historico de su ID completo."""
        plan = plan_report(internal_id, date_range, lookups, strict=strict)
        if not plan.task_nomenclature:
            return plan
        history = ProjectDateRangeResolver(
            self._reader, self._today
        ).resolve_from_history(internal_id)
        if history.start_date is None or history.end_date is None:
            raise ClockifyProjectError(
                f"No se encontro el rango de {internal_id} en {history.source}."
            )
        if history.start_date > history.end_date:
            raise ClockifyProjectError(
                f"El periodo historico de {internal_id} tiene "
                "la fecha de inicio posterior a la de fin."
            )
        start = max(plan.start_date, history.start_date)
        finish = min(plan.end_date, history.end_date)
        if start > finish:
            return replace(plan, empty_range=True)
        return ReportPlan(
            internal_id,
            plan.clockify_project_id,
            start,
            finish,
            plan.task_nomenclature,
        )

    @staticmethod
    def _effective_range(
        plan: ReportPlan, original: ProjectDateRange
    ) -> ProjectDateRange:
        """Describe el rango realmente usado por un CR compartido."""
        if plan.task_nomenclature:
            return ProjectDateRange(
                plan.start_date,
                plan.end_date,
                sheet_names.SHEET_PROJECTS_HISTORY,
            )
        return original

    def _load_lookups(self) -> ProjectLookups:
        """Lee los proyectos de Clockify y los vinculos manuales."""
        return (
            self._load_clockify_projects(),
            load_project_links(self._reader),
        )

    def _fetch_many(
        self,
        plans: list[ReportPlan],
        rates: dict[str, float],
    ) -> list[list[TimeEntry] | TimeEntrySourceError]:
        """
        Descarga varios reportes en paralelo.

        Args:
            plans: Descargas pendientes.
            rates: Costing rate por recurso.

        Returns:
            Por cada plan, sus registros o el error que ocurrio.
        """

        def fetch_or_error(
            plan: ReportPlan,
        ) -> list[TimeEntry] | TimeEntrySourceError:
            try:
                return self._fetch_report(plan, rates)
            except TimeEntrySourceError as error:
                return error

        return map_in_parallel(fetch_or_error, plans, MAX_PARALLEL_REPORTS)

    def _load_clockify_projects(
        self,
        force_refresh: bool = False,
    ) -> list[ClockifyProject]:
        """Lee los proyectos del workspace, con cache de una hora.

        La lista (~1,500 proyectos) tarda en leerse de la cache de archivos;
        este cargador la conserva para las consultas siguientes de la misma
        peticion. Una lectura forzada la renueva.
        """
        if self._projects is not None and not force_refresh:
            return self._projects

        cache_key = f"{self._cache_prefix}:projects"
        cached_projects = self._cache_store.get(cache_key)

        if isinstance(cached_projects, list) and not force_refresh:
            self._projects = cached_projects
            return cached_projects

        projects = self._client_factory().list_projects(self._workspace_id)
        self._cache_store.set(cache_key, projects, PROJECTS_CACHE_SECONDS)
        self._projects = projects

        return projects

    def _fetch_report(
        self,
        plan: ReportPlan,
        rates: dict[str, float],
    ) -> list[TimeEntry]:
        """
        Descarga el reporte de un proyecto, con cache de seis horas.

        Crea su propio cliente HTTP para poder ejecutarse en paralelo.

        Args:
            plan: Descarga pendiente.
            rates: Costing rate por recurso.

        Returns:
            Los registros del proyecto.
        """
        if plan.empty_range:
            return []
        cache_key = (
            f"{self._cache_prefix}:report:{plan.clockify_project_id}:"
            f"{plan.internal_id}:{plan.start_date}:{plan.end_date}:cr-v2"
            f"{self._store_stamp}"
        )
        cached_entries = self._cache_store.get(cache_key)

        if isinstance(cached_entries, list):
            return cached_entries

        project_entries, _ = self._download_report(
            plan, rates, use_raw_cache=True
        )
        cache_seconds = report_cache_seconds(
            bool(project_entries),
            plan.end_date,
            self._today,
        )
        self._cache_store.set(cache_key, project_entries, cache_seconds)

        return project_entries

    def _download_report(
        self,
        plan: ReportPlan,
        rates: dict[str, float],
        use_raw_cache: bool = False,
    ) -> tuple[list[TimeEntry], int]:
        """
        Obtiene un reporte y aplica las reglas del proyecto interno.

        Args:
            plan: Descarga pendiente.
            rates: Costing rate por recurso.
            use_raw_cache: Reutiliza los meses entre IDs y rangos. Si es
                falso, vuelve a descargarlos y actualiza la cache mensual.

        Returns:
            Los registros y el numero de solicitudes enviadas.
        """
        if plan.empty_range:
            return [], 0
        report_entries, request_count = self._monthly_report(
            plan, use_raw_cache
        )
        project_entries = [
            build_time_entry_from_report(
                report_entry,
                plan.internal_id,
                rates,
                self._timezone,
            )
            for report_entry in report_entries
        ]
        if plan.task_nomenclature:
            if any(
                entry.task_id and not entry.task_name
                for entry in project_entries
            ):
                task_names = {
                    to_text(task.get("id")): to_text(task.get("name"))
                    for task in self.load_project_tasks(
                        plan.clockify_project_id
                    )
                }
                project_entries = [
                    replace(entry, task_name=task_names.get(entry.task_id, ""))
                    if entry.task_id and not entry.task_name
                    else entry
                    for entry in project_entries
                ]
            project_entries = [
                entry
                for entry in project_entries
                if matches_cr_task(entry.task_name, plan.task_nomenclature)
                and entry.entry_date is not None
                and plan.start_date <= entry.entry_date.date() <= plan.end_date
            ]

        return project_entries, request_count

    def _stored_month(
        self, project_id: str, month: date, use_cache: bool
    ) -> list[JsonObject] | None:
        """Registros del mes desde la base diaria, si esta sincronizado."""
        if not (use_cache and settings.CLOCKIFY_STORE_ENABLED):
            return None
        # Import diferido: los modelos requieren las apps ya cargadas.
        from apps.datastore.services.clockify_store import read_month_rows

        return read_month_rows(project_id, month, self._synced_months)

    def _monthly_report(
        self, plan: ReportPlan, use_cache: bool
    ) -> tuple[list[JsonObject], int]:
        """Reutiliza meses completos y recorta al rango solicitado."""
        month = plan.start_date.replace(day=1)
        result: list[JsonObject] = []
        seen: set[str] = set()
        requests = 0
        client: ClockifyClient | None = None
        # Un mes que aun no empieza no tiene registros: no se consulta.
        while month <= min(plan.end_date, self._today):
            month_end = month.replace(
                day=calendar.monthrange(month.year, month.month)[1]
            )
            # El mes actual crece cada dia: la cobertura es parte de la clave.
            coverage_end = min(month_end, max(self._today, plan.end_date))
            month_key = (
                f"{self._cache_prefix}:raw-month:v1:"
                f"{plan.clockify_project_id}:{REPORT_TIMEZONE}:"
                f"{month}:"
            )
            key = month_key + str(coverage_end)
            full_key = month_key + str(month_end)
            lock = _REPORT_LOCKS[
                int(hashlib.sha256(month_key.encode()).hexdigest()[:8], 16)
                % len(_REPORT_LOCKS)
            ]
            with lock:
                cached: object = self._stored_month(
                    plan.clockify_project_id, month, use_cache
                )
                if isinstance(cached, list):
                    coverage_end = month_end
                elif use_cache:
                    cached = self._cache_store.get(key)
                if not isinstance(cached, list) and use_cache:
                    cached = self._cache_store.get(full_key)
                    if isinstance(cached, list):
                        coverage_end = month_end
                if isinstance(cached, list):
                    rows = cached
                else:
                    if client is None:
                        client = self._client_factory()
                    rows, count = client.fetch_detailed_report_counted(
                        self._workspace_id,
                        plan.clockify_project_id,
                        month,
                        coverage_end,
                        REPORT_TIMEZONE,
                    )
                    requests += count
                    self._cache_store.set(
                        key,
                        rows,
                        monthly_cache_seconds(
                            bool(rows), coverage_end, self._today
                        ),
                    )
            query_start = max(month, plan.start_date)
            query_end = min(coverage_end, plan.end_date)
            if (query_start, query_end) != (month, coverage_end) and any(
                parse_entry_day(
                    (row.get("timeInterval") or {}).get("start"),
                    self._timezone,
                )
                is None
                for row in rows
            ):
                # Sin fecha no podemos recortar un mes con seguridad.
                if client is None:
                    client = self._client_factory()
                rows, count = client.fetch_detailed_report_counted(
                    self._workspace_id,
                    plan.clockify_project_id,
                    query_start,
                    query_end,
                    REPORT_TIMEZONE,
                )
                requests += count
            for row in rows:
                day = parse_entry_day(
                    (row.get("timeInterval") or {}).get("start"),
                    self._timezone,
                )
                if day is not None and not (
                    plan.start_date <= day.date() <= plan.end_date
                ):
                    continue
                entry_id = to_text(row.get("_id") or row.get("id"))
                if entry_id and entry_id in seen:
                    continue
                if entry_id:
                    seen.add(entry_id)
                result.append(row)
            month = month_end + timedelta(days=1)
        return result, requests


def plan_report(
    internal_id: str,
    date_range: ProjectDateRange,
    lookups: ProjectLookups,
    strict: bool = False,
) -> ReportPlan:
    """
    Valida el rango y ubica el proyecto de Clockify de un ID interno.

    Args:
        internal_id: ID interno del proyecto.
        date_range: Rango de fechas a consultar.
        lookups: Proyectos de Clockify y vinculos manuales.
        strict: Conserva la coincidencia estricta salvo el respaldo CR base.

    Returns:
        La descarga pendiente.

    Raises:
        ClockifyProjectError: Cuando falta el rango o el proyecto.
    """
    projects, linked_ids = lookups

    if date_range.start_date is None or date_range.end_date is None:
        raise ClockifyProjectError(
            f"No se encontro el rango de fechas en {date_range.source}.",
        )

    if date_range.start_date > date_range.end_date:
        raise ClockifyProjectError(
            "La fecha de inicio es posterior a la de fin.",
        )

    project = resolve_clockify_project(
        internal_id, projects, linked_ids, strict=strict
    )

    if project is None:
        raise ClockifyProjectError(
            f"No se encontro una coincidencia unica para {internal_id} "
            "en Clockify. "
            f"Vinculalo en la hoja {SHEET_PROJECT_LINKS}.",
        )

    return ReportPlan(
        internal_id=internal_id,
        clockify_project_id=project.project_id,
        start_date=date_range.start_date,
        end_date=date_range.end_date,
        task_nomenclature=(
            cr_nomenclature(internal_id)
            if cr_nomenclature(internal_id)
            and not matches_cr_task(project.name, cr_nomenclature(internal_id))
            else ""
        ),
    )


def collect_project_ids(reader: SheetReader) -> list[str]:
    """
    Junta los IDs de Proyectos y de la hoja Recursos, sin repetir.

    Args:
        reader: Repositorio de lectura de Sheets.

    Returns:
        Los IDs internos en orden de aparicion.
    """
    project_ids = [
        to_text(row.get("ID_Proyecto"))
        for row in reader.read_as_objects(sheet_names.SHEET_PROJECTS)
    ]

    try:
        resource_rows = reader.read_as_objects(sheet_names.SHEET_RESOURCES)
    except SheetNotFoundError:
        logger.warning("No existe la hoja Recursos; solo se usan Proyectos.")
        resource_rows = []

    project_ids.extend(
        to_text(get_flexible_value(row, ["Proyecto"])) for row in resource_rows
    )

    return [
        project_id for project_id in dict.fromkeys(project_ids) if project_id
    ]


def load_project_links(reader: SheetReader) -> dict[str, str]:
    """
    Lee los vinculos manuales ID interno -> ID de proyecto en Clockify.

    En Apps Script vivian en PropertiesService; aqui se leen de la hoja
    opcional Clockify_Vinculos (columnas ID_Proyecto y Clockify_Project_ID).

    Args:
        reader: Repositorio de lectura de Sheets.

    Returns:
        ID interno normalizado -> ID de Clockify.
    """
    if not reader.sheet_exists(SHEET_PROJECT_LINKS):
        return {}

    linked_ids: dict[str, str] = {}

    for row in reader.read_as_objects(SHEET_PROJECT_LINKS):
        internal_id = to_text(get_flexible_value(row, ["ID_Proyecto"]))
        clockify_id = to_text(
            get_flexible_value(row, ["Clockify_Project_ID", "Clockify ID"]),
        ).strip()

        if internal_id and clockify_id:
            linked_ids[normalize_link_key(internal_id)] = clockify_id

    return linked_ids
