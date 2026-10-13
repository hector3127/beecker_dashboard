"""Vigencia por nomenclatura desde Historico_Proyectos."""

import re
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, datetime

from apps.ejecutivo.services.ixb_rules import (
    COMPLETED_STATES,
    HISTORY_FINISH_COLUMNS,
    HISTORY_START_COLUMNS,
    SUSPENDED_STATES,
    read_history_date,
    read_history_id,
    read_history_status,
)
from core.utils.cell_types import SheetRow


@dataclass(slots=True)
class HistoryPeriod:
    """Vigencia, estado y fechas de una nomenclatura segun el historico."""

    active: bool = False
    status: str = "Pendiente"
    start: datetime | None = None
    finish: datetime | None = None
    closed_stages: dict[str, bool] | None = None


def resolve_history_period(
    rows: Sequence[SheetRow],
    project_id: str,
    today: date,
) -> HistoryPeriod:
    """Cada ID usa solo su historial; hoy se incluye hasta terminar el dia."""
    events = []
    for row in rows:
        if read_history_id(row).casefold() != project_id.strip().casefold():
            continue
        status = read_history_status(row)
        start = read_history_date(row, HISTORY_START_COLUMNS)
        finish = read_history_date(row, HISTORY_FINISH_COLUMNS)
        events.append((status, start, finish))

    completed = [
        day
        for status, start, finish in events
        if status in COMPLETED_STATES and (day := finish or start) is not None
    ]
    if any(day < today for day in completed):
        return HistoryPeriod()

    phases = [
        (
            re.sub(r"\s+(EST|OP)$", "", status),
            start,
            finish,
            status.endswith(" EST"),
        )
        for status, start, finish in events
        if status not in COMPLETED_STATES | SUSPENDED_STATES and start
    ]
    real = [event for event in phases if not event[3]]
    planned = [event for event in phases if event[3]]
    started = [event for event in real if event[1] <= today]
    # Si hay ejecucion real, un plan anterior no adelanta su inicio.
    if not real:
        started = [event for event in planned if event[1] <= today]
    suspensions = [
        (start, finish)
        for name, start, finish in events
        if name in SUSPENDED_STATES
        and start
        and start <= today
        and (finish is None or today <= finish)
    ]
    if not started:
        if not suspensions:
            return HistoryPeriod()
        first_start = min(start for start, _ in suspensions)
        return HistoryPeriod(
            active=True,
            status="Suspendido",
            start=datetime.combine(first_start, datetime.min.time()),
            closed_stages={
                name: False
                for name in ("discovery", "development", "deployment")
            },
        )

    current = max(started, key=lambda event: event[1])
    labels = {
        "DISCOVERY": "Discovery",
        "DEVELOPMENT": "Development",
        "DEPLOYMENT": "Deployment",
    }
    status = labels.get(current[0], current[0].capitalize())
    if suspensions and max(start for start, _ in suspensions) >= current[1]:
        status = "Suspendido"

    starts = [event[1] for event in (real or planned)]
    deployment = [event for event in real if event[0] == "DEPLOYMENT"]
    if not deployment:
        deployment = [event for event in planned if event[0] == "DEPLOYMENT"]
    last_deployment = (
        max(deployment, key=lambda event: event[1]) if deployment else None
    )
    finish = last_deployment[2] if last_deployment else None
    closed = {}
    for name in labels:
        phase_events = [
            event for event in (real or planned) if event[0] == name
        ]
        last = (
            max(phase_events, key=lambda event: event[1])
            if phase_events
            else None
        )
        closed[name.lower()] = bool(last and last[2] and last[2] < today)
    return HistoryPeriod(
        active=True,
        status=status,
        start=datetime.combine(min(starts), datetime.min.time()),
        finish=datetime.combine(finish, datetime.min.time())
        if finish
        else None,
        closed_stages=closed,
    )
