"""Exact scope allocation and EVA rows using only provider evidence."""

import re
from datetime import date
from decimal import Decimal
from typing import Any
from zoneinfo import ZoneInfo

from apps.clockify.constants import REPORT_TIMEZONE
from apps.ejecutivo.services.azure_stages import (
    CLOSED_WORK_ITEM_STATES,
    STAGES,
    empty_work_item_counts,
    stage_from_path,
)
from apps.portal.services.eva_azure_source import financials
from core.utils.dates import to_datetime

Json = dict[str, Any]
TERMINAL = {"CLOSED", "COMPLETED", "CANCELLED", "CANCELED", "REMOVED"}
SUSPENDED = {"SUSPENDED", "SUSPENDIDO", "ON HOLD", "PAUSED"}
TOKEN = re.compile(
    r"(?:^|[^A-Z0-9])(CR\d*(?:_S\d+)?|S\d+)(?=$|[^A-Z0-9])", re.I
)


def scope_tokens(text: str) -> set[str]:
    """Recognize boundary-delimited scope codes, preserving compound CRs."""
    return {m[1].upper() for m in TOKEN.finditer(text)}


def item_fields(item: Json) -> Json:
    """Read a provider work item's fields."""
    return item.get("fields") or {}


def resolve_scope(
    candidate: Json, iterations: list[Json], siblings: list[Json]
) -> str:
    """Resolve exact roots; aliases require unique matching date evidence."""
    roots = {
        p.split("\\")[1]
        for i in iterations
        if len((p := str(i.get("path", ""))).split("\\")) > 1
    }
    available = {token for root in roots for token in scope_tokens(root)}
    code = candidate["scope"]
    if code in available:
        return code
    if code.endswith("_S1") and code[:-3] in available:
        return code[:-3]
    if code == "BASE" and available == {"S1"} and len(siblings) == 1:
        return "S1"
    # Some sources call the first CR "CR1", while their tree says "CR".
    # Require both dates to match; do not infer it from numbering alone.
    if code in {"CR1", "CR1_S1"} and "CR" in available:
        starts, ends = [], []
        for iteration in iterations:
            if "CR" not in scope_tokens(str(iteration.get("path", ""))):
                continue
            start = to_datetime(iteration.get("fechaInicio"))
            end = to_datetime(iteration.get("fechaFin"))
            if start:
                starts.append(start.date().isoformat())
            if end:
                ends.append(end.date().isoformat())
        if (
            starts
            and ends
            and candidate["start"] == min(starts)
            and candidate["finish"] == max(ends)
        ):
            return "CR"
    return ""


def scoped_items(items: list[Json], scope: str) -> list[Json]:
    """An exact iteration scope; S1 never absorbs CR2_S1 or S10."""
    return [
        i
        for i in items
        if scope_tokens(str(item_fields(i).get("System.IterationPath", "")))
        == {scope}
    ]


def build_row(
    candidate: Json,
    scope: str,
    items: list[Json],
    iterations: list[Json],
    cut: date,
) -> Json:
    """Build counts and status without guessing project closure."""
    fields = candidate["fields"]
    own = scoped_items(items, scope) if scope else []
    roots = [
        item_fields(i)
        for i in own
        if str(item_fields(i).get("System.WorkItemType", "")).upper() == "EPIC"
        and str(item_fields(i).get("System.Title", "")).strip().upper()
        == "GENERAL"
    ]
    states = {str(root.get("System.State", "")).upper() for root in roots}
    status = fields.get("status", "")
    closed = status.upper() in TERMINAL or bool(states) and states <= TERMINAL
    if not status:
        status = "Suspendido" if states & SUSPENDED else "Pendiente"
        if status == "Pendiente":
            for stage in STAGES:
                epics = [
                    item_fields(i)
                    for i in own
                    if str(
                        item_fields(i).get("System.WorkItemType", "")
                    ).upper()
                    == "EPIC"
                    and stage_from_path(
                        str(item_fields(i).get("System.IterationPath", ""))
                    )
                    == stage
                ]
                if any(
                    str(e.get("System.State", "")).upper() not in TERMINAL
                    for e in epics
                ):
                    status = stage
                    break
    if closed:
        status = "Completed"
    counts = empty_work_item_counts()
    for item in own:
        wi = item_fields(item)
        group = (
            stage_from_path(str(wi.get("System.IterationPath", ""))).lower()
            or "general"
        )
        is_closed = (
            str(wi.get("System.State", "")).upper() in CLOSED_WORK_ITEM_STATES
        )
        for target in {"general", group}:
            counts[target]["total"] += 1
            counts[target]["cerrados" if is_closed else "pendientes"] += 1
    stages = {}
    for stage in STAGES:
        ends = [
            to_datetime(i.get("fechaFin"))
            for i in iterations
            if scope_tokens(str(i.get("path", ""))) == {scope}
            and stage_from_path(str(i.get("path", ""))) == stage
        ]
        dates = [end.date() for end in ends if end]
        stages[stage.lower()] = {"cerrada": bool(dates) and max(dates) < cut}
    risks = [
        str(item_fields(i).get("System.Title", ""))
        for i in own
        if str(item_fields(i).get("System.WorkItemType", "")).upper() == "RISK"
        and str(item_fields(i).get("System.State", "")).upper()
        in {"ACTIVE", "PROPOSED"}
    ]
    end = (
        date.fromisoformat(candidate["finish"]) if candidate["finish"] else None
    )
    return {
        "idProyecto": candidate["project_id"],
        "deliveryManager": fields.get("delivery_manager", "Sin asignar"),
        "servicio": fields.get("service", "Pendiente").upper(),
        "nombre": fields.get("project_name", candidate["azure_project"]),
        "cliente": fields.get("client", ""),
        "fechaInicio": candidate["start"],
        "fechaFin": candidate["finish"],
        "budget": float(candidate["budget"])
        if candidate["budget"] is not None
        else None,
        "status": status,
        "closed": closed,
        "desviacionDias": (cut - end).days if end else None,
        "wi": counts,
        "riesgos": risks,
        "etapas": stages,
        "burn": None,
        "etc": None,
        "avance": None,
        "hoursDeviation": None,
        "budget_pending": candidate["budget"] is None,
        "hours_pending": True,
        "azure_pending": not scope or not roots,
        "progress_pending": True,
        "scope": scope,
        "summary_scope": candidate["scope"],
        "source_issues": list(candidate["issues"]),
        "unknown_labels": candidate["unknown_labels"],
    }


def assign_hours(rows: list[Json], entries: list[Json], cut: date) -> None:
    """Assign each billable entry once using exact task/tag plus date range.

    Ambiguous or unclassified entries leave the affected rows pending. An
    untagged entry is usable only if exactly one scope covers its day.
    """
    totals = {id(row): Decimal(0) for row in rows}
    pending: set[int] = set()
    seen: set[str] = set()
    for entry in entries:
        if not entry.get("billable"):
            continue
        key = str(entry.get("_id") or entry.get("id") or "")
        moment = to_datetime((entry.get("timeInterval") or {}).get("start"))
        if not key or not moment:
            pending.update(id(r) for r in rows)
            continue
        if key in seen:
            continue
        seen.add(key)
        day = (
            moment.astimezone(ZoneInfo(REPORT_TIMEZONE)).date()
            if moment.tzinfo
            else moment.date()
        )
        eligible = [
            r
            for r in rows
            if r["fechaInicio"]
            and r["fechaFin"]
            and r["fechaInicio"]
            <= day.isoformat()
            <= min(r["fechaFin"], cut.isoformat())
        ]
        task = entry.get("task") or {}
        tokens = scope_tokens(
            str(entry.get("taskName") or task.get("name") or "")
        )
        for tag in entry.get("tags") or []:
            tokens |= scope_tokens(
                str(tag.get("name", "") if isinstance(tag, dict) else tag)
            )
        selected = (
            [r for r in eligible if tokens == {r["scope"]}]
            if tokens
            else eligible
        )
        if len(selected) != 1:
            # A valid tag for a different scope belongs outside these rows.
            if (
                not tokens
                or not selected
                and any(r["scope"] in tokens for r in eligible)
            ):
                pending.update(id(r) for r in eligible)
            continue
        interval = entry.get("timeInterval") or {}
        duration = interval.get("duration")
        try:
            seconds = Decimal(str(duration))
            if not seconds.is_finite() or seconds < 0:
                raise ValueError("Invalid duration")
        except (ValueError, ArithmeticError):
            pending.add(id(selected[0]))
            continue
        totals[id(selected[0])] += seconds / Decimal(3600)
    for row in rows:
        known = (
            id(row) not in pending
            and bool(row["scope"])
            and bool(row["fechaInicio"] and row["fechaFin"])
            and row["fechaInicio"] <= row["fechaFin"]
        )
        budget = (
            Decimal(str(row["budget"])) if row["budget"] is not None else None
        )
        result = financials(budget, totals[id(row)] if known else None)
        row.update(
            {
                "burn": float(result["burn"])
                if result["burn"] is not None
                else None,
                "etc": float(result["etc"])
                if result["etc"] is not None
                else None,
                "hoursDeviation": float(result["hours_deviation"])
                if result["hours_deviation"] is not None
                else None,
                "avance": float(result["advance"])
                if result["advance"] is not None
                else None,
                "hours_pending": not known,
                "progress_pending": result["advance"] is None,
            }
        )
