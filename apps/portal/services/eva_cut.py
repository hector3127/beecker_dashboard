"""EVA 1 at a local calendar cut, reconstructed from dated source records.

This is not a stored copy of the original email. Current Azure work items
must never be presented as their historical state.
"""

from collections.abc import Callable, Sequence
from dataclasses import replace
from datetime import date, datetime
from typing import Any

from django.utils import timezone

from apps.clockify.provider import build_clockify_loader
from apps.clockify.services.time_entry_loader import ClockifyTimeEntryLoader
from apps.ejecutivo.services.ixb_history import resolve_history_period
from apps.ejecutivo.services.ixb_rules import (
    CLOSED_PROJECT_STATES,
    HISTORY_FINISH_COLUMNS,
    HISTORY_START_COLUMNS,
    read_history_date,
    read_history_id,
    read_history_status,
    read_project_id,
)
from apps.ejecutivo.services.ixb_summary import IxbSources, build_ixb_summary
from apps.ejecutivo.services.project_dashboard import build_history_block_rows
from apps.portal.constants import EVA2_STATUS_COLUMNS
from apps.portal.schemas import Eva2View
from apps.portal.services.eva2 import _pivot_rows, build_eva2_view
from apps.portal.services.time_cost import build_time_cost
from core.exceptions import DashboardError
from core.sheets.factory import build_sheet_repository
from core.time_entries.models import TimeEntry
from core.utils.dates import to_datetime


def cut_rows(
    projects: Sequence[dict[str, Any]],
    history: Sequence[dict[str, Any]],
    cut: date,
    entries: Callable[[str], list[TimeEntry]],
) -> list[dict[str, Any]]:
    """Select open exact IDs, including suspended/overdue and retired IDs.

    A terminal event on the cut day is considered closed at end of day.
    DM comes from the latest dated event on/before the cut for that exact ID.
    A:I event rows and their J budgets must not be confused with K: metadata.
    """
    catalog = {
        read_project_id(row).casefold(): dict(row)
        for row in projects
        if read_project_id(row)
    }
    events: dict[str, list[dict[str, Any]]] = {}
    for row in history:
        pid = read_history_id(row)
        if pid:
            events.setdefault(pid.casefold(), []).append(row)
    selected, pending_budget = [], set()
    for key, own in events.items():
        terminal = [
            row
            for row in own
            if read_history_status(row) in CLOSED_PROJECT_STATES
        ]
        if any(
            (
                day := read_history_date(row, HISTORY_FINISH_COLUMNS)
                or read_history_date(row, HISTORY_START_COLUMNS)
            )
            is None
            or day <= cut
            for row in terminal
        ):
            continue
        if not resolve_history_period(own, read_history_id(own[0]), cut).active:
            continue
        dated = [
            row
            for row in own
            if (day := read_history_date(row, HISTORY_START_COLUMNS))
            is not None
            and day <= cut
        ]
        dated.sort(
            key=lambda row: (
                read_history_date(row, HISTORY_START_COLUMNS) or date.min
            )
        )
        source = catalog.get(key, {})
        row = dict(source)
        row["ID_Proyecto"] = read_history_id(own[0])
        for target, field in (
            ("Servicio", "Service"),
            ("Nombre", "Project Name"),
            ("Cliente", "Account"),
        ):
            value = next(
                (
                    str(event.get(field) or "").strip()
                    for event in reversed(dated)
                    if str(event.get(field) or "").strip()
                ),
                "",
            )
            if value:
                row[target] = value
        manager = next(
            (
                str(event.get("Delivery Manager") or "").strip()
                for event in reversed(dated)
                if str(event.get("Delivery Manager") or "").strip()
            ),
            "Sin asignar",
        )
        row["Delivery Manager"] = manager
        # Historical stage budgets are repeated, not additive. Use the last
        # recorded value, never sum Discovery/Development/Deployment copies.
        budget = next(
            (
                event["Budget  (Hrs)"]
                for event in reversed(dated)
                if event.get("Budget  (Hrs)") not in (None, "")
            ),
            source.get("Budget_Hrs"),
        )
        row["Budget_Hrs"] = budget
        if budget in (None, ""):
            pending_budget.add(key)
        selected.append(row)

    pending_hours: set[str] = set()

    def through_cut(pid: str) -> list[TimeEntry]:
        try:
            loaded = entries(pid)
        except DashboardError:
            pending_hours.add(pid.casefold())
            return []
        if any(entry.entry_date is None for entry in loaded):
            pending_hours.add(pid.casefold())
        return [
            entry
            for entry in loaded
            if entry.entry_date is not None
            and (day := to_datetime(entry.entry_date)) is not None
            and day.date() <= cut
        ]

    # Override the legacy first-match DM lookup with the dated exact-ID result.
    dated_managers = [
        {
            "Project ID": row["ID_Proyecto"],
            "Delivery Manager": row["Delivery Manager"],
        }
        for row in selected
    ]
    sources = IxbSources(selected, list(history), through_cut, None)
    rows: list[dict[str, Any]] = build_ixb_summary(
        sources, datetime.combine(cut, datetime.min.time())
    )["filas"]
    managers = {
        r["Project ID"].casefold(): r["Delivery Manager"]
        for r in dated_managers
    }
    for row in rows:
        key = row["idProyecto"].casefold()
        row["deliveryManager"] = managers[key]
        row["budget_pending"] = key in pending_budget
        row["hours_pending"] = key in pending_hours
    return rows


def load_cut(cut: date) -> dict[str, Any]:
    """Load source data without changing other EVA/Operations loaders."""
    try:
        reader = build_sheet_repository()
        values = reader.read_values("Historico_Proyectos")
        history = build_history_block_rows(values, [])
        # J belongs to the A:I event record. K onward is a different table.
        event_values = [
            row
            for row in values[1:]
            if any(cell not in (None, "") for cell in row[:9])
        ]
        for event, raw in zip(history, event_values, strict=True):
            event["Budget  (Hrs)"] = raw[9] if len(raw) > 9 else ""
        loader: ClockifyTimeEntryLoader | None = None

        def entries(pid: str) -> list[TimeEntry]:
            nonlocal loader
            if loader is None:
                loader = build_clockify_loader(reader)
            starts = [
                day
                for row in history
                if read_history_id(row).casefold() == pid.casefold()
                and (day := read_history_date(row, HISTORY_START_COLUMNS))
                is not None
                and day <= cut
            ]
            return loader.load_project(pid, custom_range=(min(starts), cut))

        rows = cut_rows(
            reader.read_as_objects("Proyectos"), history, cut, entries
        )
        view = build_eva2_view(rows)
        flags = {row["idProyecto"]: row for row in rows}
        view = replace(
            view,
            projects=tuple(
                replace(
                    p,
                    budget_pending=flags[p.project_id]["budget_pending"],
                    hours_pending=flags[p.project_id]["hours_pending"],
                    azure_pending=True,
                )
                for p in view.projects
            ),
        )
        return {"eva": view, "error": ""}
    except DashboardError as error:
        return {"eva": build_eva2_view([]), "error": error.build_message()}


def read_cut(value: str) -> date:
    """Only ISO days up to today; invalid/future input is a validation error."""
    parsed = date.fromisoformat(value)
    if parsed.isoformat() != value or parsed > timezone.localdate():
        raise ValueError("Fecha de corte inválida")
    return parsed


def select_view(view: Eva2View, manager: str, service: str) -> Eva2View:
    """All visible summaries use the same DM/service selection as the table."""
    projects = tuple(
        p
        for p in view.projects
        if (not manager or p.manager == manager)
        and (not service or p.service == service)
    )
    services, service_totals = _pivot_rows(
        projects, view.services, lambda p: p.service
    )
    statuses, status_totals = _pivot_rows(
        projects,
        tuple(code for code, _ in EVA2_STATUS_COLUMNS),
        lambda p: p.status_code,
    )
    suspended = [p for p in projects if p.status_code == "sus"]
    return replace(
        view,
        projects=projects,
        total_projects=len(projects),
        service_rows=services,
        service_totals=service_totals,
        status_rows=statuses,
        status_totals=status_totals,
        suspended_count=len(suspended),
        suspended_note=" · ".join(
            f"{p.project_id} · {p.name}" for p in suspended
        ),
        time_cost=build_time_cost(
            (p.deviation_days for p in projects),
            (
                p.progress
                for p in projects
                if not p.budget_pending and not p.hours_pending
            ),
        ),
    )
