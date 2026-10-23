"""Monthly account hours from synchronized Clockify, without rates."""

import re
from calendar import monthrange
from collections import defaultdict
from datetime import date
from typing import Any

from django.utils import timezone

from apps.clockify.services.clockify_client import ClockifyProject
from apps.clockify.services.project_matcher import resolve_clockify_project
from apps.clockify.services.time_entry_loader import load_project_links
from apps.datastore.models import ClockifyMonthSync, ClockifyTimeEntry, Project
from apps.ejecutivo.services.account_view import account_matches
from apps.portal.services.cost_project_inventory import inventory
from apps.portal.services.executive_period import ExecutivePeriod, applied
from apps.portal.services.project_task_scope import (
    financial_task_tokens,
    financial_variant,
)
from core.sheets.factory import build_sheet_repository
from core.sheets.protocols import SheetReader
from core.utils.dates import to_datetime

MONTHS = (
    "Ene",
    "Feb",
    "Mar",
    "Abr",
    "May",
    "Jun",
    "Jul",
    "Ago",
    "Sep",
    "Oct",
    "Nov",
    "Dic",
)
MONTH_ID = re.compile(
    r"^((?:AER|ROC)\.[A-Z0-9]+\.\d{3})(?:\.(0[1-9]|1[0-2]))?$", re.I
)


def project_catalog(reader: SheetReader, year: int) -> dict[str, Any]:
    """Use the same operational inventory and financial IDs as account costs."""
    with applied(ExecutivePeriod(date(year, 1, 1), date(year, 12, 31), "anio")):
        catalog = inventory(reader)
    for row in reader.read_values("DataRevenue")[1:]:
        if len(row) < 8 or any(
            str(c).strip().casefold()
            in {"total", "subtotal", "grand total", "total general"}
            for c in row[:7]
        ):
            continue
        day = to_datetime(row[6])
        pid, owner = str(row[4] or "").strip(), str(row[1] or "").strip()
        if pid and owner and day and day.year == year:
            item = catalog.setdefault(
                pid.casefold(), {"id": pid, "accounts": set()}
            )
            item["accounts"].add(owner)
    return catalog


def _month_scope(pid: str, ids: list[str]) -> tuple[str, int | None, set[int]]:
    """Keep AER/ROC .MM partitions consistent with the financial report."""
    match = MONTH_ID.fullmatch(pid)
    child = financial_variant(pid)
    if not match:
        return (child[0] if child else pid), None, set()
    base, suffix = match.groups()
    reserved = {
        int(m.group(2))
        for candidate in ids
        if (m := MONTH_ID.fullmatch(candidate))
        and m.group(1).casefold() == base.casefold()
        and m.group(2)
    }
    month = (
        int(suffix)
        if suffix
        else (1 if base.upper().startswith("ROC.") and reserved else None)
    )
    return (
        base,
        month,
        reserved if base.upper().startswith("AER.") and not suffix else set(),
    )


def load_account_hours(
    client: str,
    year: int,
    reader: SheetReader | None = None,
    *,
    start: date | None = None,
    end: date | None = None,
) -> dict[str, Any]:
    """Build projects × months, preserving unknown months and unique entries.

    Reads only the synchronized database; opening the report never launches
    a fresh Clockify download. Missing links/months remain explicitly pending.
    """
    today = timezone.localdate()
    if not 2000 <= year <= today.year:
        raise ValueError("Selecciona un año entre 2000 y el año actual.")
    first = start or date(year, 1, 1)
    last = min(end or date(year, 12, 31), today)
    if first > last or first.year < 2000 or (last - first).days > 1096:
        raise ValueError(
            "Elige fechas válidas, hasta hoy y de hasta tres años."
        )
    first_month, last_month = first.replace(day=1), last.replace(day=1)
    reader = reader or build_sheet_repository()
    catalog: dict[str, Any] = {}
    for selected_year in range(first.year, last.year + 1):
        for key, item in project_catalog(reader, selected_year).items():
            if key in catalog:
                catalog[key]["accounts"].update(item["accounts"])
            else:
                catalog[key] = {**item, "accounts": set(item["accounts"])}
    syncs = dict(
        ClockifyMonthSync.objects.filter(
            month__range=(first_month, last_month)
        ).values_list("month", "synced_at")
    )
    month_dates = [
        date(i // 12, i % 12 + 1, 1)
        for i in range(
            first.year * 12 + first.month - 1, last.year * 12 + last.month
        )
    ]
    months = [
        {
            "key": day.strftime("%Y-%m"),
            "label": MONTHS[day.month - 1]
            + (f" {day.year}" if first.year != last.year else ""),
            "partial": day < first
            or date(day.year, day.month, monthrange(day.year, day.month)[1])
            > last,
            "available": day in syncs,
        }
        for day in month_dates
    ]
    projects = [
        ClockifyProject(pid, name)
        for pid, name in ClockifyTimeEntry.objects.order_by()
        .values_list("project_id", "project_name")
        .distinct()
    ]
    links = load_project_links(reader)
    year_projects = set(
        ClockifyTimeEntry.objects.filter(entry_date__range=(first, last))
        .order_by()
        .values_list("project_id", flat=True)
        .distinct()
    )
    names = {}
    for saved in Project.objects.values("internal_id", "name", "client__name"):
        pid = saved["internal_id"]
        names[pid.casefold()] = saved["name"]
        child = financial_variant(pid)
        if pid.casefold() in catalog or (child and child[0] in catalog):
            continue
        # Include investment/non-financial IDs only with explicit account
        # ownership in the catalog and recorded activity in the selected year.
        if not account_matches(saved["client__name"], client):
            continue
        match = resolve_clockify_project(pid, projects, links)
        if match and match.project_id in year_projects:
            catalog[pid.casefold()] = {
                "id": pid,
                "accounts": {saved["client__name"]},
            }
    selected = [
        item
        for item in catalog.values()
        if any(account_matches(name, client) for name in item["accounts"])
    ]
    selected.sort(key=lambda p: p["id"].casefold())
    ids = [item["id"] for item in catalog.values()]
    plans, rows = {}, []
    for item in selected:
        pid = item["id"]
        lookup, only_month, reserved = _month_scope(pid, ids)
        project = resolve_clockify_project(pid, projects, links)
        if project is None and lookup.casefold() != pid.casefold():
            project = resolve_clockify_project(lookup, projects, links)
        shared = any(
            not account_matches(owner, client) for owner in item["accounts"]
        )
        issue = (
            "ID compartido entre cuentas; asignación pendiente"
            if shared
            else "Sin vínculo único en los registros guardados de Clockify"
            if project is None
            else ""
        )
        rows.append(
            {
                "id": pid,
                "name": names.get(pid.casefold())
                or (project.name if project else pid),
                "issue": issue,
                "cells": [],
                "known_hours": 0.0,
                "partial": bool(issue),
            }
        )
        if project is not None and not shared:
            plans[pid] = (project, only_month, reserved)
    raw = ClockifyTimeEntry.objects.filter(
        project_id__in={p[0].project_id for p in plans.values()},
        month__range=(first_month, last_month),
    ).values(
        "entry_id",
        "project_id",
        "entry_date",
        "month",
        "duration_seconds",
        "task_name",
        "task_id",
    )
    by_project = defaultdict(list)
    for entry in raw:
        by_project[entry["project_id"]].append(entry)
    claims = defaultdict(set)
    unknown = defaultdict(set)
    amounts = {}
    for pid, (project, only_month, reserved) in plans.items():
        variant = financial_variant(pid)
        # A dedicated CR/S project already isolates its own records.
        dedicated = (
            re.sub(r"[\s|_-]+", "", project.name).casefold()
            == re.sub(r"[\s|_-]+", "", pid).casefold()
        )
        excluded = {
            v[1]
            for candidate in ids
            if (v := financial_variant(candidate)) and v[0] == pid.casefold()
        }
        for entry in by_project[project.project_id]:
            day = entry["entry_date"]
            month = entry["month"].month
            month_key = entry["month"].strftime("%Y-%m")
            if day and not first <= day <= last:
                continue
            if (only_month and month != only_month) or month in reserved:
                continue
            if not day or day.replace(day=1) != entry["month"]:
                unknown[pid].add(month_key)
                continue
            if (variant and not dedicated) or excluded:
                if entry["task_id"] and not entry["task_name"]:
                    unknown[pid].add(month_key)
                    continue
                tokens = financial_task_tokens(entry["task_name"])
                if variant and not dedicated and tokens != {variant[1]}:
                    if variant[1].startswith("CR") and not tokens:
                        unknown[pid].add(month_key)
                    continue
                if not variant and tokens & excluded:
                    continue
            claims[entry["entry_id"]].add(pid)
            amounts[entry["entry_id"]] = (month_key, entry["duration_seconds"])
    seconds: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for entry_id, owners in claims.items():
        entry_month, duration = amounts[entry_id]
        if len(owners) != 1:
            for pid in owners:
                unknown[pid].add(entry_month)
            continue
        seconds[next(iter(owners))][entry_month] += duration
    for row in rows:
        for month_info in months:
            known = not row["issue"] and month_info["available"]
            hours = (
                seconds[row["id"]][str(month_info["key"])] / 3600
                if known
                else None
            )
            partial = not known or month_info["key"] in unknown[row["id"]]
            row["cells"].append(
                {
                    "hours": round(hours, 4) if hours is not None else None,
                    "partial": partial,
                }
            )
            row["partial"] |= partial
        row["known_hours"] = round(
            sum(c["hours"] or 0 for c in row["cells"]), 4
        )
        if unknown[row["id"]] and not row["issue"]:
            row["issue"] = (
                "Registros sin fecha, tarea o asignación única; total parcial"
            )
    totals = [
        {
            "hours": round(sum(r["cells"][i]["hours"] or 0 for r in rows), 4)
            if m["available"]
            and (
                not rows
                or any(r["cells"][i]["hours"] is not None for r in rows)
            )
            else None,
            "partial": not m["available"]
            or any(r["cells"][i]["partial"] for r in rows),
        }
        for i, m in enumerate(months)
    ]
    return {
        "client": client,
        "year": year,
        "months": months,
        "projects": rows,
        "totals": totals,
        "known_hours": round(sum(r["known_hours"] for r in rows), 4),
        "partial": any(t["partial"] for t in totals),
        "synced_at": max(syncs.values()).isoformat() if syncs else None,
        "cutoff": last.isoformat(),
        "start": first.isoformat(),
        "end": last.isoformat(),
    }


def select_account_projects(
    data: dict[str, Any], ids: list[str]
) -> dict[str, Any]:
    """Filter authorized report rows and recalculate their monthly totals."""
    selected = {pid.strip().casefold() for pid in ids if pid.strip()}
    if not selected:
        return data
    known = {row["id"].casefold() for row in data["projects"]}
    if not selected <= known:
        raise ValueError(
            "Hay proyectos que no pertenecen al reporte solicitado."
        )
    rows = [row for row in data["projects"] if row["id"].casefold() in selected]
    totals = [
        {
            "hours": round(
                sum(row["cells"][i]["hours"] or 0 for row in rows), 4
            )
            if any(row["cells"][i]["hours"] is not None for row in rows)
            else None,
            "partial": any(row["cells"][i]["partial"] for row in rows),
        }
        for i in range(len(data["months"]))
    ]
    return {
        **data,
        "projects": rows,
        "totals": totals,
        "known_hours": round(sum(row["known_hours"] for row in rows), 4),
        "partial": any(t["partial"] for t in totals),
    }
