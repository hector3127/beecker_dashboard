"""Carga del historico de KPIs con cache corta y errores controlados."""

import hashlib
import logging
from dataclasses import dataclass, replace

from django.conf import settings
from django.core.cache import cache
from django.utils import timezone

from apps.clockify.provider import build_clockify_loader
from apps.clockify.services.cr_hours import cr_nomenclature
from apps.dashboard.schemas.records import ProjectRecord
from apps.dashboard.services.record_reader import read_risk_records
from apps.portal.constants import (
    KPI_HISTORY_CACHE_KEY,
    KPI_HISTORY_CACHE_SECONDS,
)
from apps.portal.schemas import KpiHistory
from apps.portal.services.kpi_history import (
    HistorySources,
    build_kpi_history,
    month_cuts,
)
from apps.portal.services.kpi_sources import KpiSheetReader, load_kpi_sources
from core.exceptions import DashboardError
from core.sheets.factory import build_sheet_repository
from core.time_entries.factory import build_time_entry_provider
from core.time_entries.models import TimeEntry
from core.utils.parallel import map_in_parallel

"""BKD.120.027 - Cargador del historico de KPIs
Lee MPB para AER/T&M, Historico_Proyectos para otros servicios, Riesgos
y las horas de Clockify. No consulta Proyectos; guarda solo cache local. El
resultado correcto se guarda 10 minutos; un error se regresa como texto.
"""

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class KpiHistoryLoad:
    """Historico de KPIs y el motivo si no se pudo reconstruir."""

    history: KpiHistory | None
    error: str = ""
    notice: str = ""


def load_kpi_history(year: int | None = None) -> KpiHistoryLoad:
    """
    Reconstruye los KPIs por mes y trimestre de un ano.

    Args:
        year: Ano a reconstruir; el actual si no se indica.

    Returns:
        El historico, o None con el motivo si una fuente fallo.
    """
    now = timezone.localtime().replace(tzinfo=None)
    chosen = year or now.year
    key = f"{KPI_HISTORY_CACHE_KEY}:{chosen}"
    cached = cache.get(key)

    if isinstance(cached, KpiHistoryLoad):
        return cached
    if isinstance(cached, KpiHistory):
        return KpiHistoryLoad(history=cached)

    try:
        reader = build_sheet_repository()
        reader.prefetch(["MPB", "Historico_Proyectos", "Riesgos"])
        sources = load_kpi_sources(reader, now.date())
        inventory: dict[str, ProjectRecord] = {}
        for _, cut in month_cuts(chosen, now.date()):
            for project in sources.at(cut):
                if project.start_date is None:
                    continue
                previous = inventory.get(project.project_id)
                if previous is not None and previous.start_date is not None:
                    project = replace(
                        project,
                        start_date=min(previous.start_date, project.start_date),
                        end_date=max(previous.end_date, project.end_date)
                        if previous.end_date and project.end_date
                        else None,
                    )
                inventory[project.project_id] = project
        projects = list(inventory.values())
        scoped = KpiSheetReader(reader, projects)
        failures: dict[str, str] = {}
        if settings.TIME_ENTRY_SOURCE != "clockify":
            entries = (
                build_time_entry_provider(scoped).load_time_entries().entries
            )
        else:
            signature = hashlib.sha256(
                repr(
                    (
                        settings.GOOGLE_SPREADSHEET_ID,
                        chosen,
                        now.date(),
                        projects,
                    )
                ).encode()
            ).hexdigest()
            hours_key = "portal:kpi-source-hours:v2:" + signature
            hours_snapshot = cache.get(hours_key)
            if hours_snapshot is not None:
                entries, failures = hours_snapshot
            else:
                scoped.prefetch(
                    [
                        "Recursos",
                        "Banda salarial",
                        "Master rates",
                        "Clockify_Vinculos",
                    ]
                )

                def load(project: ProjectRecord) -> tuple[list[TimeEntry], str]:
                    assert project.start_date is not None
                    end = min(
                        project.end_date.date()
                        if project.end_date
                        else now.date(),
                        now.date(),
                    )
                    if end < project.start_date.date():
                        return [], (
                            "Inicio "
                            + project.start_date.strftime("%d/%m/%Y")
                            + " posterior al fin "
                            + end.strftime("%d/%m/%Y")
                        )
                    try:
                        return build_clockify_loader(scoped).load_project(
                            project.project_id, (project.start_date.date(), end)
                        ), ""
                    except DashboardError as error:
                        return [], error.build_message()

                outcomes = list(
                    zip(
                        projects,
                        map_in_parallel(load, projects, max_workers=2),
                        strict=True,
                    )
                )
                outcomes.sort(
                    key=lambda pair: bool(cr_nomenclature(pair[0].project_id)),
                    reverse=True,
                )
                unique: dict[str | tuple[str, int], TimeEntry] = {}
                for project, (records, error) in outcomes:
                    if error:
                        failures[project.project_id] = error
                    for index, record in enumerate(records):
                        unique.setdefault(
                            record.entry_id or (project.project_id, index),
                            record,
                        )
                entries = tuple(unique.values())
                cache.set(
                    hours_key,
                    (entries, failures),
                    60 if failures else KPI_HISTORY_CACHE_SECONDS,
                )
        history = build_kpi_history(
            HistorySources(
                projects=projects,
                entries=entries,
                risks=read_risk_records(reader),
                managers=sources.managers,
                resolve_projects=sources.at,
                unavailable_hours=frozenset(failures),
            ),
            now,
            chosen,
        )
    except DashboardError as error:
        logger.warning("No se pudo reconstruir el historico: %s", error)

        return KpiHistoryLoad(history=None, error=error.build_message())

    notice = ""
    if failures:
        notice = (
            "C parcial: los promedios solo incluyen proyectos con presupuesto "
            "y horas disponibles. "
            "Sin horas verificadas: "
            + "; ".join(pid + ": " + error for pid, error in failures.items())
        )
    result = KpiHistoryLoad(history=history, notice=notice)
    cache.set(key, result, 60 if failures else KPI_HISTORY_CACHE_SECONDS)
    return result
