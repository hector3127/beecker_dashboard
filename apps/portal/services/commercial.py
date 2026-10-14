"""Lectura comercial del backlog, sin escribir ni inventar montos."""

import math
import unicodedata
from collections.abc import Sequence
from typing import Any

from core.utils.cell_types import CellValue
from core.utils.dates import to_datetime


def normalize(value: object) -> str:
    """Normaliza texto comercial sin acentos ni espacios repetidos."""
    text = unicodedata.normalize("NFKD", str(value or "").strip().casefold())
    return " ".join(
        "".join(c for c in text if not unicodedata.combining(c)).split()
    )


def clean(value: object) -> str:
    """Limpia marcadores de valores ausentes de la hoja."""
    text = str(value if value is not None else "").strip()
    return (
        ""
        if normalize(text) in {"(no value)", "no value", "null", "none"}
        else text
    )


def commercial_rows(
    values: Sequence[Sequence[CellValue]],
) -> dict[str, Any]:
    """Lee oportunidades por encabezados de Backlog_Proyectos."""
    header_at = next(
        (
            i
            for i, row in enumerate(values[:12])
            if {"account name", "opportunity name", "opportunity stage"}
            <= {normalize(cell) for cell in row}
        ),
        None,
    )
    if header_at is None:
        raise ValueError(
            "Backlog_Proyectos no contiene los encabezados "
            "comerciales requeridos."
        )
    headers = [normalize(cell) for cell in values[header_at]]
    aliases = {
        "cuenta": ["account name"],
        "oportunidad": ["opportunity name"],
        "manager": ["delivery manager"],
        "etapa": ["opportunity stage"],
        "fechaCierre": [
            "fecha de cierre",
            "fecha de cierre - diario",
            "close date",
            "closing date",
        ],
        "servicio": ["service type"],
        "factura": ["invoice name"],
        "horas": ["total hours"],
        "monto": ["valor", "amount", "deal amount"],
        "moneda": ["currency opportunity", "currency"],
        "duracion": ["duration_service"],
        "account": ["account"],
        "fechaInicio": ["fecha inicio"],
        "stageComercial": ["stage"],
        "cio": ["cio"],
        "calculadora": ["calculadora"],
        "arq": ["arq"],
        "enTiempo": ["en tiempo"],
        "observaciones": ["observaciones"],
        "estimacion": ["estimacion"],
        "seguimiento": ["fecha ultimo seguimiento"],
        "id": ["deal id", "opportunity id", "record id"],
        "probabilidad": [
            "probabilidad",
            "probabilidad (ficticia - prueba)",
            "probability",
        ],
    }
    columns = {
        key: next((i for i, h in enumerate(headers) if h in names), -1)
        for key, names in aliases.items()
    }
    result = []
    for row_number, row in enumerate(values[header_at + 1 :], header_at + 2):

        def cell(key: Any, row: Sequence[CellValue] = row) -> Any:
            index = columns[key]
            return row[index] if 0 <= index < len(row) else ""

        item: dict[str, Any] = {
            key: clean(cell(key))
            for key in columns
            if key not in {"horas", "monto"}
        }
        if not any(item[key] for key in ("cuenta", "oportunidad", "etapa")):
            continue
        moment = to_datetime(cell("fechaCierre"))
        item["fechaCierre"] = moment.date().isoformat() if moment else None
        for key in ("fechaInicio", "seguimiento"):
            moment = to_datetime(cell(key))
            item[key] = moment.date().isoformat() if moment else None
        raw_hours = clean(cell("horas"))
        try:
            hours = float(raw_hours.replace(",", "")) if raw_hours else None
            item["horas"] = (
                hours
                if hours is None or math.isfinite(hours) and hours >= 0
                else None
            )
        except (ValueError, TypeError):
            item["horas"] = None
        raw_amount = clean(cell("monto"))
        try:
            amount = float(raw_amount.replace(",", "")) if raw_amount else None
            item["monto"] = (
                amount
                if amount is None or math.isfinite(amount) and amount >= 0
                else None
            )
        except (ValueError, TypeError):
            item["monto"] = None
        raw_probability = clean(cell("probabilidad"))
        item["probabilidadFicticia"] = "ficticia" in (
            headers[columns["probabilidad"]]
            if columns["probabilidad"] >= 0
            else ""
        )
        try:
            probability = (
                float(raw_probability.replace("%", "").replace(",", "."))
                if raw_probability
                else None
            )
            if (
                probability is not None
                and "%" not in raw_probability
                and 0 < probability <= 1
            ):
                probability *= 100
            item["probabilidad"] = (
                probability
                if probability is None
                or math.isfinite(probability)
                and 0 <= probability <= 100
                else None
            )
        except (ValueError, TypeError):
            item["probabilidad"] = None
        stage = normalize(item["etapa"])
        item["estado"] = (
            "ganada"
            if stage.startswith("closed won")
            else "perdida"
            if stage.startswith("closed lost")
            else "abierta"
        )
        item["fila"] = row_number
        result.append(item)
    return {
        "ok": True,
        "fuente": "Backlog_Proyectos",
        "filas": result,
        "tieneId": columns["id"] >= 0,
        "columnasFaltantes": [
            key for key, index in columns.items() if index < 0
        ],
    }
