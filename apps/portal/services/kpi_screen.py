"""KPIs de Delivery Managers: contexto de la pantalla desde una consulta.

No lee la petición, el reloj ni la base: recibe la consulta, la fecha de
hoy y las cuatro lecturas (`KpiSources`). Se puede llamar igual desde la
vista actual y desde el módulo de Genesis, y se prueba sin cliente HTTP.
"""

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field, replace
from datetime import date
from typing import TypedDict

from apps.portal.schemas import KpiMatrix, KpiView, Period, PeriodPicker
from apps.portal.services.eva_cut import read_cut
from apps.portal.services.kpi_dm_store import StoredKpiCut
from apps.portal.services.kpi_eva import select_managers
from apps.portal.services.kpi_history import build_matrix
from apps.portal.services.kpi_history_loader import KpiHistoryLoad
from apps.portal.services.kpi_quarterly import (
    AverageMatrix,
    build_quarter_averages,
)
from apps.portal.services.period_filter import build_picker, parse_period

FIRST_YEAR = 2021
INVALID_QUERY = "Selecciona una fecha de corte no futura y un año válido."


class KpiQueryError(ValueError):
    """La consulta trae un mes, un corte o un año que no se puede atender."""


@dataclass(frozen=True, slots=True)
class KpiQuery:
    """Parámetros de la pantalla, en el texto que llegan."""

    month: str = ""
    cut: str = ""
    history_year: str = ""
    year: str = ""
    chart_year: str = ""
    managers: tuple[str, ...] = ()
    params: Mapping[str, Sequence[str]] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class KpiSources:
    """Las lecturas que necesita la pantalla; la vista las inyecta."""

    load_history: Callable[[int], KpiHistoryLoad]
    latest_cut: Callable[[], date | None]
    load_cut: Callable[[date], StoredKpiCut]
    monthly_cut: Callable[[date], date]


class KpiContext(TypedDict, total=False):
    """Claves que consume el serializador de la API y la página."""

    period: Period
    picker: PeriodPicker
    kpis: KpiView
    cut_label: str
    cut_is_current: bool
    cut_available: bool
    history_error: str
    history_notice: str
    kpi_storage: dict[str, str | None]
    kpi_filters: dict[str, object]
    month_matrix: KpiMatrix
    quarter_matrix: AverageMatrix
    chart: dict[str, object]


def _resolve(
    query: KpiQuery, today: date, sources: KpiSources, latest: date | None
) -> tuple[date, date, int, int]:
    try:
        if query.month:
            month = date.fromisoformat(query.month + "-01")
            if month > today.replace(day=1) or month.year < FIRST_YEAR:
                raise ValueError("Mes inválido")
            cut = sources.monthly_cut(month)
        else:
            cut = read_cut(query.cut or (latest or today).isoformat(), today)
            month = cut.replace(day=1)
        history_year = int(query.history_year or query.year or today.year)
        chart_year = int(query.chart_year or history_year)
        if not all(
            FIRST_YEAR <= year <= today.year
            for year in (history_year, chart_year)
        ):
            raise ValueError("Año inválido")
    except ValueError as exc:
        raise KpiQueryError(INVALID_QUERY) from exc
    return cut, month, history_year, chart_year


def _only(load: KpiHistoryLoad, managers: Sequence[str]) -> KpiHistoryLoad:
    if load.history is None or not managers:
        return load
    return replace(
        load,
        history=replace(
            load.history,
            months=tuple(
                replace(month, view=select_managers(month.view, managers))
                for month in load.history.months
            ),
            managers=tuple(
                item for item in load.history.managers if item[0] in managers
            ),
        ),
    )


def _chart(history: KpiHistoryLoad) -> dict[str, object] | None:
    if history.history is None:
        return None
    matrix = build_matrix(history.history.months, history.history.managers)
    return {
        "labels": list(matrix.headers),
        "series": [
            {
                "name": row.name,
                "values": [
                    cell.time_cost.cost_percent if cell and cell.total else None
                    for cell in row.cells
                ],
            }
            for row in matrix.rows
        ],
    }


def build_kpi_context(
    query: KpiQuery, today: date, sources: KpiSources
) -> KpiContext:
    """Resumen del corte, historia anual y gráfica.

    Lanza `KpiQueryError` si la consulta no es válida.
    """
    latest = sources.latest_cut()
    cut, month, history_year, chart_year = _resolve(
        query, today, sources, latest
    )
    period = parse_period({"periodo": "anio", "anio": str(history_year)}, today)
    annual = sources.load_history(history_year)
    chart_history = (
        annual
        if chart_year == history_year
        else sources.load_history(chart_year)
    )
    selected = sources.load_cut(cut)
    summary = selected.view
    names = sorted(
        {row.name for row in summary.rows}
        | {
            name
            for load in (annual, chart_history)
            if load.history
            for name, _ in load.history.managers
        }
    )
    annual, chart_history = (
        _only(annual, query.managers),
        _only(chart_history, query.managers),
    )
    observation = selected.observation
    missing = (
        f" No hay una captura KPI guardada para {cut:%d/%m/%Y}."
        if observation is None
        else ""
    )
    context = KpiContext(
        period=period,
        picker=build_picker(period, today, query.params),
        kpis=select_managers(summary, query.managers),
        cut_label=cut.strftime("%d/%m/%Y"),
        cut_is_current=cut == today,
        cut_available=observation is not None,
        history_error=annual.error,
        history_notice=annual.notice + missing,
        kpi_storage={
            "latest_cut": latest.isoformat() if latest else None,
            "selected_status": observation.period.status
            if observation
            else "missing",
        },
        kpi_filters={
            "month": month.strftime("%Y-%m"),
            "max_month": today.strftime("%Y-%m"),
            "cut": cut.isoformat(),
            "max_cut": today.isoformat(),
            "history_year": history_year,
            "chart_year": chart_year,
            "years": list(range(today.year, FIRST_YEAR - 1, -1)),
            "managers": names,
            "selected_managers": list(query.managers),
        },
    )
    if annual.history is not None:
        context["month_matrix"] = build_matrix(
            annual.history.months, annual.history.managers
        )
        context["quarter_matrix"] = build_quarter_averages(
            annual.history.months, annual.history.managers
        )
    chart = _chart(chart_history)
    if chart is not None:
        context["chart"] = chart
    return context
