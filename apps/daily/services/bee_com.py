"""Centro de comunicacion corporativa (hoja Comunicados)."""

from collections.abc import Mapping
from datetime import datetime
from typing import Any

from apps.daily.services.ixs_store import (
    IxsError,
    IxsStore,
    JsonObject,
    cell,
    write_lock,
)
from core.utils.cell_types import CellValue
from core.utils.dates import to_datetime, to_local_naive
from core.utils.js_values import (
    js_or_text,
    js_str,
)

"""BKD.070.018 - beeCom
Equivale a beeComListar() y beeComGuardar(): lista los comunicados del
mas reciente al mas antiguo y los crea o edita conservando su fecha.
"""

SHEET = "Comunicados"
HEADERS = (
    "UID",
    "Fecha",
    "Título",
    "Resumen",
    "Contenido",
    "Categoría",
    "Importante",
    "Proyecto",
    "Publicado por",
    "Puntos clave",
)
KEY_POINTS_COLUMN = 10
CATEGORIES = ("Aviso", "Lineamiento", "Nuevo proceso", "Cambio", "Otro")
MAX_TITLE = 180
MAX_CONTENT = 20000
MAX_SUMMARY = 350
MAX_SHORT_TEXT = 100
MAX_KEY_POINTS = 5000


def ensure_sheet(store: IxsStore) -> list[list[CellValue]]:
    """
    Crea la hoja si no existe y completa el encabezado "Puntos clave".

    Returns:
        Los valores de la hoja.
    """
    store.writer.ensure_sheet(SHEET, HEADERS)
    rows = store.values(SHEET)

    if not js_str(cell(rows[0] if rows else [], KEY_POINTS_COLUMN - 1)).strip():
        store.writer.write_cell(SHEET, 1, KEY_POINTS_COLUMN, "Puntos clave")
        rows = store.values(SHEET)

    return rows


def date_text(value: CellValue | datetime) -> str:
    """
    Fecha del comunicado como yyyy-MM-dd.

    Sheets entrega las fechas como numero de serie; el texto se deja
    igual, como String(r[1] || '') del original.
    """
    if isinstance(value, datetime):
        return to_local_naive(value).strftime("%Y-%m-%d")

    if isinstance(value, int | float) and not isinstance(value, bool):
        moment = to_datetime(value)
        return moment.strftime("%Y-%m-%d") if moment else ""

    return js_or_text(value)


def list_communications(store: IxsStore) -> JsonObject:
    """
    Comunicados con UID y titulo, del mas reciente al mas antiguo.

    Returns:
        {"ok", "comunicados"}.
    """
    rows = ensure_sheet(store)[1:]
    items = [
        {
            "uid": js_str(cell(row, 0)),
            "fecha": date_text(cell(row, 1)),
            "titulo": js_or_text(cell(row, 2)),
            "resumen": js_or_text(cell(row, 3)),
            "contenido": js_or_text(cell(row, 4)),
            "categoria": js_or_text(cell(row, 5)) or "Aviso",
            "importante": cell(row, 6) is True
            or js_str(cell(row, 6)).lower() == "true",
            "proyecto": js_or_text(cell(row, 7)),
            "autor": js_or_text(cell(row, 8)),
            "puntosClave": js_or_text(cell(row, 9)),
        }
        for row in rows
    ]
    items = [item for item in items if item["uid"] and item["titulo"]]
    items.sort(key=lambda item: str(item["fecha"]), reverse=True)

    return {"ok": True, "comunicados": items}


def save_communication(store: IxsStore, payload_value: object) -> JsonObject:
    """
    Crea o edita un comunicado (beeComGuardar).

    Args:
        store: Hojas de la vista.
        payload_value: titulo, contenido, categoria, uid y demas campos.

    Returns:
        La lista actualizada.

    Raises:
        IxsError: Con los mensajes de validacion del original.
    """
    with write_lock():
        payload: Mapping[str, Any] = (
            payload_value if isinstance(payload_value, dict) else {}
        )
        title = js_or_text(payload.get("titulo")).strip()
        content = js_or_text(payload.get("contenido")).strip()

        if (
            not title
            or len(title) > MAX_TITLE
            or not content
            or len(content) > MAX_CONTENT
        ):
            raise IxsError("Escribe un título y contenido válidos.")

        category = js_or_text(payload.get("categoria")) or "Aviso"

        if category not in CATEGORIES:
            raise IxsError("Categoría inválida.")

        uid = js_or_text(payload.get("uid")).strip()
        rows = ensure_sheet(store)
        target = (
            next(
                (
                    number
                    for number, row in enumerate(rows[1:], start=2)
                    if js_str(cell(row, 0)) == uid
                ),
                0,
            )
            if uid
            else 0
        )

        if uid and not target:
            raise IxsError("Comunicado no encontrado.")

        row = [
            uid or store.new_uid(),
            cell(rows[target - 1], 1) if target else store.now,
            title,
            js_or_text(payload.get("resumen")).strip()[:MAX_SUMMARY],
            content,
            category,
            payload.get("importante") is True,
            js_or_text(payload.get("proyecto")).strip()[:MAX_SHORT_TEXT],
            js_or_text(payload.get("autor")).strip()[:MAX_SHORT_TEXT],
            js_or_text(payload.get("puntosClave")).strip()[:MAX_KEY_POINTS],
        ]

        if target:
            store.writer.write_row(SHEET, target, row)
        else:
            store.writer.append_row(SHEET, row)

    return list_communications(store)
