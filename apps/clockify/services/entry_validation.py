"""Validacion de registros de Clockify (sin tag, fuera de horario, area)."""

import json
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from core.exceptions import DashboardError, describe_error
from core.integrations.claude_client import ClaudeClient, text_blocks
from core.sheets import sheet_names
from core.sheets.protocols import SheetReader, SheetWriter
from core.time_entries.models import TimeEntry
from core.utils.js_values import js_or_text, js_str, js_truthy
from core.utils.text import get_flexible_value, normalize_name

"""BKD.020.013 - Validacion de registros de Clockify
Equivale a obtenerRegistrosMalRegistrados(), obtenerAreasReglas(),
guardarAreaRegla(), eliminarAreaRegla(), limpiarValidacionesIAClockify()
y _validarReglaAreaConIA() de ClockifyService.gs. La regla de area con
Claude existe pero no se usa al validar, igual que en el original.
"""

JsonObject = dict[str, Any]

AREA_RULES_SHEET = "Areas_Reglas"
AREA_RULES_HEADERS = ("Area", "Regla_Texto")
EXAMPLE_RULES = (
    (
        "Developer",
        "El registro debe mencionar el número de ticket o tarea en la "
        "descripción (ej. #1234), y no debe ser una descripción vacía o "
        'genérica como "trabajo".',
    ),
    (
        "QA",
        "El registro debe mencionar el caso de prueba o el módulo que se "
        "está probando. No es válido registrar tiempo con descripciones como "
        '"pruebas" sin más detalle.',
    ),
    (
        "Arquitecto",
        "El bloque de tiempo debe ser de al menos 30 minutos, ya que las "
        "tareas de arquitectura no deberían registrarse en bloques más "
        "cortos.",
    ),
)
VALIDATIONS_SHEET = "Validaciones_IA_Clockify"
VALIDATIONS_HEADERS = ("EntryId", "Cumple", "Motivo", "FechaValidado")
WORK_START_HOUR = 8
WORK_END_HOUR = 18
NO_AREA = "Sin área asignada"
EMPTY_COUNTERS = {"sinTag": 0, "fueraHorario": 0, "reglaArea": 0}
AREA_RULE_TOKENS = 150
RESOURCES_SHEET = sheet_names.SHEET_RESOURCES


@dataclass(frozen=True, slots=True)
class DetailedEntry:
    """Registro con el area del recurso (_obtenerEntradasDetalladasClockify)."""

    entry_id: str
    resource: str
    area: Any
    description: str
    started_at: datetime | None
    ended_at: datetime | None
    hours: float
    tags: tuple[str, ...]


def ensure_area_sheet(reader: SheetReader, writer: SheetWriter) -> None:
    """Crea la hoja de reglas por area con tres ejemplos (_hojaAreasReglas)."""
    if reader.sheet_exists(AREA_RULES_SHEET):
        return

    writer.ensure_sheet(AREA_RULES_SHEET, AREA_RULES_HEADERS)

    for area, rule in EXAMPLE_RULES:
        writer.append_row(AREA_RULES_SHEET, [area, rule])


def list_area_rules(reader: SheetReader, writer: SheetWriter) -> JsonObject:
    """
    Reglas por area (obtenerAreasReglas).

    Si la hoja no existe se crea con los ejemplos y esta vez regresa la
    lista vacia, como el original.
    """
    if not reader.sheet_exists(AREA_RULES_SHEET):
        ensure_area_sheet(reader, writer)
        return {"ok": True, "areas": []}

    return {
        "ok": True,
        "areas": [
            {"area": row.get("Area"), "regla": row.get("Regla_Texto") or ""}
            for row in reader.read_as_objects(AREA_RULES_SHEET)
            if js_truthy(row.get("Area"))
        ],
    }


def area_row_number(reader: SheetReader, area: str) -> int:
    """Fila (base 1) del area, comparando sin mayusculas; 0 si no existe."""
    values = reader.read_values(AREA_RULES_SHEET)

    return next(
        (
            number
            for number, row in enumerate(values[1:], start=2)
            if js_str(row[0] if row else "").strip().lower() == area.lower()
        ),
        0,
    )


def save_area_rule(
    reader: SheetReader,
    writer: SheetWriter,
    area_value: object,
    rule_value: object,
) -> JsonObject:
    """Crea o actualiza la regla de un area (guardarAreaRegla)."""
    area = js_or_text(area_value).strip()

    if not area:
        return {"ok": False, "error": "Falta el nombre del área."}

    ensure_area_sheet(reader, writer)
    rule = js_or_text(rule_value).strip()
    row_number = area_row_number(reader, area)

    if row_number:
        writer.write_cell(AREA_RULES_SHEET, row_number, 2, rule)
    else:
        writer.append_row(AREA_RULES_SHEET, [area, rule])

    return {"ok": True}


def delete_area_rule(
    reader: SheetReader,
    writer: SheetWriter,
    area_value: object,
) -> JsonObject:
    """Elimina la regla de un area (eliminarAreaRegla)."""
    ensure_area_sheet(reader, writer)
    area = "undefined" if area_value is None else js_str(area_value)
    row_number = area_row_number(reader, area.strip())

    if not row_number:
        return {"ok": False, "error": f'No se encontró el área "{area}".'}

    writer.delete_row(AREA_RULES_SHEET, row_number)

    return {"ok": True}


def ensure_validations_sheet(reader: SheetReader, writer: SheetWriter) -> None:
    """Crea Validaciones_IA_Clockify (_hojaValidacionesIA)."""
    if not reader.sheet_exists(VALIDATIONS_SHEET):
        writer.ensure_sheet(VALIDATIONS_SHEET, VALIDATIONS_HEADERS)


def validations_map(
    reader: SheetReader, writer: SheetWriter
) -> dict[str, JsonObject]:
    """Registros ya validados por Claude (_obtenerMapaValidacionesIA)."""
    try:
        ensure_validations_sheet(reader, writer)
        rows = reader.read_as_objects(VALIDATIONS_SHEET)
    except DashboardError:
        return {}

    return {
        js_str(row.get("EntryId")): {
            "cumple": js_str(row.get("Cumple")).strip().upper() == "TRUE",
            "motivo": row.get("Motivo") or "",
        }
        for row in rows
        if js_truthy(row.get("EntryId"))
    }


def clear_validations(reader: SheetReader, writer: SheetWriter) -> JsonObject:
    """Borra el historial de validaciones (limpiarValidacionesIAClockify)."""
    ensure_validations_sheet(reader, writer)
    row_count = len(reader.read_values(VALIDATIONS_SHEET))

    if row_count > 1:
        writer.delete_row_range(VALIDATIONS_SHEET, 2, row_count - 1)

    return {"ok": True}


@dataclass(frozen=True, slots=True)
class AreaRuleContext:
    """Claude, hojas y reloj para validar la regla de area."""

    reader: SheetReader
    writer: SheetWriter
    api_key: str
    model: str
    build_client: Callable[[], ClaudeClient]
    now: datetime


def validate_area_rule(
    context: AreaRuleContext,
    entry: DetailedEntry,
    rule: str,
    done: Mapping[str, JsonObject],
) -> JsonObject | None:
    """
    Pregunta a Claude si el registro cumple la regla de su area.

    Equivale a _validarReglaAreaConIA(): un registro ya validado no se
    vuelve a enviar; el resultado se guarda para siempre.

    Returns:
        {"cumple", "motivo"} o None si no hay regla, key o respuesta valida.
    """
    if not rule:
        return None

    if entry.entry_id in done:
        return dict(done[entry.entry_id])

    if not context.api_key:
        return None

    tags = ", ".join(entry.tags) if entry.tags else "(ninguno)"
    area = js_str(entry.area)
    description = entry.description or "(sin descripción)"
    prompt = (
        "Eres un validador de registros de tiempo de trabajo. La siguiente es "
        f'la REGLA configurada para el área "{area}":\n"{rule}"\n\n'
        "Evalúa si este registro de tiempo CUMPLE la regla:\n"
        f'- Descripción del registro: "{description}"\n'
        f"- Duración: {js_str(float(entry.hours))} horas\n"
        f"- Tags asignados: {tags}\n\n"
        'Responde ÚNICAMENTE un JSON con esta forma exacta: {"cumple": '
        'true/false, "motivo": "explicación breve, máximo 15 palabras"}. '
        "Sin texto adicional ni markdown."
    )

    try:
        response = context.build_client().create_message(
            {
                "model": context.model,
                "max_tokens": AREA_RULE_TOKENS,
                "messages": [{"role": "user", "content": prompt}],
            },
        )

        if response.status_code >= 300:
            return None

        blocks = text_blocks(response.json())
        text = blocks[0] if blocks else ""
        start, end = text.find("{"), text.rfind("}")

        if start == -1 or end == -1:
            return None

        result = json.loads(text[start : end + 1])
    except (DashboardError, ValueError):
        return None

    if not isinstance(result, dict):
        return None

    try:
        ensure_validations_sheet(context.reader, context.writer)
        context.writer.append_row(
            VALIDATIONS_SHEET,
            [
                entry.entry_id,
                js_truthy(result.get("cumple")),
                js_or_text(result.get("motivo")),
                context.now,
            ],
        )
    except DashboardError:
        pass

    return result


def detailed_entries(
    project: str,
    resource_rows: Sequence[Mapping[str, Any]],
    entries: Sequence[TimeEntry],
) -> list[DetailedEntry]:
    """Registros con el area (posicion) de cada recurso en Recursos."""
    area_by_name: dict[str, Any] = {}

    for row in resource_rows:
        if get_flexible_value(row, ["Proyecto"]) != project:
            continue

        name = normalize_name(
            get_flexible_value(
                row,
                [
                    "Nombre del recurso",
                    "Nombre_del_recurso",
                    "Recurso",
                    "Nombre",
                ],
            ),
        )

        if name:
            area_by_name[name] = get_flexible_value(
                row,
                ["Posicion", "Posición", "Rol"],
            )

    return [
        DetailedEntry(
            entry_id=entry.entry_id,
            resource=entry.resource_name,
            area=area_by_name.get(normalize_name(entry.resource_name))
            or NO_AREA,
            description=entry.description,
            started_at=getattr(entry, "started_at", None),
            ended_at=getattr(entry, "ended_at", None),
            hours=entry.duration_hours,
            tags=entry.tags,
        )
        for entry in entries
    ]


def tag_and_schedule_problems(entry: DetailedEntry) -> list[JsonObject]:
    """
    Sin tag (amarillo) y fuera de horario 8-18 h (rojo).

    Equivale a _validarTagYHorario() con la hora local del registro.
    """
    problems: list[JsonObject] = []

    if not entry.tags:
        problems.append(
            {
                "tipo": "sin_tag",
                "color": "amarillo",
                "mensaje": "Sin tag/etiqueta asignada",
            },
        )

    start_hour = entry.started_at.hour if entry.started_at else None
    end_hour = entry.ended_at.hour if entry.ended_at else None
    starts_outside = start_hour is not None and not (
        WORK_START_HOUR <= start_hour < WORK_END_HOUR
    )
    ends_outside = end_hour is not None and not (
        WORK_START_HOUR <= end_hour <= WORK_END_HOUR
    )

    if starts_outside or ends_outside:
        start_text = f"{start_hour}:00" if start_hour is not None else "?"
        end_text = f"{end_hour}:00" if end_hour is not None else "?"
        problems.append(
            {
                "tipo": "fuera_horario",
                "color": "rojo",
                "mensaje": f"Fuera de horario ({start_text} - {end_text})",
            },
        )

    return problems


def bad_entries(
    project_value: object,
    resource_rows: Sequence[Mapping[str, Any]],
    load_hours: Callable[[str], Any],
) -> JsonObject:
    """
    Registros con algun problema y contadores (obtenerRegistrosMalRegistrados).

    Args:
        project_value: ID interno del proyecto.
        resource_rows: Filas de la hoja Recursos.
        load_hours: Horas del proyecto (entries y project_name).

    Returns:
        {"ok", "alertas", "contadores", "proyectoClockify"}.
    """
    project = js_or_text(project_value).strip()

    try:
        hours = load_hours(project)
    except DashboardError as error:
        return {
            "ok": False,
            "error": describe_error(error),
            "alertas": [],
            "contadores": dict(EMPTY_COUNTERS),
        }

    counters = dict(EMPTY_COUNTERS)
    alerts = []

    for entry in detailed_entries(project, resource_rows, hours.entries):
        problems = tag_and_schedule_problems(entry)

        if not problems:
            continue

        for problem in problems:
            if problem["tipo"] == "sin_tag":
                counters["sinTag"] += 1
            elif problem["tipo"] == "fuera_horario":
                counters["fueraHorario"] += 1

        alerts.append(
            {
                "recurso": entry.resource,
                "area": entry.area,
                "descripcion": entry.description,
                "fecha": entry.started_at.strftime("%Y-%m-%d")
                if entry.started_at
                else "",
                "duracionHrs": entry.hours,
                "problemas": problems,
            },
        )

    return {
        "ok": True,
        "alertas": alerts,
        "contadores": counters,
        "proyectoClockify": hours.project_name,
    }
