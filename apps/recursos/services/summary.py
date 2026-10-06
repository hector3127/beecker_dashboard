"""Resumen general de Recursos (getResumenRecursos)."""

from collections.abc import Mapping, Sequence
from datetime import date, timedelta
from typing import Any

from apps.recursos.services.resource_records import (
    Record,
    role_category,
)
from core.utils.numbers import round_half_up, round_half_up_int
from core.utils.text import normalize_name

"""BKD.090.003 - Resumen de Recursos
Equivale a getResumenRecursos(), getProyectosConHoras() y
getPersonasConHoras(): KPIs, horas por dia en y fuera de horario,
distribucion por categoria y proyecto, y detalle por recurso.
"""

JsonObject = dict[str, Any]

MONTHS = (
    "Jan", "Feb", "Mar", "Apr", "May", "Jun",
    "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
)  # fmt: skip
WEEK_DAYS = 7
CHART_DAYS = 31
MAX_PROJECTS = 8
TOP_PROJECTS = 7
TOP_OUTSIDE = 5
TOP_BARS = 10
SATURDAY = 5
NO_DATE = "sin_fecha"


def round2(value: float) -> float:
    """Math.round(x * 100) / 100."""
    return round_half_up(value, 2)


def pct(part: float, total: float) -> float:
    """Math.round(part / total * 1000) / 10, o 0 sin total."""
    return round_half_up_int(part / total * 1000) / 10 if total else 0


def business_days(first: str, last: str) -> int:
    """Dias lunes a viernes entre dos fechas, inclusive."""
    try:
        start, end = date.fromisoformat(first), date.fromisoformat(last)
    except ValueError:
        return 0

    return sum(
        1
        for offset in range((end - start).days + 1)
        if (start + timedelta(days=offset)).weekday() < SATURDAY
    )


def day_label(day: str) -> str:
    """Etiqueta dd MMM (por ejemplo 05 Jan)."""
    try:
        moment = date.fromisoformat(day)
    except ValueError:
        return day

    return f"{moment.day:02d} {MONTHS[moment.month - 1]}"


def window_hours(
    hours_by_day: Mapping[str, float],
    today: date,
    days_back: int,
    size: int,
) -> float:
    """Horas de los dias today-days_back ... today-days_back-size+1."""
    return sum(
        hours_by_day.get(
            (today - timedelta(days=days_back + offset)).isoformat(),
            0,
        )
        for offset in range(size)
    )


def change_pct(current: float, previous: float) -> float | None:
    """% de cambio contra el periodo anterior, o None sin base."""
    if not previous:
        return None

    return round_half_up_int((current - previous) / previous * 1000) / 10


def ranked(totals: Mapping[str, float], total: float) -> list[JsonObject]:
    """{nombre, horas, pct} ordenado por horas descendente."""
    return sorted(
        (
            {"nombre": name, "horas": round2(hours), "pct": pct(hours, total)}
            for name, hours in totals.items()
        ),
        key=lambda item: -item["horas"],
    )


def add(totals: dict[str, float], key: str, hours: float) -> None:
    """Acumula horas por llave conservando el orden de llegada."""
    totals[key] = totals.get(key, 0) + hours


def project_distribution(
    records: Sequence[Record],
    total: float,
) -> list[JsonObject]:
    """Horas por proyecto; mas de 8 se agrupan en Otros."""
    by_project: dict[str, float] = {}

    for record in records:
        add(by_project, record.project or "Sin proyecto", record.hours)

    distribution = ranked(by_project, total)

    if len(distribution) <= MAX_PROJECTS:
        return distribution

    rest = distribution[TOP_PROJECTS:]

    return [
        *distribution[:TOP_PROJECTS],
        {
            "nombre": "Otros",
            "horas": round2(sum(item["horas"] for item in rest)),
            "pct": round_half_up(sum(item["pct"] for item in rest), 1),
        },
    ]


def resource_rows(
    records: Sequence[Record],
    positions: Mapping[str, str],
) -> list[JsonObject]:
    """Una fila por recurso, ordenada por horas totales."""
    people: dict[str, JsonObject] = {}

    for record in records:
        info = people.setdefault(
            record.resource or "Sin nombre",
            {
                "total": 0.0,
                "inside": 0.0,
                "outside": 0.0,
                "days": set(),
                "projects": {},
            },
        )
        info["total"] += record.hours
        info["outside" if record.outside_schedule else "inside"] += record.hours

        if record.day:
            info["days"].add(record.day)

        if record.project:
            add(info["projects"], record.project, record.hours)

    rows = []

    for name, info in people.items():
        projects = info["projects"]
        main = sorted(projects, key=lambda key: -projects[key])
        rows.append(
            {
                "recurso": name,
                "posicion": positions.get(normalize_name(name)) or "",
                "proyectoPrincipal": main[0] if main else "",
                "horasTotales": round2(info["total"]),
                "horasEnHorario": round2(info["inside"]),
                "horasFueraHorario": round2(info["outside"]),
                "diasTrabajados": len(info["days"]),
            },
        )

    return sorted(rows, key=lambda row: -row["horasTotales"])


def daily_chart(by_day: Mapping[str, JsonObject]) -> list[JsonObject]:
    """Ultimos 31 dias con datos, en horario y fuera de horario."""
    days = sorted(day for day in by_day if day != NO_DATE)[-CHART_DAYS:]

    return [
        {
            "fecha": day,
            "etiqueta": day_label(day),
            "enHorario": round2(by_day[day]["inside"]),
            "fueraHorario": round2(by_day[day]["outside"]),
        }
        for day in days
    ]


def build_summary(
    records: Sequence[Record],
    positions: Mapping[str, str],
    today: date,
) -> JsonObject:
    """
    Resumen general del modulo Recursos (getResumenRecursos).

    Args:
        records: Registros de todos los proyectos.
        positions: Posicion por nombre normalizado (hoja Recursos).
        today: Fecha local de hoy.

    Returns:
        El mismo objeto que regresaba el original.
    """
    total = sum(record.hours for record in records)
    unique_days = sorted({record.day for record in records if record.day})
    activities = {
        f"{record.project}||{record.description.strip() or '(sin descripción)'}"
        for record in records
    }
    projects = {record.project for record in records if record.project}
    outside_total = 0.0
    outside_detail: list[JsonObject] = []
    by_day: dict[str, JsonObject] = {}

    for record in records:
        day = by_day.setdefault(
            record.day or NO_DATE,
            {"inside": 0.0, "outside": 0.0},
        )

        if record.outside_schedule:
            outside_total += record.hours
            day["outside"] += record.hours
            outside_detail.append(
                {
                    "fecha": record.day,
                    "recurso": record.resource,
                    "horas": round2(record.hours),
                    "descripcion": record.description,
                },
            )
        else:
            day["inside"] += record.hours

    outside_detail.sort(key=lambda item: item["fecha"], reverse=True)
    hours_by_day = {
        key: value["inside"] + value["outside"] for key, value in by_day.items()
    }
    by_category: dict[str, float] = {}
    by_resource: dict[str, float] = {}

    for record in records:
        role = positions.get(normalize_name(record.resource)) or ""
        add(by_category, role_category(role), record.hours)
        add(by_resource, record.resource, record.hours)

    projects_distribution = project_distribution(records, total)
    people = resource_rows(records, positions)
    bar_items: list[JsonObject] = [
        {"nombre": name, "horas": round2(hours)}
        for name, hours in by_resource.items()
    ]
    bars = sorted(bar_items, key=lambda item: -item["horas"])[:TOP_BARS]

    return {
        "totalHoras": round2(total),
        "pctCambioSemanal": change_pct(
            window_hours(hours_by_day, today, 0, WEEK_DAYS),
            window_hours(hours_by_day, today, WEEK_DAYS, WEEK_DAYS),
        ),
        "totalRecursos": len(by_resource),
        "totalProyectos": len(projects),
        "diasTrabajados": len(unique_days),
        "diasPeriodo": (
            business_days(unique_days[0], unique_days[-1]) if unique_days else 0
        ),
        "actividadesRegistradas": len(activities),
        "horasFueraHorario": round2(outside_total),
        "pctFueraHorario": pct(outside_total, total),
        "pctEnHorario": pct(total - outside_total, total),
        "top5FueraHorario": [
            {"recurso": row["recurso"], "horas": row["horasFueraHorario"]}
            for row in sorted(
                (row for row in people if row["horasFueraHorario"] > 0),
                key=lambda row: -row["horasFueraHorario"],
            )[:TOP_OUTSIDE]
        ],
        "detalleFueraHorario": outside_detail,
        "horasPorDia": daily_chart(by_day),
        "distribucionCategoria": ranked(by_category, total),
        "distribucionProyecto": projects_distribution,
        "detallePorRecurso": people,
        "proyectoTop": projects_distribution[0]
        if projects_distribution
        else None,
        "barras": bars,
        "maxHoras": bars[0]["horas"] if bars else 1,
    }


def projects_with_hours(records: Sequence[Record]) -> list[str]:
    """Proyectos con registros, sin repetir y ordenados."""
    return sorted({record.project for record in records if record.project})


def people_with_hours(records: Sequence[Record]) -> list[str]:
    """Personas con registros, sin repetir y ordenadas."""
    return sorted({record.resource for record in records if record.resource})
