"""Dashboard del proyecto AER / T&M (horas de Clockify y hojas manuales)."""

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any

from apps.aer.constants import (
    BACKEND_VERSION,
    DETAIL_LIMIT,
    RANGE_DETAIL_LIMIT,
    WORK_END_HOUR,
    WORK_START_HOUR,
)
from apps.aer.services import people_client, plan, risks_actions
from apps.aer.services.aer_values import (
    as_number,
    date_iso,
    js_date,
    js_round,
    number_or_zero,
    pct,
    round2,
    sheet_date,
    text,
)
from apps.aer.services.manual_store import AerStore
from apps.aer.services.plan import AerError
from apps.clockify.services.date_ranges import ProjectDateRange
from apps.ejecutivo.services.project_milestones import safe_iso
from core.exceptions import DashboardError, describe_error
from core.sheets import sheet_names
from core.time_entries.models import TimeEntry
from core.utils.js_values import js_object_keys, js_str, js_truthy
from core.utils.text import get_flexible_value, normalize_name

"""BKD.080.008 - Dashboard AER
Equivale a getDashboardAERTYMProyecto() y getRegistrosClockifyAERRango():
KPIs de horas (facturables, fuera de horario, consumo contra budget y
tiempo transcurrido), salud del proyecto, alertas y las secciones
manuales de planeacion, riesgos, acciones, vacaciones, evaluaciones y
cliente.
"""

JsonObject = dict[str, Any]

AER_SERVICES = ("AER", "T&M", "TYM")
MAX_ALERTS = 8
NO_TASK = "Sin task / actividad"


@dataclass(frozen=True, slots=True)
class ClockifyHours:
    """Horas de Clockify del proyecto o el error de la consulta."""

    entries: list[TimeEntry]
    project_name: str
    date_range: ProjectDateRange | None
    error: str | None


HoursLoader = Callable[[str], ClockifyHours]


def unique_entries(entries: Sequence[TimeEntry]) -> list[TimeEntry]:
    """Registros sin repetir por ID (_aertymRegistrosUnicos)."""
    chosen: dict[str, TimeEntry] = {}

    for entry in entries:
        key = (
            f"id:{entry.entry_id}"
            if entry.entry_id
            else "|".join(
                [
                    "cmp",
                    entry.resource_name,
                    str(started(entry) or ""),
                    str(getattr(entry, "ended_at", None) or ""),
                    entry.description,
                ],
            )
        )
        chosen.setdefault(key, entry)

    return list(chosen.values())


def started(entry: TimeEntry) -> datetime | None:
    """Inicio real del registro (None si la fuente no lo trae)."""
    return getattr(entry, "started_at", None)


def moment(entry: TimeEntry) -> datetime | None:
    """Inicio real o, si falta, el dia del registro."""
    return started(entry) or entry.entry_date


def is_after_hours(entry: TimeEntry) -> bool:
    """Inicia antes de las 8 o desde las 18 (_aertymEsFueraHorario)."""
    start = started(entry)

    return bool(start) and not WORK_START_HOUR <= start.hour < WORK_END_HOUR  # type: ignore[union-attr]


def total_hours(entries: Sequence[TimeEntry]) -> float:
    """Suma de horas redondeada."""
    return round2(sum(entry.duration_hours for entry in entries))


def tasks(entries: Sequence[TimeEntry]) -> list[JsonObject]:
    """Horas por task o descripcion (_aertymTareas)."""
    hours: dict[str, float] = {}

    for entry in entries:
        name = entry.task_name.strip() or entry.description.strip() or NO_TASK
        hours[name] = hours.get(name, 0) + entry.duration_hours

    rows: list[JsonObject] = [
        {"nombre": name, "horas": round2(hours[name])}
        for name in js_object_keys(hours)
    ]
    rows.sort(key=lambda row: -float(row["horas"]))

    return rows


def capacity(
    project: str,
    resource_rows: Sequence[Mapping[str, Any]],
    entries: Sequence[TimeEntry],
) -> list[JsonObject]:
    """Horas estimadas contra reales por recurso (_aertymCapacidad)."""
    assignments = []

    for row in resource_rows:
        assignment = {
            "proyecto": text(get_flexible_value(row, ["Proyecto"])),
            "rol": get_flexible_value(row, ["Posicion", "Posición", "Rol"])
            or "",
            "nombre": get_flexible_value(
                row,
                [
                    "Nombre del recurso",
                    "Nombre_del_recurso",
                    "Recurso",
                    "Nombre",
                ],
            )
            or "",
            "horasEstimadas": number_or_zero(
                get_flexible_value(
                    row,
                    ["Horas Estimadas", "Horas_Estimadas", "HorasEstimadas"],
                ),
            ),
        }

        if assignment["proyecto"] == project and js_truthy(
            assignment["nombre"]
        ):
            assignments.append(assignment)

    real: dict[str, float] = {}

    for entry in entries:
        key = normalize_name(entry.resource_name)

        if key:
            real[key] = real.get(key, 0) + entry.duration_hours

    rows = [
        {
            "nombre": assignment["nombre"],
            "rol": assignment["rol"],
            "horasEstimadas": round2(assignment["horasEstimadas"]),
            "horasReales": round2(
                real.get(normalize_name(assignment["nombre"]), 0)
            ),
        }
        for assignment in assignments
    ]
    rows.sort(key=lambda row: -float(row["horasReales"]))

    return rows


def resource_detail(entries: Sequence[TimeEntry]) -> list[JsonObject]:
    """Horas por recurso con facturables y costo (_aertymDetallePorRecurso)."""
    groups: dict[str, dict[str, float]] = {}
    total = 0.0

    for entry in entries:
        name = text(entry.resource_name) or "Sin recurso"
        group = groups.setdefault(
            name,
            {
                "total": 0.0,
                "billable": 0.0,
                "other": 0.0,
                "after": 0.0,
                "cost": 0.0,
            },
        )
        hours = entry.duration_hours
        total += hours
        group["total"] += hours
        group["billable" if entry.is_billable else "other"] += hours

        if is_after_hours(entry):
            group["after"] += hours

        group["cost"] += hours * (entry.costing_rate or 0)

    rows: list[JsonObject] = [
        {
            "recurso": name,
            "rol": "",
            "horasTotales": round2(group["total"]),
            "facturables": round2(group["billable"]),
            "noFacturables": round2(group["other"]),
            "fueraHorario": round2(group["after"]),
            "costo": round2(group["cost"]),
            "pctTotal": pct(group["total"], total),
        }
        for name in js_object_keys(groups)
        for group in [groups[name]]
    ]
    rows.sort(key=lambda row: -float(row["horasTotales"]))

    return rows


def monthly_trend(entries: Sequence[TimeEntry]) -> list[JsonObject]:
    """Horas por mes con acumulado (_aertymTendenciaMensual)."""
    months: dict[str, float] = {}

    for entry in entries:
        when = moment(entry)

        if when is None:
            continue

        key = when.strftime("%Y-%m")
        months[key] = months.get(key, 0) + entry.duration_hours

    accumulated = 0.0
    rows = []

    for month in sorted(months):
        hours = round2(months[month])
        accumulated += hours
        rows.append(
            {"mes": month, "horas": hours, "acumulado": round2(accumulated)}
        )

    return rows


def entry_details(entries: Sequence[TimeEntry], limit: int) -> list[JsonObject]:
    """Registros mas recientes primero (_aertymRegistrosDetalle)."""
    epoch = datetime(1970, 1, 1)
    ordered = sorted(
        entries, key=lambda entry: moment(entry) or epoch, reverse=True
    )

    return [
        {
            "fecha": (moment(entry) or epoch).strftime("%Y-%m-%d")
            if moment(entry)
            else "",
            "recurso": entry.resource_name or "",
            "actividad": entry.task_name or "Sin task",
            "descripcion": entry.description or "",
            "inicio": "",
            "fin": "",
            "duracion": round2(entry.duration_hours),
            "billable": entry.is_billable,
            "fueraHorario": is_after_hours(entry),
        }
        for entry in ordered[:limit]
    ]


def days_left(end: object, today: date) -> int | None:
    """Dias para la fecha fin (_aertymDiasRestantes)."""
    if not js_truthy(end):
        return None

    moment_value = js_date(end)

    if moment_value is None:
        return None

    return js_round((moment_value.date() - today).days)


def time_pct(start: object, end: object, today: date) -> float:
    """Porcentaje del periodo transcurrido (_aertymPctTiempo)."""
    if not js_truthy(start) or not js_truthy(end):
        return 0

    first, last = js_date(start), js_date(end)

    if first is None or last is None or last.date() <= first.date():
        return 0

    elapsed = (today - first.date()).days / (last.date() - first.date()).days

    return as_number(js_round(max(0, min(1, elapsed)) * 1000) / 10)


def alerts(
    kpis: Mapping[str, Any],
    risks: Mapping[str, Any],
    actions: Mapping[str, Any],
    plan_data: Mapping[str, Any],
) -> list[JsonObject]:
    """Alertas automaticas (_aertymAlertas)."""
    out: list[JsonObject] = []

    def push(level: str, title: str, detail: str, source: str) -> None:
        out.append(
            {
                "nivel": level,
                "titulo": title,
                "detalle": detail,
                "fuente": source,
            },
        )

    overdue = number_or_zero(plan_data.get("vencidosAbiertos"))
    due_today = number_or_zero(plan_data.get("vencenHoy"))

    if overdue > 0:
        push(
            "alto",
            "Compromisos vencidos",
            f"{plan_data['vencidosAbiertos']} compromiso(s) siguen abiertos "
            "después de su fecha.",
            "Planeación",
        )

    if due_today > 0:
        push(
            "medio",
            "Compromisos que vencen hoy",
            f"{plan_data['vencenHoy']} compromiso(s) deben cerrarse hoy.",
            "Planeación",
        )

    consumption = kpis["consumoPct"]
    deviation = kpis["desviacionPts"]

    if consumption > 100:
        push(
            "alto",
            "Presupuesto de horas excedido",
            f"{js_str(round2(consumption - 100))}% por encima del budget.",
            "Clockify",
        )
    elif deviation > 15:
        push(
            "alto",
            "Consumo superior al tiempo transcurrido",
            f"+{js_str(round2(deviation))} pts.",
            "Clockify",
        )
    elif deviation > 8:
        push(
            "medio",
            "Consumo adelantado al plan",
            f"+{js_str(round2(deviation))} pts.",
            "Clockify",
        )

    if kpis["pctNoFacturables"] >= 20:
        push(
            "medio",
            "Horas no facturables elevadas",
            f"{js_str(round2(kpis['pctNoFacturables']))}% del total.",
            "Clockify",
        )

    if kpis["pctFueraHorario"] >= 5:
        push(
            "medio",
            "Horas fuera de horario",
            f"{js_str(round2(kpis['horasFueraHorario']))} h "
            f"({js_str(round2(kpis['pctFueraHorario']))}%).",
            "Clockify",
        )

    if risks["criticos"]:
        push(
            "alto",
            "Riesgos críticos abiertos",
            f"{len(risks['criticos'])} riesgo(s) requieren atención.",
            "Riesgos",
        )

    if actions["vencidas"]:
        push(
            "alto",
            "Acciones vencidas",
            f"{len(actions['vencidas'])} acción(es) vencidas.",
            "Acciones",
        )

    if not out:
        push(
            "ok",
            "Operación estable",
            "Sin desviaciones relevantes con las reglas actuales.",
            "Auto",
        )

    return out[:MAX_ALERTS]


def health(
    kpis: Mapping[str, Any],
    risks: Mapping[str, Any],
    plan_data: Mapping[str, Any],
) -> JsonObject:
    """Salud del proyecto (_aertymHealth)."""
    effort = 100.0
    consumption = kpis["consumoPct"]
    deviation = kpis["desviacionPts"]

    if consumption > 100:
        effort -= min(40, (consumption - 100) * 0.7 + 15)
    elif deviation > 10:
        effort -= min(30, deviation * 0.8)

    if kpis["pctNoFacturables"] > 20:
        effort -= min(15, (kpis["pctNoFacturables"] - 20) * 0.5 + 5)

    if kpis["pctFueraHorario"] > 5:
        effort -= min(15, (kpis["pctFueraHorario"] - 5) * 0.8 + 4)

    timing = 100.0

    if plan_data.get("filas"):
        timing -= min(
            60, number_or_zero(plan_data.get("vencidosAbiertos")) * 15
        )
        timing -= min(12, number_or_zero(plan_data.get("vencenHoy")) * 4)

        if number_or_zero(plan_data.get("cerradosTotal")) > 0:
            on_time = number_or_zero(plan_data.get("pctCerradosATiempo"))
            timing -= min(30, max(0, 100 - on_time) * 0.3)
    elif kpis["diasRestantes"] is not None and kpis["diasRestantes"] < 0:
        timing -= 40

    cost = max(0, min(100, 100 - max(0, consumption - 100)))
    risk = risks["score"] if risks else 100
    effort_score = max(0, min(100, js_round(effort)))
    timing_score = max(0, min(100, js_round(timing)))
    score = js_round(
        timing_score * 0.25 + effort_score * 0.35 + cost * 0.2 + risk * 0.2,
    )

    return {
        "score": score,
        "label": "Saludable"
        if score >= 80
        else "En seguimiento"
        if score >= 60
        else "En riesgo",
        "dimensiones": {
            "tiempo": timing_score,
            "esfuerzo": effort_score,
            "costo": js_round(cost),
            "riesgo": risk,
        },
    }


def find_project(
    project_rows: Sequence[Mapping[str, Any]],
    project: str,
) -> Mapping[str, Any]:
    """
    Fila del proyecto AER/T&M en Proyectos.

    Raises:
        AerError: Si no existe o no es AER/T&M.
    """
    row = next(
        (
            item
            for item in project_rows
            if text(item.get("ID_Proyecto")) == project
        ),
        None,
    )

    if row is None:
        raise AerError(f'No se encontró "{project}" en Proyectos.')

    service = text(get_flexible_value(row, ["Servicio", "Service"])).upper()

    if service not in AER_SERVICES:
        raise AerError(
            f"El proyecto no es AER/T&M. Servicio detectado: {service}"
        )

    return row


def build_kpis(
    row: Mapping[str, Any],
    entries: Sequence[TimeEntry],
    today: date,
) -> JsonObject:
    """KPIs de horas del proyecto."""
    total = total_hours(entries)
    billable = round2(
        sum(entry.duration_hours for entry in entries if entry.is_billable),
    )
    other = round2(total - billable)
    after_hours = round2(
        sum(entry.duration_hours for entry in entries if is_after_hours(entry)),
    )
    budget = number_or_zero(row.get("Budget_Hrs"))
    start = sheet_date(row.get("Fecha_Inicio"))
    end = sheet_date(row.get("Fecha_Fin_Estimada"))
    elapsed = time_pct(start, end, today)
    consumption = pct(total, budget)

    return {
        "budgetHoras": round2(budget),
        "horasTotales": total,
        "horasFacturables": billable,
        "horasNoFacturables": other,
        "balanceHoras": round2(budget - total),
        "pctFacturables": pct(billable, total),
        "pctNoFacturables": pct(other, total),
        "horasFueraHorario": after_hours,
        "pctFueraHorario": pct(after_hours, total),
        "pctTiempo": elapsed,
        "consumoPct": consumption,
        "desviacionPts": round2(consumption - elapsed),
        "diasRestantes": days_left(end, today),
        "costoReal": round2(
            sum(
                entry.duration_hours * (entry.costing_rate or 0)
                for entry in entries
            ),
        ),
    }


def build_dashboard(
    store: AerStore,
    project_value: object,
    load_hours: HoursLoader,
) -> JsonObject:
    """
    Dashboard completo del proyecto (getDashboardAERTYMProyecto).

    Args:
        store: Hojas AER (tambien lee Proyectos y Recursos).
        project_value: ID del proyecto.
        load_hours: Horas de Clockify del proyecto.

    Returns:
        La respuesta del original.
    """
    project = text(project_value)

    if not project:
        raise AerError("Falta ID de proyecto.")

    row = find_project(
        store.reader.read_as_objects(sheet_names.SHEET_PROJECTS), project
    )
    service = text(get_flexible_value(row, ["Servicio", "Service"])).upper()
    store.ensure_sheets()
    hours = load_hours(project)
    entries = unique_entries(hours.entries)
    today = store.today()
    plan_data = plan.plan_summary(store, project)
    plan_data["tieneDatos"] = bool(plan_data["filas"])
    kpis = build_kpis(row, entries, today)
    plan_data["avancePlanReferencia"] = (
        plan_data["avancePlan"]
        if plan_data["tieneDatos"]
        else kpis["pctTiempo"]
    )
    risks = risks_actions.risks_summary(store, project)
    risks["tieneDatos"] = bool(risks["filas"])
    actions = risks_actions.actions_summary(store, project)
    actions["tieneDatos"] = bool(actions["filas"])
    vacations = people_client.vacations(store, project)
    evaluations = people_client.evaluations(store, project)
    client = people_client.client_summary(store, project, row)
    project_health = health(kpis, risks, plan_data)
    kpis["healthScore"] = project_health["score"]
    kpis["healthLabel"] = project_health["label"]
    kpis["healthDimensiones"] = project_health["dimensiones"]
    kpis["healthFuentes"] = {
        "tiempo": True,
        "esfuerzo": True,
        "costo": True,
        "riesgo": risks["tieneDatos"],
    }
    resource_rows = (
        store.reader.read_as_objects(sheet_names.SHEET_RESOURCES)
        if store.reader.sheet_exists(sheet_names.SHEET_RESOURCES)
        else []
    )

    return {
        "ok": True,
        "backendVersion": BACKEND_VERSION,
        "proyecto": {
            "id": project,
            "nombre": row.get("Nombre") or project,
            "cliente": row.get("Cliente") or "",
            "servicio": "T&M" if service == "TYM" else service,
            "deliveryManager": people_client.delivery_manager(row),
            "estado": row.get("Estado") or "",
            "fechaInicio": safe_iso(row.get("Fecha_Inicio")),
            "fechaFin": safe_iso(row.get("Fecha_Fin_Estimada")),
        },
        "kpis": kpis,
        "alertas": alerts(kpis, risks, actions, plan_data),
        "tareas": tasks(entries),
        "capacidad": capacity(project, resource_rows, entries),
        "detalleRecursos": resource_detail(entries),
        "tendenciaMensual": monthly_trend(entries),
        "registros": entry_details(entries, DETAIL_LIMIT),
        "plan": plan_data,
        "riesgos": risks,
        "acciones": actions,
        "vacaciones": vacations,
        "evaluaciones": evaluations,
        "cliente": client,
        "clockify": clockify_status(hours),
    }


def clockify_status(hours: ClockifyHours) -> JsonObject:
    """Estado de la consulta de Clockify."""
    date_range = hours.date_range

    return {
        "ok": hours.error is None,
        "proyectoClockify": hours.project_name,
        "rango": {
            "fechaInicio": date_range.start_date.isoformat()
            if date_range.start_date
            else None,
            "fechaFin": date_range.end_date.isoformat()
            if date_range.end_date
            else None,
            "fuente": date_range.source,
        }
        if date_range
        else None,
        "error": hours.error,
    }


def entries_in_range(
    project_value: object,
    range_values: tuple[object, object],
    load_hours: HoursLoader,
) -> JsonObject:
    """
    Registros de Clockify entre dos fechas (getRegistrosClockifyAERRango).

    Returns:
        {"ok", "desde", "hasta", "total", "registros"}.
    """
    project = text(project_value)
    start, end = date_iso(range_values[0]), date_iso(range_values[1])

    if not project:
        raise AerError("Falta ID de proyecto.")

    if not start or not end:
        raise AerError("Selecciona fecha desde y hasta.")

    if end < start:
        raise AerError("La fecha Hasta no puede ser menor que Desde.")

    hours = load_hours(project)

    if hours.error is not None:
        raise AerError(hours.error or "No se pudo consultar Clockify.")

    entries = [
        entry
        for entry in unique_entries(hours.entries)
        if (when := moment(entry)) is not None
        and start <= when.strftime("%Y-%m-%d") <= end
    ]

    return {
        "ok": True,
        "desde": start,
        "hasta": end,
        "total": len(entries),
        "registros": entry_details(entries, RANGE_DETAIL_LIMIT),
    }


def safe_hours(load: Callable[[str], Any]) -> HoursLoader:
    """
    Convierte la consulta de Clockify en ClockifyHours.

    Un error de Clockify no detiene el dashboard: queda en clockify.error.
    """

    def loader(project: str) -> ClockifyHours:
        try:
            result = load(project)
        except DashboardError as error:
            return ClockifyHours([], "", None, describe_error(error))

        return ClockifyHours(
            list(result.entries),
            result.project_name,
            result.date_range,
            None,
        )

    return loader
