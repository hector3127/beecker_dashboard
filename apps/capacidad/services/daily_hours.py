"""Horas reales de Clockify por persona y dia dentro del mes."""

import calendar
import re
from collections.abc import Callable
from datetime import date
from typing import Any

from apps.capacidad.constants import MONTH_PATTERN, SPRINT_SUFFIX
from apps.capacidad.exceptions import CapacityError
from apps.capacidad.services.capacity_text import (
    normalize_capacity_text,
    parse_capacity_number,
)
from apps.clockify.services.time_entry_loader import ProjectReport
from core.exceptions import DashboardError, describe_error
from core.time_entries.models import TimeEntry

"""BKD.050.011 - Horas diarias del proyecto
Equivale a capacidadInstaladaDatosProyecto() y ciRegistroDeVariante_():
- El rango del proyecto se recorta al mes.
- Clockify se consulta con el ID base y la coincidencia estricta.
- Un registro con Task de otra nomenclatura (S2, CR1) no cuenta.
- Un fallo de Clockify nunca se interpreta como cero horas.
"""

JsonObject = dict[str, Any]

ReportLoader = Callable[[str, tuple[date, date], bool], ProjectReport]

NO_TASK = re.compile(r"(sin task|sin tarea|no task)", re.IGNORECASE)
TASK_VARIANT = re.compile(r"(?:^|[^A-Z0-9])(S\d+|CR\d*)(?=\Z|[^A-Z0-9])")
EMPTY_REPORT_NOTICE = (
    " Clockify no devolvió registros visibles en este rango; comprueba "
    "este mismo ID y fechas en su reporte detallado."
)


def build_project_daily_hours(
    project_id: str,
    month: str,
    force_refresh: bool,
    project_range: JsonObject,
    load_report: ReportLoader,
) -> JsonObject:
    """
    Suma las horas de Clockify por persona y dia del mes.

    Args:
        project_id: ID interno del proyecto (puede traer _S2 o _CR1).
        month: Mes solicitado (YYYY-MM), ya validado.
        force_refresh: Ignora la cache de Clockify.
        project_range: Resultado de resolve_project_range().
        load_report: Descarga el reporte estricto de Clockify.

    Returns:
        El mismo objeto que regresaba capacidadInstaladaDatosProyecto().
    """
    range_start = str(project_range.get("inicio") or "")
    range_finish = str(project_range.get("fin") or "")

    try:
        if not project_range.get("ok") or not range_start or not range_finish:
            raise CapacityError(
                str(project_range.get("error") or "")
                or "Falta inicio o fin del proyecto",
            )

        month_start = f"{month}-01"
        month_end = last_day_of_month(month)

        if range_finish < month_start or range_start > month_end:
            return {
                "ok": True,
                "fueraMes": True,
                "inicio": range_start,
                "fin": range_finish,
                "daily": {},
            }

        start = max(range_start, month_start)
        finish = min(range_finish, month_end)
        base_id = read_base_id(project_id)
        report = load_report(
            base_id,
            parse_report_range(start, finish, base_id),
            force_refresh,
        )
        daily = sum_daily_hours(
            [
                entry
                for entry in report.entries
                if entry_matches_variant(project_id, entry, start, finish)
            ],
            month,
        )
    except DashboardError as error:
        return {
            "ok": False,
            "inicio": range_start,
            "fin": range_finish,
            "error": describe_error(error),
        }

    return {
        "ok": True,
        "inicio": range_start,
        "fin": range_finish,
        "azureAviso": "",
        "daily": daily,
        "aviso": build_report_notice(report),
    }


def is_valid_month(month: str) -> bool:
    """
    Indica si el mes tiene el formato YYYY-MM.

    Args:
        month: Texto del mes.

    Returns:
        True si el mes es valido.
    """
    return bool(MONTH_PATTERN.fullmatch(month))


def last_day_of_month(month: str) -> str:
    """
    Calcula el ultimo dia del mes.

    Args:
        month: Mes en formato YYYY-MM.

    Returns:
        La fecha YYYY-MM-DD del ultimo dia.
    """
    year, month_number = int(month[:4]), int(month[5:])
    _, last_day = calendar.monthrange(year, month_number)

    return f"{month}-{last_day:02d}"


def read_base_id(project_id: str) -> str:
    """
    Quita la nomenclatura _S# o _CR# del ID.

    Args:
        project_id: ID interno.

    Returns:
        El ID base.

    Raises:
        CapacityError: Cuando el ID queda vacio.
    """
    base_id = SPRINT_SUFFIX.sub("", project_id.strip()).strip()

    if not base_id:
        raise CapacityError("Escribe el ID del proyecto.")

    return base_id


def parse_report_range(
    start: str,
    finish: str,
    base_id: str,
) -> tuple[date, date]:
    """
    Convierte el rango de texto a fechas.

    Args:
        start: Inicio YYYY-MM-DD.
        finish: Fin YYYY-MM-DD.
        base_id: ID consultado, para el mensaje de error.

    Returns:
        Inicio y fin como fechas.

    Raises:
        CapacityError: Cuando alguna fecha no existe o el rango se
            invierte.
    """
    try:
        start_date = date.fromisoformat(start)
        finish_date = date.fromisoformat(finish)
    except ValueError as error:
        raise CapacityError("Rango de fechas inválido.") from error

    if start_date > finish_date:
        raise CapacityError(
            "La fecha INICIO es posterior a FIN. Revisa las fechas de "
            f"{base_id}.",
        )

    return start_date, finish_date


def entry_day(entry: TimeEntry) -> str:
    """
    Obtiene el dia del registro.

    Args:
        entry: Registro de Clockify.

    Returns:
        La fecha YYYY-MM-DD, o cadena vacia si no tiene inicio.
    """
    if entry.entry_date is None:
        return ""

    return entry.entry_date.strftime("%Y-%m-%d")


def entry_matches_variant(
    project_id: str,
    entry: TimeEntry,
    start: str,
    finish: str,
) -> bool:
    """
    Indica si el registro corresponde a la variante del ID.

    Una Task explicita manda; sin Task el registro entra por su fecha.

    Args:
        project_id: ID interno (puede traer _S2 o _CR1).
        entry: Registro de Clockify.
        start: Primer dia del rango.
        finish: Ultimo dia del rango.

    Returns:
        True si el registro cuenta para la variante.
    """
    day = entry_day(entry)

    if day < start or day > finish:
        return False

    suffix_match = SPRINT_SUFFIX.search(project_id.strip())

    if not suffix_match:
        return True

    task = entry.task_name.strip()

    if not task or NO_TASK.fullmatch(task):
        return True

    variants = TASK_VARIANT.findall(task.upper())

    return bool(variants) and all(
        variant == suffix_match.group(1).upper() for variant in variants
    )


def sum_daily_hours(
    entries: list[TimeEntry],
    month: str,
) -> dict[str, dict[str, float]]:
    """
    Suma las horas por persona normalizada y dia.

    Args:
        entries: Registros de la variante.
        month: Mes solicitado (YYYY-MM).

    Returns:
        Persona normalizada -> dia -> horas.

    Raises:
        CapacityError: Cuando un registro no tiene persona, fecha del
            mes o duracion valida.
    """
    daily: dict[str, dict[str, float]] = {}

    for entry in entries:
        name = normalize_capacity_text(entry.resource_name)
        day = entry_day(entry)
        hours = parse_capacity_number(entry.duration_hours)

        if not name or not day.startswith(month) or hours is None:
            raise CapacityError(
                "Registro Clockify sin persona, fecha o duración válida",
            )

        person_days = daily.setdefault(name, {})
        person_days[day] = (person_days.get(day) or 0) + hours

    return daily


def build_report_notice(report: ProjectReport) -> str:
    """
    Construye el aviso del reporte como obtenerHorasClockifyPorProyecto().

    Args:
        report: Reporte estricto de Clockify.

    Returns:
        El aviso con el proyecto de Clockify y las consultas hechas.
    """
    notice = (
        f"Proyecto Clockify: {report.project.name} "
        f"[{report.project.project_id}]. Reporte detallado: "
        f"{report.request_count} consulta(s)."
    )

    return notice if report.entries else notice + EMPTY_REPORT_NOTICE
