"""KPIs de Delivery Managers por mes y trimestre, reconstruidos."""

import calendar
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, replace
from datetime import date, datetime, time

from apps.dashboard.constants import CATEGORY_ACTIVE, CATEGORY_CLOSED
from apps.dashboard.schemas.dashboard_models import PortfolioCosts
from apps.dashboard.schemas.records import ProjectRecord, RiskRecord
from apps.dashboard.services.project_metrics import (
    build_project_metrics,
    calculate_burn_by_project,
)
from apps.dashboard.services.project_status import categorize_project_status
from apps.portal.constants import NO_DELIVERY_MANAGER
from apps.portal.schemas import (
    KpiCut,
    KpiHistory,
    KpiMatrix,
    KpiMatrixRow,
    ProjectView,
)
from apps.portal.services.kpis_dm import build_kpi_view
from apps.portal.services.periods import MONTH_ABBREVIATIONS
from apps.portal.services.portfolio_source import to_project_view
from apps.portal.services.slugs import build_slug
from core.time_entries.models import TimeEntry

"""BKD.120.026 - Historico de KPIs de Delivery Managers
No hay base de datos ni cortes guardados, asi que cada corte se
reconstruye con las hojas y Clockify, con las mismas formulas del corte de
hoy (T, C y salud):
- Avance: horas facturables de Clockify hasta la fecha del corte entre el
  presupuesto del proyecto.
- Retraso y tendencia: contra la fecha fin del proyecto, vistos desde la
  fecha del corte.
- En ejecucion ese dia: el proyecto ya habia iniciado y hoy esta Activo, o
  esta Cerrado y su fecha fin aun no habia pasado. Los proyectos hoy en
  pausa o planificacion no se cuentan en cortes anteriores.
- Riesgos y Delivery Manager: los de hoy (las hojas no guardan historia).
- Trimestre: el corte del ultimo mes del trimestre (el de hoy si sigue en
  curso). Se reconstruye el ano que se elija.
"""

QUARTER_MONTHS = 3
MONTHS_PER_YEAR = 12
END_OF_DAY = time(23, 59, 59)
EMPTY_COSTS = PortfolioCosts({}, {})
Roster = tuple[tuple[str, str], ...]


@dataclass(frozen=True, slots=True)
class HistorySources:
    """Hojas y registros de Clockify que usa el historico."""

    projects: Sequence[ProjectRecord]
    entries: Sequence[TimeEntry]
    risks: Sequence[RiskRecord]
    managers: Mapping[str, str]
    resolve_projects: Callable[[date], Sequence[ProjectRecord]] | None = None
    unavailable_hours: frozenset[str] = frozenset()


def month_cuts(year: int, today: date) -> list[tuple[str, date]]:
    """
    Fechas de corte de enero a diciembre (o al mes en curso) de un ano.

    Args:
        year: Ano a reconstruir.
        today: Fecha de hoy.

    Returns:
        (YYYY-MM, ultimo dia del mes) de cada mes; el actual corta hoy.
    """
    last_month = today.month if year >= today.year else MONTHS_PER_YEAR
    cuts = []

    for month in range(1, last_month + 1):
        last = date(year, month, calendar.monthrange(year, month)[1])
        cuts.append((f"{year}-{month:02d}", min(last, today)))

    return cuts


def build_kpi_history(
    sources: HistorySources,
    now: datetime,
    year: int,
) -> KpiHistory:
    """
    Reconstruye los KPIs de cada mes y trimestre de un ano.

    Args:
        sources: Proyectos, horas, riesgos y Delivery Managers.
        now: Fecha y hora local actual.
        year: Ano a reconstruir.

    Returns:
        Los cortes por mes y por trimestre y los DM que aparecen.
    """
    months = tuple(
        _build_cut(sources, key, cut, now)
        for key, cut in month_cuts(year, now.date())
    )
    quarters = tuple(
        _as_quarter(cut)
        for cut in months
        if int(cut.key[5:7]) % QUARTER_MONTHS == 0 or cut is months[-1]
    )

    return KpiHistory(
        months=months,
        quarters=quarters,
        managers=_managers(months),
    )


def build_matrix(cuts: Sequence[KpiCut], managers: Roster) -> KpiMatrix:
    """
    Ordena los cortes en una tabla: una fila por Delivery Manager.

    Args:
        cuts: Cortes en orden (meses o trimestres).
        managers: (nombre, slug) de los DM a mostrar.

    Returns:
        Encabezados, filas con su KPI por corte y los totales.
    """
    rows = []

    for name, slug in managers:
        cells = tuple(
            next((row for row in cut.view.rows if row.name == name), None)
            for cut in cuts
        )
        rows.append(KpiMatrixRow(name=name, slug=slug, cells=cells))

    return KpiMatrix(
        headers=tuple(
            f"{cut.label}*" if cut.partial else cut.label for cut in cuts
        ),
        partial=tuple(cut.partial for cut in cuts),
        rows=tuple(rows),
        totals=tuple(cut.view.totals if cut.observed else None for cut in cuts),
    )


def _build_cut(
    sources: HistorySources,
    key: str,
    cut: date,
    now: datetime,
) -> KpiCut:
    """KPIs de todos los Delivery Managers a una fecha de corte."""
    is_today = cut >= now.date()
    moment = datetime.combine(cut, END_OF_DAY)
    entries = [
        entry
        for entry in sources.entries
        if entry.entry_date is not None and entry.entry_date.date() <= cut
    ]
    burn = calculate_burn_by_project(entries)
    views: list[ProjectView] = []

    resolved = (
        sources.resolve_projects(cut) if sources.resolve_projects else None
    )
    for project in resolved if resolved is not None else sources.projects:
        at_cut = (
            project
            if resolved is not None or is_today
            else _project_at(project, cut)
        )

        if at_cut is None:
            continue

        metrics = build_project_metrics(
            at_cut,
            burn,
            sources.risks,
            EMPTY_COSTS,
            now if is_today else moment,
        )
        view = to_project_view(metrics, dict(sources.managers))
        if resolved is not None and (
            at_cut.budget_hours <= 0
            or at_cut.project_id in sources.unavailable_hours
        ):
            view = replace(view, progress_percent=None)
        views.append(view)

    return KpiCut(
        key=key,
        label=MONTH_ABBREVIATIONS[int(key[5:7]) - 1].capitalize(),
        cut_label=cut.strftime("%d/%m/%Y"),
        view=build_kpi_view(views),
        partial=is_today,
    )


def _as_quarter(cut: KpiCut) -> KpiCut:
    """El corte de un mes tomado como el de su trimestre."""
    number = (int(cut.key[5:7]) - 1) // QUARTER_MONTHS + 1

    return replace(cut, key=f"{cut.key[:4]}-T{number}", label=f"T{number}")


def _project_at(project: ProjectRecord, cut: date) -> ProjectRecord | None:
    """El proyecto como estaba en ejecucion en el corte, o None."""
    start = project.start_date

    if start is None or start.date() > cut:
        return None

    category = categorize_project_status(project.status)
    end = project.end_date

    if category == CATEGORY_CLOSED:
        if end is None or end.date() < cut:
            return None
    elif category != CATEGORY_ACTIVE:
        return None

    return replace(project, status="Development")


def _managers(months: Sequence[KpiCut]) -> Roster:
    """DM de los cortes: los de hoy primero y luego los que ya no tienen."""
    ordered: dict[str, int] = {}

    for cut in reversed(months):
        for row in cut.view.rows:
            if row.name != NO_DELIVERY_MANAGER and row.total > 0:
                ordered.setdefault(row.name, row.total)

    return tuple(
        (name, build_slug(name))
        for name in sorted(ordered, key=lambda item: (-ordered[item], item))
    )


def chart_series(
    matrix: KpiMatrix,
    limit: int,
) -> dict[str, object]:
    """
    Datos de la grafica de C por mes de los DM con mas proyectos.

    Args:
        matrix: Tabla por mes.
        limit: Cantidad maxima de Delivery Managers.

    Returns:
        Etiquetas y una serie de C (%) por Delivery Manager.
    """
    eligible = [
        row
        for row in matrix.rows
        if any(
            first is not None
            and second is not None
            and first.total > 0
            and second.total > 0
            and first.time_cost.cost_percent is not None
            and second.time_cost.cost_percent is not None
            for first, second in zip(row.cells, row.cells[1:], strict=False)
        )
    ]
    return {
        "labels": list(matrix.headers),
        "series": [
            {
                "name": row.name,
                "values": [
                    cell.time_cost.cost_percent
                    if cell and cell.total > 0
                    else None
                    for cell in row.cells
                ],
            }
            for row in eligible[:limit]
        ],
    }
