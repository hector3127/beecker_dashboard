"""Capacidad mensual basada exclusivamente en registros de Clockify."""

import calendar
from collections import defaultdict
from datetime import date
from typing import Any

from django.conf import settings
from django.db import transaction
from django.db.models import Q
from django.db.models.query import QuerySet

from apps.datastore.models import ClockifyMonthSync, ClockifyTimeEntry
from apps.portal.services.capacity_roster import (
    operations_roster,
    project_identity,
    project_metadata,
    roster_match,
)
from apps.portal.services.holidays import count_business_days
from core.exceptions import DashboardError

# ID de proveedor confirmado en el catálogo Clockify: Comida.
FOOD_PROJECT_ID = "61d5aa2596aafe5141cd7413"


def month_entries(
    month: str, roster: list[dict[str, Any]] | None = None
) -> QuerySet[ClockifyTimeEntry]:
    """Horas de la plantilla operativa; único proyecto excluido: Comida."""
    people = operations_roster(month) if roster is None else roster
    rows = ClockifyTimeEntry.objects.filter(
        month=date.fromisoformat(month + "-01")
    ).exclude(project_id=FOOD_PROJECT_ID)
    ids, names = set(), set()
    for user_id, user_name in rows.values_list(
        "user_id", "user_name"
    ).distinct():
        if roster_match(people, user_id, user_name):
            if user_id:
                ids.add(user_id)
            else:
                names.add(user_name)
    return rows.filter(Q(user_id__in=ids) | Q(user_id="", user_name__in=names))


@transaction.atomic
def capacity_report(month: str, workday_hours: float = 8) -> dict[str, Any]:
    """Un solo corte consistente para personas, proyectos, horas y capacidad."""
    sync = (
        ClockifyMonthSync.objects.filter(
            month=date.fromisoformat(month + "-01")
        ).first()
        if settings.CLOCKIFY_STORE_ENABLED
        else None
    )
    if sync is None:
        return {
            "ok": False,
            "mes": month,
            "error": "El mes de Clockify no está sincronizado.",
        }
    try:
        roster = operations_roster(month)
    except DashboardError as error:
        return {"ok": False, "mes": month, "error": error.build_message()}
    metadata = project_metadata()
    people = {
        p["id"]: {
            **p,
            "seconds": 0,
            "billable_seconds": 0,
            "projects": set(),
            "record_ids": set(),
        }
        for p in roster
    }
    matrix: dict[tuple[str, str], dict[str, Any]] = {}
    projects: dict[str, dict[str, Any]] = {}
    seconds = billable = entries = 0
    daily: dict[tuple[str, date], int] = defaultdict(int)
    for row in (
        month_entries(month, roster)
        .values(
            "project_id",
            "project_name",
            "user_id",
            "user_name",
            "entry_date",
            "duration_seconds",
            "billable",
        )
        .iterator()
    ):
        person_meta = roster_match(roster, row["user_id"], row["user_name"])
        if person_meta is None:
            continue
        person_id = person_meta["id"]
        person = people[person_id]
        if row["user_id"]:
            person["record_ids"].add(row["user_id"])
        pid = row["project_id"]
        project = projects.setdefault(
            pid,
            {
                "id": pid,
                "name": row["project_name"] or "Sin proyecto",
                "seconds": 0,
                "billable_seconds": 0,
                "entries": 0,
                "people": {},
                "first": None,
                "last": None,
            },
        )
        member = project["people"].setdefault(
            person_id,
            {
                "id": person_id,
                "name": person["name"],
                "seconds": 0,
                "billable_seconds": 0,
            },
        )
        assignment = matrix.setdefault(
            (person_id, pid),
            {
                **person_meta,
                "clockify_id": row["user_id"] or person_meta["clockify_id"],
                "project_id": pid,
                "project_name": row["project_name"] or "Sin proyecto",
                **project_identity(row["project_name"], metadata),
                "seconds": 0,
                "billable_seconds": 0,
                "daily": {},
            },
        )
        duration = row["duration_seconds"]
        seconds += duration
        billable += duration if row["billable"] else 0
        entries += 1
        person["projects"].add(pid)
        for target in (person, project, member, assignment):
            target["seconds"] += duration
            target["billable_seconds"] += duration if row["billable"] else 0
        project["entries"] += 1
        day = row["entry_date"]
        if day:
            day_key = day.isoformat()
            assignment["daily"][day_key] = (
                assignment["daily"].get(day_key, 0) + duration
            )
            daily[(person_id, day)] += duration
            project["first"] = min(project["first"] or day, day)
            project["last"] = max(project["last"] or day, day)
    days = count_business_days(month)
    base = len(people) * days * workday_hours
    consumed = seconds / 3600
    over = {
        person_id
        for (person_id, _), value in daily.items()
        if value > workday_hours * 3600
    }
    monthly = {
        "available": True,
        "month": month,
        "consumed": round(consumed, 2),
        "billable": round(billable / 3600, 2),
        "entries": entries,
        "people": sum(bool(p["projects"]) for p in people.values()),
        "synced_at": sync.synced_at.isoformat(),
    }
    summary = {
        "month": month,
        "source": "clockify",
        "roster_source": "Bandas/rol · Operaciones",
        "people": len(people),
        "registered_people": len(people),
        "recorded_people": monthly["people"],
        "projects": len(projects),
        "days": days,
        "workday_hours": workday_hours,
        "base": round(base, 2),
        "consumed": monthly["consumed"],
        "billable": monthly["billable"],
        "nonbillable": round((seconds - billable) / 3600, 2),
        "available": round(base - consumed, 2),
        "estimated": None,
        "over": len(over),
        "pending": 0,
        "clockify_month": monthly,
    }

    def hours(target: dict[str, Any]) -> dict[str, float]:
        return {
            "hours": round(target["seconds"] / 3600, 2),
            "billable": round(target["billable_seconds"] / 3600, 2),
            "nonbillable": round(
                (target["seconds"] - target["billable_seconds"]) / 3600, 2
            ),
        }

    project_rows = [
        {
            "id": p["id"],
            "name": p["name"],
            **hours(p),
            "entries": p["entries"],
            "people": sorted(
                [
                    {"id": m["id"], "name": m["name"], **hours(m)}
                    for m in p["people"].values()
                ],
                key=lambda m: m["name"].casefold(),
            ),
            "first": p["first"].isoformat() if p["first"] else None,
            "last": p["last"].isoformat() if p["last"] else None,
        }
        for p in projects.values()
    ]
    people_rows = [
        {
            "id": p["id"],
            "name": p["name"],
            "clockify_id": p["clockify_id"]
            or " / ".join(sorted(p["record_ids"])),
            "clockify_ids": sorted(
                p["record_ids"]
                | ({p["clockify_id"]} if p["clockify_id"] else set())
            ),
            "role": p["role"],
            "band": p["band"],
            **hours(p),
            "projects": len(p["projects"]),
            "base": round(days * workday_hours, 2),
            "available": round(days * workday_hours - p["seconds"] / 3600, 2),
        }
        for p in people.values()
    ]
    matrix_rows = [
        {
            **{
                key: row[key]
                for key in (
                    "id",
                    "clockify_id",
                    "name",
                    "role",
                    "band",
                    "project_id",
                    "project_name",
                    "business_id",
                    "manager",
                    "project_title",
                )
            },
            **hours(row),
            "daily": {
                day: round(value / 3600, 4)
                for day, value in row["daily"].items()
            },
        }
        for row in matrix.values()
    ]
    for person in people_rows:
        if not person["projects"]:
            matrix_rows.append(
                {
                    **person,
                    "project_id": "",
                    "project_name": "Sin registros en el mes",
                    "business_id": "",
                    "manager": "—",
                    "project_title": "Sin registros en el mes",
                    "daily": {},
                }
            )
    return {
        "ok": True,
        "matrix": sorted(
            matrix_rows, key=lambda r: (r["name"].casefold(), r["project_name"])
        ),
        "calendar_days": [
            date.fromisoformat(month + "-01").replace(day=d).isoformat()
            for d in range(
                1, calendar.monthrange(int(month[:4]), int(month[5:7]))[1] + 1
            )
        ],
        "mes": month,
        "summary": summary,
        "projects": sorted(
            project_rows, key=lambda p: (-p["hours"], p["name"])
        ),
        "people": sorted(people_rows, key=lambda p: p["name"].casefold()),
        "excluded_project_id": FOOD_PROJECT_ID,
    }
