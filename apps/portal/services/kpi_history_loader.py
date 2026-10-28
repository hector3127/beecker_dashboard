"""DM compliance reconstructed from the same exact-ID inventory as EVA 1."""

from dataclasses import dataclass
from datetime import datetime

from django.conf import settings
from django.core.cache import cache
from django.utils import timezone

from apps.clockify.provider import build_clockify_loader
from apps.dashboard.schemas.records import ProjectRecord
from apps.portal.constants import (
    KPI_HISTORY_CACHE_KEY,
    KPI_HISTORY_CACHE_SECONDS,
)
from apps.portal.schemas import KpiHistory
from apps.portal.services.eva_cut import cut_rows, read_sources
from apps.portal.services.kpi_eva import build_eva_history, monthly_cuts
from apps.portal.services.kpi_sources import KpiSheetReader
from core.exceptions import DashboardError
from core.sheets.factory import build_sheet_repository
from core.time_entries.factory import build_time_entry_provider
from core.time_entries.models import TimeEntry
from core.utils.dates import to_datetime
from core.utils.text import extract_base_id


@dataclass(frozen=True, slots=True)
class KpiHistoryLoad:
    """Monthly history and explicit source failures/pending percentages."""

    history: KpiHistory | None
    error: str = ""
    notice: str = ""


def load_kpi_history(year: int | None = None) -> KpiHistoryLoad:
    """Reuse each project's hours across all monthly cuts, never Azure today."""
    now = timezone.localtime().replace(tzinfo=None)
    chosen = year or now.year
    cuts = monthly_cuts(chosen, now.date())
    if not cuts:
        return KpiHistoryLoad(
            None, "Aún no hay un corte de lunes a jueves en el periodo."
        )
    key = f"{KPI_HISTORY_CACHE_KEY}:eva1-compliance-v1:{chosen}:{now.date()}"
    cached = cache.get(key)
    if isinstance(cached, KpiHistoryLoad):
        return cached
    try:
        reader = build_sheet_repository()
        reader.prefetch(["Proyectos", "Historico_Proyectos"])
        projects, events = read_sources(reader)
        inventory: dict[str, ProjectRecord] = {}
        for _, cut, _ in cuts:
            for row in cut_rows(projects, events, cut, lambda pid: []):
                pid = row["idProyecto"]
                start = to_datetime(row["fechaInicio"])
                previous = inventory.get(pid)
                if (
                    previous is not None
                    and previous.start_date is not None
                    and start is not None
                ):
                    start = min(start, previous.start_date)
                inventory[pid] = ProjectRecord(
                    pid,
                    row["nombre"],
                    row["cliente"],
                    row["status"],
                    row["servicio"],
                    row["budget"],
                    start,
                    datetime.combine(cuts[-1][1], datetime.min.time()),
                )
        scoped = KpiSheetReader(reader, list(inventory.values()))
        all_entries = None
        if settings.TIME_ENTRY_SOURCE != "clockify":
            all_entries = (
                build_time_entry_provider(scoped).load_time_entries().entries
            )
        loaded: dict[str, list[TimeEntry]] = {}
        failed: dict[str, DashboardError] = {}

        def entries(pid: str) -> list[TimeEntry]:
            if pid in failed:
                raise failed[pid]
            if pid not in loaded:
                if all_entries is not None:
                    loaded[pid] = [
                        e
                        for e in all_entries
                        if extract_base_id(e.project_id).casefold()
                        == extract_base_id(pid).casefold()
                    ]
                else:
                    record = inventory[pid]
                    assert record.start_date is not None
                    try:
                        loaded[pid] = build_clockify_loader(
                            scoped
                        ).load_project(
                            pid, (record.start_date.date(), cuts[-1][1])
                        )
                    except DashboardError as error:
                        failed[pid] = error
                        raise
            return loaded[pid]

        history = build_eva_history(
            chosen, now, lambda cut: cut_rows(projects, events, cut, entries)
        )
    except DashboardError as error:
        return KpiHistoryLoad(None, error.build_message())
    pending = any(
        row.time_cost.time_days is None or row.time_cost.cost_percent is None
        for cut in history.months
        for row in cut.view.rows
    )
    notice = ""
    if pending:
        notice = (
            "T/C pendientes donde falta fecha Finish, presupuesto válido "
            "u horas verificadas. TP conserva todos los proyectos del corte; "
            "no se reduce el denominador."
        )
    if failed:
        notice += " Sin horas verificadas: " + "; ".join(
            pid + ": " + err.build_message() for pid, err in failed.items()
        )
    result = KpiHistoryLoad(history, notice=notice)
    cache.set(key, result, 60 if pending else KPI_HISTORY_CACHE_SECONDS)
    return result
