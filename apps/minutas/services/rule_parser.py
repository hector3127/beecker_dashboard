"""Extraccion por reglas de las notas de Gemini en Google Meet."""

import re
from collections.abc import Sequence
from dataclasses import dataclass, field

from core.utils.cell_types import SheetRow
from core.utils.text import to_text

"""BKD.060.004 - Parser de minutas
Equivale a extraerDatosPorReglas() y limpiarMarkdown():
- El codigo del proyecto sale de la primera linea con AAA.000.
- Los asistentes son los enlaces mailto de la linea "Invitado".
- Proximos pasos son pendientes; Detalles son acuerdos o riesgos segun
  sus palabras clave.
"""

TITLE_CODE = re.compile(r"[A-Z]{2,4}\.\d{2,4}", re.ASCII)
PROJECT_CODE = re.compile(r"([A-Z]{2,5}\.\d{2,4})", re.ASCII)
MAILTO_LINK = re.compile(r"\[([^\]]+)\]\(mailto:[^)]+\)")
MARKDOWN_LINK = re.compile(r"\[([^\]]+)\]\([^)]+\)")
HEADER_SYMBOLS = re.compile(r"[:*#]")
BULLET_PREFIX = re.compile(r"^[*\-]\s*")
OWNER_PREFIX = re.compile(r"^\[([^\]]+)\]\s*(.+)")
TRAILING_TIMESTAMP = re.compile(r"\(\d{1,2}:\d{2}:\d{2}\)\s*\Z", re.ASCII)

SECTION_HEADERS = {
    "resumen": ("resumen", "summary"),
    "proximosPasos": (
        "próximos pasos",
        "proximos pasos",
        "next steps",
        "suggested next steps",
        "elementos de acción",
    ),
    "detalles": ("detalles", "details"),
}
RISK_WORDS = (
    "riesgo",
    "risk",
    "bloqueo",
    "blocker",
    "espera",
    "pendiente de",
    "sin cambios",
    "estancad",
    "retraso",
    "delay",
    "problema",
    "preocupa",
)
MIN_PENDING_LENGTH = 3
MIN_DETAIL_LENGTH = 5


@dataclass(slots=True)
class PendingItem:
    """Pendiente detectado en Proximos pasos."""

    responsible: str
    description: str


@dataclass(slots=True)
class ExtractedMinute:
    """Datos extraidos de una minuta."""

    project_id: str = ""
    summary: str = ""
    attendees: list[str] = field(default_factory=list)
    pending_items: list[PendingItem] = field(default_factory=list)
    risks: list[str] = field(default_factory=list)
    agreements: list[str] = field(default_factory=list)


def js_trim(text: str) -> str:
    """
    Quita espacios como String.trim() de JavaScript (incluye BOM).

    Args:
        text: Texto original.

    Returns:
        El texto sin espacios externos.
    """
    return text.strip().strip("﻿").strip()


def clean_markdown(line: str) -> str:
    """
    Deja solo el texto visible de los enlaces [texto](url).

    Args:
        line: Linea de la minuta.

    Returns:
        La linea limpia.
    """
    return js_trim(MARKDOWN_LINK.sub(r"\1", line))


def extract_by_rules(
    text: str,
    project_rows: Sequence[SheetRow],
) -> ExtractedMinute:
    """
    Extrae proyecto, resumen, asistentes, pendientes, acuerdos y riesgos.

    Args:
        text: Texto completo de la minuta.
        project_rows: Filas de la hoja Proyectos.

    Returns:
        Los datos extraidos.
    """
    lines = [js_trim(line) for line in text.split("\n")]
    lines = [line for line in lines if line]
    code = find_project_code(lines)
    project = find_project(text, code, project_rows)
    sections = split_sections(lines)
    details = [
        detail
        for detail in (
            clean_detail(line) for line in bullets(sections["detalles"])
        )
        if len(detail) > MIN_DETAIL_LENGTH
    ]

    return ExtractedMinute(
        project_id=(
            to_text(project.get("ID_Proyecto")) if project is not None else code
        ),
        summary=" ".join(clean_markdown(line) for line in sections["resumen"]),
        attendees=find_attendees(lines),
        pending_items=[
            item
            for item in (
                parse_pending(line)
                for line in bullets(sections["proximosPasos"])
            )
            if len(item.description) > MIN_PENDING_LENGTH
        ],
        risks=[detail for detail in details if is_risk(detail)],
        agreements=[detail for detail in details if not is_risk(detail)],
    )


def find_project_code(lines: Sequence[str]) -> str:
    """
    Busca el codigo del proyecto en la primera linea que lo contiene.

    Args:
        lines: Lineas de la minuta.

    Returns:
        El codigo (por ejemplo MCC.026), o cadena vacia.
    """
    title = next((line for line in lines if TITLE_CODE.search(line)), "")
    match = PROJECT_CODE.search(title)

    return match.group(1) if match else ""


def find_project(
    text: str,
    code: str,
    project_rows: Sequence[SheetRow],
) -> SheetRow | None:
    """
    Busca el proyecto por codigo y, si no, por nombre en el texto.

    Args:
        text: Texto completo de la minuta.
        code: Codigo detectado.
        project_rows: Filas de la hoja Proyectos.

    Returns:
        La fila del proyecto, o None.
    """
    by_code = next(
        (row for row in project_rows if row.get("ID_Proyecto") == code),
        None,
    )

    if by_code is not None:
        return by_code

    lowered_text = text.lower()

    return next(
        (
            row
            for row in project_rows
            if row.get("Nombre")
            and to_text(row.get("Nombre")).lower() in lowered_text
        ),
        None,
    )


def find_attendees(lines: Sequence[str]) -> list[str]:
    """
    Lee los nombres de los enlaces mailto de la linea "Invitado".

    Args:
        lines: Lineas de la minuta.

    Returns:
        Los nombres de los asistentes.
    """
    guests_line = next(
        (line for line in lines if line.startswith("Invitado")),
        "",
    )

    return [match.group(1) for match in MAILTO_LINK.finditer(guests_line)]


def split_sections(lines: Sequence[str]) -> dict[str, list[str]]:
    """
    Separa la minuta por sus encabezados de una sola linea.

    Args:
        lines: Lineas de la minuta.

    Returns:
        Lineas de resumen, proximosPasos, detalles y otros.
    """
    sections: dict[str, list[str]] = {
        "resumen": [],
        "proximosPasos": [],
        "detalles": [],
        "otros": [],
    }
    current = "otros"

    for line in lines:
        header_text = js_trim(HEADER_SYMBOLS.sub("", line.lower()))
        header_key = next(
            (
                key
                for key, names in SECTION_HEADERS.items()
                if header_text in names
            ),
            None,
        )

        if header_key is None:
            sections[current].append(line)
        else:
            current = header_key

    return sections


def bullets(lines: Sequence[str]) -> list[str]:
    """
    Filtra las lineas de vineta (que empiezan con * o -).

    Args:
        lines: Lineas de una seccion.

    Returns:
        Las vinetas.
    """
    return [line for line in lines if line.startswith(("*", "-"))]


def parse_pending(line: str) -> PendingItem:
    """
    Lee "* [Responsable] descripcion" como pendiente.

    Args:
        line: Vineta de Proximos pasos.

    Returns:
        El pendiente con responsable y descripcion.
    """
    clean_line = BULLET_PREFIX.sub("", line, count=1)
    owner_match = OWNER_PREFIX.match(clean_line)

    if owner_match:
        return PendingItem(owner_match.group(1), js_trim(owner_match.group(2)))

    return PendingItem("", js_trim(clean_line))


def clean_detail(line: str) -> str:
    """
    Limpia una vineta de Detalles: enlaces y timestamp final.

    Args:
        line: Vineta de Detalles.

    Returns:
        El texto del detalle.
    """
    clean_line = clean_markdown(BULLET_PREFIX.sub("", line, count=1))

    return js_trim(TRAILING_TIMESTAMP.sub("", clean_line))


def is_risk(detail: str) -> bool:
    """
    Indica si el detalle menciona una palabra de riesgo.

    Args:
        detail: Texto del detalle.

    Returns:
        True si es riesgo.
    """
    lowered_detail = detail.lower()

    return any(word in lowered_detail for word in RISK_WORDS)
