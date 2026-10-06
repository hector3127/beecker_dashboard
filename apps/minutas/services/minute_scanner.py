"""Escaneo de la carpeta de Drive y registro de minutas nuevas."""

import logging
import time
from dataclasses import dataclass
from datetime import datetime

from apps.minutas.constants import (
    AGREEMENT_SEPARATOR,
    DEFAULT_SENTIMENT,
    MIN_TEXT_LENGTH,
    MINUTE_ID_DOC_CHARS,
    MINUTE_ID_PREFIX,
    MINUTE_SOURCE,
    PROCESS_PROCESS,
    RULE_RISK_ORIGIN,
    SCAN_PROCESS,
)
from apps.minutas.exceptions import DriveRequestError
from apps.minutas.services.drive_folder import DocumentSource, DriveDocument
from apps.minutas.services.rule_parser import extract_by_rules, js_trim
from core.sheets import sheet_names
from core.sheets.audit import append_history, log_automation
from core.sheets.protocols import SheetReader, SheetWriter
from core.utils.cell_types import CellValue
from core.utils.text import to_text

"""BKD.060.006 - Escaneo de minutas
Equivale a escanearMinutasNuevas() y procesarMinuta():
- Solo se procesan los Google Docs creados hoy.
- Cada minuta se guarda en Minutas; sus pendientes en
  Pendientes_Minutas y sus riesgos en Riesgos (con historico).
"""

logger = logging.getLogger(__name__)

RowData = dict[str, CellValue | datetime]


@dataclass(slots=True)
class ScanContext:
    """Dependencias del escaneo."""

    reader: SheetReader
    writer: SheetWriter
    source: DocumentSource
    now: datetime


def scan_new_minutes(context: ScanContext, folder_id: str) -> int:
    """
    Procesa los Google Docs de hoy que no estan en Minutas.

    Args:
        context: Dependencias del escaneo.
        folder_id: Carpeta de Drive con las notas de Gemini.

    Returns:
        Cuantos documentos nuevos se procesaron.

    Raises:
        DriveRequestError: Cuando Drive no permite leer la carpeta.
    """
    started = time.monotonic()

    if not folder_id:
        log_automation(
            context.reader,
            context.writer,
            SCAN_PROCESS,
            "ERROR",
            "Falta configurar CARPETA_MINUTAS_ID",
            None,
            context.now,
        )
        return 0

    # El original compara el ID del documento contra ID_Minuta
    # (MIN-xxxxxxxx), asi que los documentos de hoy se vuelven a procesar
    # en cada escaneo; las filas se actualizan por su ID.
    processed_ids = {
        row.get("ID_Minuta")
        for row in context.reader.read_as_objects(sheet_names.SHEET_MINUTES)
    }
    new_documents = [
        document
        for document in context.source.list_documents(folder_id)
        if document.document_id not in processed_ids
        and document.created_at.date() == context.now.date()
    ]

    for document in new_documents:
        process_minute(context, document)

    log_automation(
        context.reader,
        context.writer,
        SCAN_PROCESS,
        "OK",
        f"{len(new_documents)} minutas nuevas procesadas",
        int((time.monotonic() - started) * 1000) or None,
        context.now,
    )

    return len(new_documents)


def process_minute(context: ScanContext, document: DriveDocument) -> None:
    """
    Lee un documento y guarda la minuta, pendientes y riesgos.

    Args:
        context: Dependencias del escaneo.
        document: Google Doc de la minuta.
    """
    try:
        text = context.source.export_text(document.document_id)
    except DriveRequestError as error:
        log_automation(
            context.reader,
            context.writer,
            PROCESS_PROCESS,
            "ERROR",
            f'No se pudo leer "{document.name}" ({document.document_id}): '
            f"{error.detail}",
            None,
            context.now,
        )
        return

    if not text or len(js_trim(text)) < MIN_TEXT_LENGTH:
        # Documento vacio o que Gemini todavia esta generando.
        return

    extracted = extract_by_rules(
        text,
        context.reader.read_as_objects(sheet_names.SHEET_PROJECTS),
    )
    minute_id = MINUTE_ID_PREFIX + document.document_id[:MINUTE_ID_DOC_CHARS]
    project_id = extracted.project_id or ""
    minute_data: RowData = {
        "ID_Minuta": minute_id,
        "ID_Proyecto": project_id,
        "ID_Sprint": "",
        "Fecha_Reunion": document.created_at,
        "Fuente": MINUTE_SOURCE,
        "Doc_URL": document.url,
        "Asistentes": ", ".join(extracted.attendees),
        "Resumen_IA": extracted.summary,
        "Riesgos_Detectados": "",
        "Pendientes": "",
        "Acuerdos": AGREEMENT_SEPARATOR.join(extracted.agreements),
        "WorkItems_Mencionados": "",
        "Sentimiento_Reunion": DEFAULT_SENTIMENT,
        "Procesado": True,
    }
    context.writer.upsert_row(
        sheet_names.SHEET_MINUTES,
        "ID_Minuta",
        minute_data,
    )

    for index, pending in enumerate(extracted.pending_items):
        context.writer.upsert_row(
            sheet_names.SHEET_MINUTES_PENDING,
            "ID_Pendiente",
            {
                "ID_Pendiente": f"{minute_id}-P{index}",
                "ID_Minuta": minute_id,
                "ID_Proyecto": project_id,
                "Descripcion": pending.description,
                "Responsable": pending.responsible or "",
                "Fecha_Compromiso": "",
                "Prioridad": "Media",
                "Estado": "Abierto",
            },
        )

    for index, risk in enumerate(extracted.risks):
        risk_data: RowData = {
            "ID_Riesgo": f"{minute_id}-R{index}",
            "ID_Proyecto": project_id,
            "Descripcion": risk,
            "Impacto": "Medio",
            "Probabilidad": "Media",
            "Estado": "Abierto",
            "Responsable": "",
            "Fecha_Deteccion": context.now,
            "Fecha_Revision": "",
            "Plan_Mitigacion": "",
            "Origen": RULE_RISK_ORIGIN,
        }
        context.writer.upsert_row(
            sheet_names.SHEET_RISKS,
            "ID_Riesgo",
            risk_data,
        )
        append_history(
            context.reader,
            context.writer,
            sheet_names.SHEET_RISKS_HISTORY,
            risk_data,
            None,
            context.now,
        )

    logger.info("Minuta %s procesada (%s).", minute_id, to_text(project_id))
