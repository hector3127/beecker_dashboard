"""Consumo mensual de EVA-04 exclusivamente desde la base de Sheets."""

import math
import re
from collections import Counter, defaultdict
from collections.abc import Mapping
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any

from apps.gse.services.cells import norm
from core.utils.dates import to_datetime

# Categorias que componen Horas Reales en el reporte original.
BASE_TAGS = {
    norm(tag)
    for tag in (
        "Monitoreo",
        "Ajustes L1",
        "Ajustes L2",
        "Atención a cliente",
        "Sesión con cliente",
    )
}
EXTRA_TAGS = {
    norm(tag)
    for tag in (
        "Change Request",
        "Knowledge Transfer",
        "Gestión de equipos",
        "Hora Extra",
    )
}

# Tope mensual de horas que fija cada servicio (Average Limit del EVA-04).
SERVICE_LIMITS = {
    "ROC": 30.0,
    "AER": 160.0,
    "RAAS": 40.0,
    "SAAS": 80.0,
    "TM": 160.0,  # norm() convierte «T&M» y «T & M» en «t m»
    "TYM": 160.0,
}


# Hours Package Limit por defecto cuando la fuente no lo trae.
DEFAULT_PACKAGE_LIMITS = {"RAAS": 80}


def service_key(service: Any) -> str:
    """Servicio sin acentos, espacios ni mayusculas: «RaaS» -> «RAAS»."""
    return norm(service).upper().replace(" ", "")


def service_limit(service: Any) -> float | None:
    """Tope mensual del servicio; None si el servicio no tiene regla."""
    return SERVICE_LIMITS.get(service_key(service))


BOT_TAG = re.compile(r"\s*(\d+)")


def bot_tag(value: Any) -> str:
    """Numero del BOT al inicio de un texto: «3634 - Gestion» -> «3634»."""
    match = BOT_TAG.match(str(value or ""))
    return str(int(match.group(1))) if match else ""


def id_key(value: Any) -> str:
    """Identificador comparable: minusculas, un espacio, sin ceros iniciales.

    Asi «Mexico12» (ROC) y «Mexico012» (Clockify) son el mismo BOT.
    """
    text = " ".join(str(value or "").casefold().split())
    return re.sub(r"(?<=[^\d])0+(?=\d)", "", text)


def task_matches(task: Any, bot: Any) -> bool:
    """La tarea es el BOT o empieza con el, como «AWN.001 - Payne Nickles»."""
    task_id, bot_id = id_key(task), id_key(bot)
    if not bot_id or not task_id.startswith(bot_id):
        return False
    rest = task_id[len(bot_id) :]
    return not rest or not (rest[0].isalnum() or rest[0] == ".")


def task_key(value: Any) -> str:
    """Normaliza espacios y mayusculas sin borrar IDs ni signos."""
    return " ".join(str(value or "").strip().casefold().split())


def number(value: Any) -> float | None:
    """Conserva ceros numericos y distingue celdas sin datos."""
    if value is None or isinstance(value, bool) or str(value).strip() == "":
        return None
    try:
        result = float(Decimal(str(value).strip().replace(",", "")))
    except (InvalidOperation, ValueError, OverflowError):
        return None
    return result if math.isfinite(result) else None


def resolve_month(value: str | None, today: date) -> date:
    """Valida el mes elegido; por defecto usa el mes actual del portal."""
    if not value:
        return today.replace(day=1)
    try:
        result = date.fromisoformat(value + "-01")
    except ValueError as error:
        raise ValueError("El mes debe tener el formato AAAA-MM.") from error
    return result


def monthly_hours(
    values: list[list[Any]], month: date
) -> tuple[dict[str, Decimal], set[str]]:
    """Suma una vez cada registro por tarea, etiquetas y mes de Sheets."""
    return index_month(build_hour_index(values, month.year), month)


def index_month(
    index: dict[str, Any], month: date
) -> tuple[dict[str, Decimal], set[str]]:
    """Consulta un mes agregado sin volver a recorrer la base."""
    key = month.strftime("%Y-%m")
    if key in index["errors"]:
        raise ValueError("Hay horas no numericas en la base del mes elegido.")
    return index["totals"].get(key, {}), index["tasks"]


def build_hour_index(values: list[list[Any]], year: int) -> dict[str, Any]:
    """Agrega doce meses en un recorrido y conserva los errores por mes."""
    aliases = {
        "project": ("Project", "Proyecto"),
        "task": ("Task", "Tarea"),
        "duration": ("Duration (decimal)", "Horas"),
        "day": ("Start Date", "Fecha"),
        "tags": ("Tags", "Etiquetas"),
        "id": ("ID Registro", "Entry ID", "ID"),
        "workspace": ("Workspace",),
    }
    headers = [norm(c) for c in values[0]] if values else []
    cols = {
        name: next(
            (
                headers.index(norm(alias))
                for alias in names
                if norm(alias) in headers
            ),
            -1,
        )
        for name, names in aliases.items()
    }
    if any(cols[name] < 0 for name in ("task", "duration", "day", "tags")):
        raise ValueError(
            "La base de horas necesita Task, Duration (decimal), "
            "Start Date y Tags."
        )
    totals: dict[str, dict[str, Decimal]] = {}
    project_tasks: dict[str, dict[str, dict[str, Decimal]]] = {}
    tasks: set[str] = set()
    projects: set[str] = set()
    seen: dict[str, set[tuple[str, str]]] = defaultdict(set)
    errors: set[str] = set()
    for row in values[1:]:

        def cell(name: str, record: list[Any] = row) -> Any:
            col = cols[name]
            return record[col] if 0 <= col < len(record) else ""

        key = task_key(cell("task"))
        if not key:
            continue
        tasks.add(key)
        project = task_key(cell("project"))
        if project:
            projects.add(project)
        day = to_datetime(cell("day"))
        if day is None or day.year != year:
            continue
        month_key = day.strftime("%Y-%m")
        entry_id = str(cell("id")).strip()
        identity = (str(cell("workspace")), entry_id)
        if entry_id and identity in seen[month_key]:
            continue
        hours = number(cell("duration"))
        if hours is None:
            errors.add(month_key)
            continue
        if entry_id:
            seen[month_key].add(identity)
        # Por proyecto y BOT se cuentan las horas de todas las etiquetas.
        if project:
            by_task = project_tasks.setdefault(month_key, {}).setdefault(
                project, {}
            )
            by_task[key] = by_task.get(key, Decimal(0)) + Decimal(str(hours))
        # Por nombre de tarea (respaldo) solo las categorias de Horas Reales.
        tags = BASE_TAGS | (EXTRA_TAGS if day.month >= 9 else set())
        if norm(cell("tags")) in tags:
            bucket = totals.setdefault(month_key, {})
            bucket[key] = bucket.get(key, Decimal(0)) + Decimal(str(hours))
    return {
        "totals": totals,
        "tasks": tasks,
        "errors": errors,
        "project_tasks": project_tasks,
        "projects": projects,
    }


def index_projects(
    index: dict[str, Any], month: date
) -> tuple[dict[str, dict[str, Decimal]], set[str]]:
    """Horas del mes por proyecto y tarea, y los proyectos vistos en el ano."""
    return (
        index.get("project_tasks", {}).get(month.strftime("%Y-%m"), {}),
        index.get("projects", set()),
    )


def enrich_hours(
    report: dict[str, Any],
    values: list[list[Any]],
    month: date,
    index: dict[str, Any] | None = None,
    project_map: Mapping[str, str] | None = None,
) -> None:
    """
    Cruza proyecto y BOT y calcula tope menos consumo sin ocultar excesos.

    Args:
        report: Resultado de build_eva4.
        values: Hoja de horas (solo si no se pasa el indice).
        month: Mes consultado.
        index: Indice anual de horas.
        project_map: ROC ID (task_key) -> nombre del proyecto en Clockify,
            cuando no se llaman igual (p. ej. por Clockify_Vinculos).
    """
    if index is None:
        index = build_hour_index(values, month.year)
    totals, tasks = index_month(index, month)
    project_tasks, projects = index_projects(index, month)
    bot_counts = Counter(task_key(p["bot_id"]) for p in report["processes"])
    no_task = 0
    missing_limit = 0
    for process in report["processes"]:
        name = task_key(process["process"])
        bot = task_key(process["bot_id"])
        process["bot_label"] = bot_tag(process["bot_id"]) or process["bot_id"]
        project = task_key(process["project_id"])
        project = (project_map or {}).get(project, project)
        bot_id = process["bot_id"] or process["process"]
        if project and project in projects and id_key(bot_id):
            # Proyecto (ROC ID) + BOT: tareas «3634 - ...» o «AMK.001». Si no
            # hay ninguna, vale el nombre exacto del proceso; si tampoco, 0
            # (el proyecto existe en Clockify, igual que la suma del Excel).
            in_project = project_tasks.get(project, {})
            found = [
                hours
                for task, hours in in_project.items()
                if task_matches(task, bot_id)
            ]
            if not found and name in in_project:
                found = [in_project[name]]
            consumed: float | None = float(sum(found, Decimal(0)))
        elif not project:
            # Sin ROC ID no se sabe de que proyecto son las horas: una tarea
            # llamada igual en otro cliente (p. ej. «Isa») no cuenta.
            consumed = None
        else:
            # Un BOT compartido por varios procesos no asigna todo a todos.
            key = (
                name
                if name in tasks
                else (bot if bot_counts[bot] == 1 and bot in tasks else "")
            )
            consumed = float(totals.get(key, Decimal(0))) if key else None
        # El servicio manda; el tope del Sheet solo cubre servicios sin regla.
        limit = service_limit(process["service"])
        if limit is None:
            limit = number(process["average_limit"])
        process["invested_hours"] = (
            round(consumed, 2) if consumed is not None else None
        )
        process["average_limit"] = limit
        if process["package_limit"] in ("", None):
            default = DEFAULT_PACKAGE_LIMITS.get(
                service_key(process["service"])
            )
            if default is not None:
                process["package_limit"] = default
        process["hours_balance"] = (
            round(limit - consumed, 2)
            if limit is not None and consumed is not None
            else None
        )
        no_task += consumed is None
        missing_limit += limit is None
    report["unmatched_tasks"] = no_task
    report["missing_limits"] = missing_limit
    report["month"] = month.strftime("%Y-%m")


def apply_limits(report: dict[str, Any], values: list[list[Any]]) -> None:
    """Lee topes de una tabla del mismo Sheet, sin usar el Excel local."""
    header = next(
        (
            i
            for i, row in enumerate(values[:20])
            if any(norm(c) in {"tope mensual", "average limit"} for c in row)
        ),
        None,
    )
    if header is None:
        return
    headers = [norm(c) for c in values[header]]

    def column(*names: str) -> int:
        return next(
            (headers.index(norm(n)) for n in names if norm(n) in headers), -1
        )

    limit_col = column("Tope Mensual", "Average Limit")
    task_col = column("Process Name", "Task", "Id Bot", "BOT ID")
    client_col = column("Client", "Cliente")
    if task_col < 0:
        return
    limits: dict[tuple[str, str], set[float]] = defaultdict(set)
    for row in values[header + 1 :]:
        if max(task_col, limit_col) >= len(row):
            continue
        limit = number(row[limit_col])
        if limit is None:
            continue
        client = task_key(row[client_col]) if 0 <= client_col < len(row) else ""
        limits[(client, task_key(row[task_col]))].add(limit)
    for process in report["processes"]:
        if number(process["average_limit"]) is not None:
            continue
        client = task_key(process["client"])
        keys = (task_key(process["process"]), task_key(process["bot_id"]))
        matches = set().union(
            *(
                limits.get((who, key), set())
                for who in (client, "")
                for key in keys
            )
        )
        if len(matches) == 1:
            process["average_limit"] = matches.pop()
