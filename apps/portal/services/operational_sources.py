"""Operativa uses the exact EVA populations and legacy capacity RPCs."""

import calendar
import hashlib
import json
import re
import unicodedata
from datetime import date
from typing import Any

from django.core.cache import cache
from django.utils import timezone

from apps.capacidad.rpc import get_capacity_base, get_capacity_project_data
from apps.clockify.provider import build_clockify_loader
from apps.portal.schemas import ProjectView
from core.exceptions import DashboardError
from core.sheets.factory import build_sheet_repository


def norm(value: Any) -> Any:
    """Normaliza nombres para cruzar fuentes operativas."""
    return "".join(
        c
        for c in unicodedata.normalize("NFKD", str(value or "").lower())
        if not unicodedata.combining(c)
    ).strip()


def remaining_days(project: Any) -> Any:
    """Calcula los dias restantes hasta terminar el proyecto."""
    from datetime import datetime

    for pattern in ("%d/%m/%y", "%Y-%m-%d", "%d/%m/%Y"):
        try:
            return (
                datetime.strptime(str(project.end), pattern).date()
                - timezone.localdate()
            ).days
        except ValueError:
            pass
    return getattr(project, "renewal_days", None)


def aer_open_risks(project_ids: Any) -> Any:
    # Lee riesgos del dashboard sin ejecutar la limpieza de escrituras.
    """Cuenta riesgos abiertos sin modificar las hojas."""
    if not project_ids:
        return {}
    from apps.aer.constants import SHEET_RISKS
    from apps.aer.services.plan import is_closed
    from apps.aer.services.risks_actions import dedup_risks

    key = "portal:aer-open-risks:v1"
    rows = cache.get(key)
    if rows is None:
        try:
            reader = build_sheet_repository()
            rows = (
                reader.read_as_objects(SHEET_RISKS)
                if reader.sheet_exists(SHEET_RISKS)
                else []
            )
            cache.set(key, rows, 300)
        except DashboardError:
            return {pid: "No disponible" for pid in project_ids}
    return {
        pid: sum(
            1
            for row in dedup_risks(
                [
                    row
                    for row in rows
                    if str(row.get("ID_Proyecto") or "").strip() == pid
                ]
            )
            if not is_closed(row.get("Estado") or "Abierto")
            and row.get("Riesgo")
        )
        for pid in project_ids
    }


def eva_projects(ixb: Any, aer: Any) -> Any:
    """Convierte proyectos EVA a la poblacion operativa."""
    result = []
    for p in [*ixb.view.projects, *aer.view.projects]:
        paused = getattr(p, "status_code", "") == "sus"
        days = remaining_days(p)
        progress = p.progress
        over_hours = p.budget > 0 and p.burn is not None and p.burn > p.budget
        few_hours = (
            p.budget > 0
            and p.burn is not None
            and p.budget - p.burn <= p.budget * 0.10
        )
        health = (
            "Cr\u00edtica"
            if over_hours or (days is not None and days < 0)
            else "En Riesgo"
            if days is None or (days <= 30 and few_hours)
            else "A tiempo"
        )
        result.append(
            ProjectView(
                p.project_id,
                p.name,
                getattr(p, "client", ""),
                p.manager,
                p.service,
                "En Pausa" if paused else "Activo",
                health,
                "",
                round(progress or 0),
                days or 0,
                p.budget,
                p.burn or 0,
                p.etc or 0,
            )
        )
    return result


def tagged_investment(projects: Any, include_suspended: Any = False) -> Any:
    """Suma inversion por etiquetas sin duplicar registros."""
    selected = {
        p.project_id: p
        for p in projects
        if include_suspended or getattr(p, "status_code", "") != "sus"
    }
    ids = sorted(selected)
    signature = hashlib.sha256(
        json.dumps(
            [
                (
                    pid,
                    str(getattr(selected[pid], "start", "")),
                    str(getattr(selected[pid], "end", "")),
                )
                for pid in ids
            ],
            ensure_ascii=True,
        ).encode("utf-8")
    ).hexdigest()
    key = (
        "portal:tagged-investment:v7:"
        + timezone.localdate().isoformat()
        + ":"
        + signature
    )
    stored = cache.get(key)
    if stored is not None:
        return stored
    totals = {"operational": 0.0, "commercial": 0.0}
    by_project = {pid: {"operational": 0.0, "commercial": 0.0} for pid in ids}
    today = timezone.localdate()
    month_index = today.year * 12 + today.month - 1
    labels = (
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
    monthly: dict[str, dict[str, Any]] = {}
    for offset in range(5, -1, -1):
        year, month = divmod(month_index - offset, 12)
        monthly[f"{year}-{month + 1:02d}"] = {
            "label": f"{labels[month]} {year}",
            "billable": 0.0,
            "operational": 0.0,
            "commercial": 0.0,
            "projects": {},
        }
    errors = []
    seen = set()
    try:
        loader = build_clockify_loader(build_sheet_repository())
        for project_id in ids:
            try:
                project = selected[project_id]

                def parse_day(text: Any) -> Any:
                    from datetime import datetime

                    for pattern in ("%d/%m/%y", "%Y-%m-%d", "%d/%m/%Y"):
                        try:
                            return datetime.strptime(str(text), pattern).date()
                        except ValueError:
                            pass
                    return None

                start, end = (
                    parse_day(getattr(project, "start", "")),
                    parse_day(getattr(project, "end", "")),
                )
                entries = (
                    loader.load_project(project_id, (start, end))
                    if start and end
                    else loader.load_project(project_id)
                )
                suffix = re.search(r"_(S\d+|CR\d+)$", project_id, re.I)
                for entry in entries:
                    if suffix:
                        marker_text = " ".join(
                            [entry.task_name, entry.description, *entry.tags]
                        )
                        markers = re.findall(
                            r"(?<![A-Z0-9])(S\d+|CR\d+)(?![A-Z0-9])",
                            marker_text.upper(),
                        )
                        if markers and suffix[1].upper() not in markers:
                            continue
                    token = entry.entry_id or (
                        entry.project_id,
                        entry.resource_name,
                        entry.entry_date,
                        entry.duration_hours,
                        entry.description,
                    )
                    if token in seen:
                        continue
                    seen.add(token)
                    tags = {t.strip().upper() for t in entry.tags}
                    for tag, category in [
                        ("INV_OPERATIVA", "operational"),
                        ("INV_COMERCIAL", "commercial"),
                    ]:
                        if tag in tags:
                            totals[category] += entry.duration_hours
                            by_project[project_id][category] += (
                                entry.duration_hours
                            )
                    recorded = entry.entry_date
                    if recorded is not None:
                        if hasattr(recorded, "tzinfo") and timezone.is_aware(
                            recorded
                        ):
                            recorded = timezone.localtime(recorded)
                        day = (
                            recorded.date()
                            if hasattr(recorded, "date")
                            else recorded
                        )
                        bucket = monthly.get(day.strftime("%Y-%m"))
                        if (
                            bucket is not None
                            and day <= today
                            and (not start or day >= start)
                            and (not end or day <= end)
                        ):
                            # Categorias exclusivas evitan duplicar horas.
                            chart_category = (
                                "operational"
                                if "INV_OPERATIVA" in tags
                                else "commercial"
                                if "INV_COMERCIAL" in tags
                                else "billable"
                                if entry.is_billable
                                else None
                            )
                            if chart_category:
                                bucket[chart_category] += entry.duration_hours
                                item = bucket["projects"].setdefault(
                                    project_id,
                                    {
                                        "id": project_id,
                                        "name": project.name,
                                        "client": getattr(
                                            project, "client", ""
                                        ),
                                        "service": getattr(
                                            project, "service", ""
                                        ),
                                        "billable": 0.0,
                                        "operational": 0.0,
                                        "commercial": 0.0,
                                        "total": 0.0,
                                    },
                                )
                                item[chart_category] += entry.duration_hours
                                item["total"] += entry.duration_hours
            except DashboardError as error:
                errors.append(project_id + ": " + error.build_message())
    except DashboardError as error:
        errors.append(error.build_message())
    maximum = max(
        (
            sum(row[k] for k in ("billable", "operational", "commercial"))
            for row in monthly.values()
        ),
        default=0,
    )
    for row in monthly.values():
        row["projects"] = list(row["projects"].values())
        row["total"] = sum(
            row[k] for k in ("billable", "operational", "commercial")
        )
        for category in ("billable", "operational", "commercial"):
            row[category + "_height"] = (
                row[category] / maximum * 100 if maximum else 0
            )
    result = {
        "by_project": by_project,
        "monthly": list(monthly.values()),
        "monthly_has_data": maximum > 0,
        "totals": totals,
        "complete": not errors,
        "error": "; ".join(errors),
        "projects": len(ids),
    }
    if not errors:
        cache.set(key, result, 300)
    return result


def legacy_capacity(month: Any) -> Any:
    """Calcula capacidad diaria desde las fuentes del panel."""
    key = "portal:legacy-capacity:v2:" + month
    cached = cache.get(key)
    if cached is not None:
        return cached
    base = get_capacity_base(month)
    if not base.get("ok"):
        return {"error": base.get("error", "Capacidad no disponible")}
    year, mon = map(int, month.split("-"))
    days = [
        date(year, mon, d).isoformat()
        for d in range(1, calendar.monthrange(year, mon)[1] + 1)
        if date(year, mon, d).weekday() < 5
    ]
    people: dict[str, dict[str, float]] = {}
    fact = 0.0
    pending = 0
    meta = {}
    estimated = 0.0
    consumed = 0.0
    registered = set()
    assignments = set()
    for row in base.get("filas", []):
        if norm(row.get("concepto")) == "sin asignacion":
            continue
        pid = row.get("idProyecto", "")
        key2 = (pid, row.get("iteration", ""))
        if pid and key2 not in meta:
            meta[key2] = get_capacity_project_data(pid, key2[1], month)
        data = meta.get(key2, {"ok": True, "daily": {}})
        if data.get("fueraMes"):
            continue
        if (
            data.get("inicio")
            and data.get("fin")
            and (data["fin"] < month + "-01" or data["inicio"] > days[-1])
        ):
            continue
        person = norm(row.get("recurso"))
        assignment = (person, pid, row.get("iteration", ""))
        if assignment in assignments:
            continue
        assignments.add(assignment)
        values = people.setdefault(person, {day: 0.0 for day in days})
        rule = row.get("regla") or {}
        if not data.get("ok") or not rule:
            pending += 1
            continue
        recorded = data.get("daily", {}).get(person, {})
        total = sum(float(recorded.get(day) or 0) for day in days)
        if total > 0:
            registered.add(person)
            estimated += float(row.get("horasEstimadas") or 0)
            consumed += total
        if rule.get("facturable") == "Facturable":
            fact += sum(float(recorded.get(day) or 0) for day in days)
        if rule.get("afecta"):
            for day in days:
                values[day] += float(recorded.get(day) or 0)
    result = {
        "month": month,
        "people": len(people),
        "days": len(days),
        "base": len(people) * len(days) * 8,
        "billable": round(fact, 2),
        "available": None
        if pending
        else round(
            sum(
                max(0, 8 - v)
                for values in people.values()
                for v in values.values()
            ),
            2,
        ),
        "estimated": round(estimated, 2),
        "consumed": round(consumed, 2),
        "registered_people": len(registered),
        "pending": pending,
        "over": sum(
            any(v > 8.001 for v in values.values())
            for values in people.values()
        ),
    }
    if not pending:
        cache.set(key, result, 300)
    return result


def manager_monthly_history(manager: Any, current_projects: Any) -> Any:
    """Incluye proyectos cerrados que se cruzan con los ultimos seis meses."""
    from types import SimpleNamespace

    from apps.clockify.services.date_ranges import ProjectDateRangeResolver
    from apps.ejecutivo.services.aer_tym_summary import (
        find_mpb_header,
        resolve_columns,
    )
    from apps.ejecutivo.services.ixb_rules import (
        find_delivery_manager,
        read_history_id,
        read_project_id,
        read_project_manager,
    )
    from apps.ejecutivo.services.mpb_values import (
        parse_mpb_date,
        parse_mpb_hours,
        read_cell,
    )
    from core.sheets import sheet_names
    from core.utils.text import get_flexible_value

    today = timezone.localdate()
    index = today.year * 12 + today.month - 6
    year, month = divmod(index, 12)
    first = date(year, month + 1, 1)
    manager_signature = hashlib.sha256(manager.encode("utf-8")).hexdigest()
    cache_key = (
        "portal:dm-monthly-history:v5:"
        + manager_signature
        + ":"
        + today.isoformat()
    )
    cached = cache.get(cache_key)
    if cached is not None:
        return cached
    try:
        reader = build_sheet_repository()
        rows = reader.read_as_objects(sheet_names.SHEET_PROJECTS)
        history = (
            reader.read_as_objects(sheet_names.SHEET_PROJECTS_HISTORY)
            if reader.sheet_exists(sheet_names.SHEET_PROJECTS_HISTORY)
            else []
        )
        candidates = {p.project_id: p for p in current_projects}
        resolver = ProjectDateRangeResolver(reader, today)
        references = {
            read_project_id(row): row for row in rows if read_project_id(row)
        }
        for row in history:
            pid = read_history_id(row)
            if not pid:
                continue
            merged = references.setdefault(pid, {"ID_Proyecto": pid})
            aliases = {
                "Nombre": ["Project Name", "Nombre"],
                "Cliente": ["Account", "Client", "Cliente"],
                "Servicio": ["Service", "Servicio"],
                "Budget_Hrs": ["Budget", "Budget_Hrs", "Presupuesto"],
                "Delivery Manager": ["Delivery Manager", "Delivery_Manager"],
            }
            for field, names in aliases.items():
                value = get_flexible_value(row, names)
                if value is not None and str(value).strip():
                    merged[field] = value
            if pid in candidates:
                current = candidates[pid]
                candidates[pid] = SimpleNamespace(
                    project_id=pid,
                    name=str(merged.get("Nombre") or current.name),
                    client=str(
                        merged.get("Cliente") or getattr(current, "client", "")
                    ),
                    service=str(
                        merged.get("Servicio")
                        or getattr(current, "service", "")
                    ),
                    budget=parse_mpb_hours(merged["Budget_Hrs"])
                    if merged.get("Budget_Hrs") is not None
                    else getattr(current, "budget", None),
                    start=current.start,
                    end=current.end,
                )
        for pid, row in references.items():
            dm = find_delivery_manager(
                history, [row], pid
            ) or read_project_manager(row)
            if norm(dm) != norm(manager) or pid in candidates:
                continue
            try:
                period = resolver.resolve(pid)
            except DashboardError:
                continue
            if (
                period.start_date
                and period.end_date
                and period.start_date <= today
                and period.end_date >= first
            ):
                candidates[pid] = SimpleNamespace(
                    project_id=pid,
                    name=str(row.get("Nombre") or pid),
                    client=str(row.get("Cliente") or ""),
                    service=str(
                        get_flexible_value(row, ["Servicio", "Service"]) or ""
                    ),
                    budget=parse_mpb_hours(row.get("Budget_Hrs")),
                    start=period.start_date.isoformat(),
                    end=period.end_date.isoformat(),
                )
        values = reader.read_values("MPB")
        header = find_mpb_header(values)
        if header is not None:
            columns = resolve_columns(values[header])
            for mpb_row in values[header + 1 :]:
                if norm(read_cell(mpb_row, columns["manager"])) != norm(
                    manager
                ):
                    continue
                pid = str(
                    read_cell(mpb_row, columns["project_id"]) or ""
                ).strip()
                mpb_start_text, mpb_end_text = (
                    parse_mpb_date(read_cell(mpb_row, columns["start"])),
                    parse_mpb_date(read_cell(mpb_row, columns["end"])),
                )
                mpb_start = (
                    date.fromisoformat(mpb_start_text)
                    if mpb_start_text
                    else None
                )
                mpb_end = (
                    date.fromisoformat(mpb_end_text) if mpb_end_text else None
                )
                if (
                    pid
                    and mpb_start
                    and mpb_end
                    and mpb_start <= today
                    and mpb_end >= first
                ):
                    candidates[pid] = SimpleNamespace(
                        project_id=pid,
                        name=str(read_cell(mpb_row, columns["name"]) or pid),
                        client=str(read_cell(mpb_row, columns["client"]) or ""),
                        service=str(
                            read_cell(mpb_row, columns["service"]) or ""
                        ),
                        budget=parse_mpb_hours(
                            read_cell(mpb_row, columns["budget"])
                        ),
                        start=mpb_start.isoformat(),
                        end=mpb_end.isoformat(),
                    )
        from copy import deepcopy
        from datetime import datetime

        result = deepcopy(
            tagged_investment(list(candidates.values()), include_suspended=True)
        )

        def day(value: Any) -> Any:
            for pattern in ("%Y-%m-%d", "%d/%m/%y", "%d/%m/%Y"):
                try:
                    return datetime.strptime(str(value), pattern).date()
                except ValueError:
                    pass
            return None

        for offset, bucket in enumerate(result["monthly"]):
            yy, mm = divmod(first.year * 12 + first.month - 1 + offset, 12)
            month_start = date(yy, mm + 1, 1)
            month_end = min(
                today, date(yy, mm + 1, calendar.monthrange(yy, mm + 1)[1])
            )
            budget = 0.0
            missing = 0
            projects = {p["id"]: p for p in bucket["projects"]}
            for pid, project in candidates.items():
                start, end = day(project.start), day(project.end)
                if (
                    not start
                    or not end
                    or start > end
                    or start > month_end
                    or end < month_start
                ):
                    continue
                hours = getattr(project, "budget", None)
                planned = (
                    None
                    if hours is None or hours <= 0
                    else hours
                    * ((min(end, month_end) - max(start, month_start)).days + 1)
                    / ((end - start).days + 1)
                )
                item = projects.setdefault(
                    pid,
                    {
                        "id": pid,
                        "name": project.name,
                        "client": getattr(project, "client", ""),
                        "service": getattr(project, "service", ""),
                        "billable": 0,
                        "operational": 0,
                        "commercial": 0,
                        "total": 0,
                    },
                )
                item["project_budget"] = hours
                item["budget"] = (
                    round(planned, 2) if planned is not None else None
                )
                if planned is None:
                    missing += 1
                else:
                    budget += planned
            bucket["projects"] = list(projects.values())
            bucket["budget"] = round(budget, 2)
            bucket["budget_missing"] = missing
        result["scope"] = (
            "Incluye proyectos actuales y cerrados con fechas dentro "
            "del periodo. DM segun asignacion disponible en las hojas."
        )
        if result["complete"]:
            cache.set(cache_key, result, 300)
        return result
    except DashboardError as error:
        return {"complete": False, "error": error.build_message()}
