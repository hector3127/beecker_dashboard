"""Quarterly presentation averages monthly cuts, as in the GSE workbook."""

from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass

from apps.portal.schemas import KpiCut, KpiManagerRow, TimeCost
from apps.portal.services.kpi_history import Roster


@dataclass(frozen=True)
class AverageCell:
    """Monthly means retained before display rounding."""

    total: float
    time_cost: TimeCost


@dataclass(frozen=True)
class AverageRow:
    """One manager across the available quarters."""

    name: str
    slug: str
    cells: tuple[AverageCell | None, ...]


@dataclass(frozen=True)
class AverageMatrix:
    """Quarter headers, manager rows and averages of monthly totals."""

    headers: tuple[str, ...]
    rows: tuple[AverageRow, ...]
    totals: tuple[AverageCell | None, ...]


def _average(values: Sequence[float | int | None]) -> float | None:
    known = [value for value in values if value is not None]
    return sum(known) / len(known) if known else None


def _cell(rows: Sequence[KpiManagerRow]) -> AverageCell | None:
    if not rows:
        return None
    return AverageCell(
        total=sum(row.total for row in rows) / len(rows),
        time_cost=TimeCost(
            time_days=_average([row.time_cost.time_days for row in rows]),
            cost_percent=_average([row.time_cost.cost_percent for row in rows]),
        ),
    )


def build_quarter_averages(
    cuts: Sequence[KpiCut], managers: Roster
) -> AverageMatrix:
    """Average known monthly cells without inventing zeroes for absence."""
    groups: dict[int, list[KpiCut]] = defaultdict(list)
    for cut in cuts:
        groups[(int(cut.key[5:7]) - 1) // 3 + 1].append(cut)
    quarters = [groups[key] for key in sorted(groups)]
    return AverageMatrix(
        headers=tuple(
            f"T{key}"
            + (
                "*"
                if len(groups[key]) < 3 or any(c.partial for c in groups[key])
                else ""
            )
            for key in sorted(groups)
        ),
        rows=tuple(
            AverageRow(
                name,
                slug,
                tuple(
                    _cell(
                        [
                            row
                            for cut in group
                            for row in cut.view.rows
                            if row.name == name
                        ]
                    )
                    for group in quarters
                ),
            )
            for name, slug in managers
        ),
        totals=tuple(
            _cell([cut.view.totals for cut in group]) for group in quarters
        ),
    )
