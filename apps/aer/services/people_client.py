"""Vacaciones, evaluaciones y datos del cliente del proyecto AER."""

import re
from collections.abc import Mapping
from datetime import timedelta
from typing import Any

from apps.aer.constants import (
    SHEET_CLIENT_INFO,
    SHEET_CONTACTS,
    SHEET_DOCUMENTS,
    SHEET_EVALUATIONS,
    SHEET_GOVERNANCE,
    SHEET_VACATIONS,
)
from apps.aer.services.aer_values import (
    clamp,
    date_iso,
    date_obj,
    js_round,
    number_or_zero,
    text,
    to_bool,
)
from apps.aer.services.manual_store import AerStore, project_rows
from apps.aer.services.plan import AerError
from core.utils.js_values import js_locale_key
from core.utils.text import get_flexible_value

"""BKD.080.007 - Personas y cliente AER
Equivale a _aertymVacacionesProyecto(), _aertymEvaluacionesProyecto(),
_aertymClienteProyecto() y a guardar/eliminar vacaciones, evaluaciones,
contactos, informacion, gobierno y documentos del cliente.
"""

JsonObject = dict[str, Any]

EVALUATION_DIMENSIONS = (
    "Calidad",
    "Cumplimiento",
    "Comunicacion",
    "Colaboracion",
    "Autonomia",
)
CONTACT_FLAGS = (
    "Es_Decisor",
    "Requerimientos",
    "Aprueba",
    "Valida",
    "Decide",
    "Informado",
)
DELIVERY_MANAGER_KEYS = (
    "Delivery Manager",
    "Delivery Manag",
    "Scrum_Master",
    "Scrum Master",
    "SM",
    "Sponsor",
)
DEFAULT_GOVERNANCE = (
    ("Seguimiento semanal", "Semanal", "PO + Delivery + Cliente", "Teams"),
    ("Comité operativo", "Quincenal", "Sponsor + PO + Delivery", "Correo"),
    ("Comité ejecutivo", "Mensual", "Sponsor + Dirección", "Teams"),
)
MONTHS = (
    "Jan",
    "Feb",
    "Mar",
    "Apr",
    "May",
    "Jun",
    "Jul",
    "Aug",
    "Sep",
    "Oct",
    "Nov",
    "Dec",
)
CHANNEL_SEPARATOR = re.compile(r"[,;|]")
WEEKEND = (5, 6)


def business_days(start: object, end: object) -> int:
    """Dias lunes a viernes entre dos fechas, inclusive."""
    first, last = date_obj(start), date_obj(end)

    if not first or not last or last < first:
        return 0

    return sum(
        1
        for offset in range((last - first).days + 1)
        if (first + timedelta(days=offset)).weekday() not in WEEKEND
    )


def vacations(store: AerStore, project: str) -> JsonObject:
    """Vacaciones del proyecto por fecha de inicio."""
    rows = [
        {
            "uid": text(row.get("UID")),
            "recurso": text(row.get("Recurso")),
            "inicio": date_iso(row.get("Inicio")),
            "fin": date_iso(row.get("Fin")),
            "dias": business_days(row.get("Inicio"), row.get("Fin")),
            "estado": text(row.get("Estado")) or "Aprobada",
            "comentarios": text(row.get("Comentarios")),
            "registradoPor": text(row.get("Registrado_Por")),
            "fechaRegistro": date_iso(row.get("Fecha_Registro")),
        }
        for row in project_rows(store, SHEET_VACATIONS, project)
    ]
    rows.sort(
        key=lambda row: (
            js_locale_key(str(row["inicio"] or "9999-12-31")),
            js_locale_key(str(row["recurso"])),
        ),
    )

    return {"filas": rows}


def evaluation_category(score: object) -> str:
    """Categoria por puntaje (_aertymCategoriaEvaluacion)."""
    value = number_or_zero(score)

    if value >= 90:
        return "Alto desempeño"

    if value >= 80:
        return "Sólido"

    return "En seguimiento" if value >= 70 else "Crítico"


def evaluation_row(row: Mapping[str, Any]) -> JsonObject:
    """Evaluacion como la usa el panel."""
    dimensions = [
        number_or_zero(row.get(name)) for name in EVALUATION_DIMENSIONS
    ]
    score = number_or_zero(row.get("Score"))

    if not score and any(value > 0 for value in dimensions):
        score = js_round(sum(dimensions) / len(dimensions))

    def number(name: str) -> int | float:
        value = number_or_zero(row.get(name))
        return int(value) if value.is_integer() else value

    return {
        "uid": text(row.get("UID")),
        "recurso": text(row.get("Recurso")),
        "fechaEvaluacion": date_iso(row.get("Fecha_Evaluacion")),
        "periodo": text(row.get("Periodo")),
        "evaluador": text(row.get("Evaluador")),
        "score": max(0, min(100, js_round(score))),
        "calidad": number("Calidad"),
        "cumplimiento": number("Cumplimiento"),
        "comunicacion": number("Comunicacion"),
        "colaboracion": number("Colaboracion"),
        "autonomia": number("Autonomia"),
        "categoria": text(row.get("Categoria")) or evaluation_category(score),
        "comentario": text(row.get("Comentario")),
        "planAccion": text(row.get("Plan_Accion")),
        "proximaEvaluacion": date_iso(row.get("Proxima_Evaluacion")),
    }


class Descending(str):
    """Texto que se ordena de mayor a menor."""

    def __lt__(self, other: str) -> bool:
        return js_locale_key(str(self)) > js_locale_key(str(other))


def evaluations(store: AerStore, project: str) -> JsonObject:
    """Evaluaciones del proyecto, la mas reciente primero."""
    rows = [
        evaluation_row(row)
        for row in project_rows(store, SHEET_EVALUATIONS, project)
    ]
    rows.sort(
        key=lambda row: (
            Descending(row["fechaEvaluacion"] or ""),
            js_locale_key(row["recurso"]),
        ),
    )

    return {"filas": rows}


def delivery_manager(project_row: Mapping[str, Any]) -> Any:
    """Delivery Manager de la fila de Proyectos (_aertymDeliveryManager)."""
    value = get_flexible_value(project_row, DELIVERY_MANAGER_KEYS)

    return value if value not in ("", None, 0, False) else ""


def client_info(
    store: AerStore,
    project: str,
    project_row: Mapping[str, Any],
) -> JsonObject:
    """Informacion del cliente (_aertymClienteInfoProyecto)."""
    rows = project_rows(store, SHEET_CLIENT_INFO, project)
    row = rows[0] if rows else {}

    return {
        "uid": text(row.get("UID")),
        "areaPrincipal": text(row.get("Area_Principal")),
        "sponsor": text(row.get("Sponsor")),
        "productOwner": text(row.get("Product_Owner")),
        "correoDistribucion": text(row.get("Correo_Distribucion")),
        "rutaEscalamiento": text(row.get("Ruta_Escalamiento")),
        "canales": text(row.get("Canales")),
        "proximaReunion": date_iso(row.get("Proxima_Reunion")),
        "tipoReunion": text(row.get("Tipo_Reunion")),
        "cliente": text(project_row.get("Cliente")),
        "deliveryManager": delivery_manager(project_row),
    }


def contacts(store: AerStore, project: str) -> list[JsonObject]:
    """Contactos del cliente ordenados por nombre."""
    rows = [
        {
            "uid": text(row.get("UID")),
            "nombre": text(row.get("Nombre")),
            "cargo": text(row.get("Cargo")),
            "rol": text(row.get("Rol")),
            "area": text(row.get("Area")),
            "correo": text(row.get("Correo")),
            "telefono": text(row.get("Telefono")),
            "nivelDecision": text(row.get("Nivel_Decision")) or "Bajo",
            "estado": text(row.get("Estado")) or "Activo",
            "esDecisor": to_bool(row.get("Es_Decisor")),
            "canal": text(row.get("Canal")),
            "alcance": text(row.get("Alcance")),
            "requerimientos": to_bool(row.get("Requerimientos")),
            "aprueba": to_bool(row.get("Aprueba")),
            "valida": to_bool(row.get("Valida")),
            "decide": to_bool(row.get("Decide")),
            "informado": to_bool(row.get("Informado")),
            "notas": text(row.get("Notas")),
        }
        for row in project_rows(store, SHEET_CONTACTS, project)
    ]
    rows.sort(key=lambda row: js_locale_key(str(row["nombre"])))

    return rows


def governance(store: AerStore, project: str) -> list[JsonObject]:
    """Reuniones de gobierno; las tres sugeridas si no hay ninguna."""
    rows = [
        {
            "uid": text(row.get("UID")),
            "reunion": text(row.get("Reunion")),
            "frecuencia": text(row.get("Frecuencia")),
            "participantes": text(row.get("Participantes")),
            "canal": text(row.get("Canal")),
            "notas": text(row.get("Notas")),
        }
        for row in project_rows(store, SHEET_GOVERNANCE, project)
    ]
    rows = [row for row in rows if row["reunion"]]

    if rows:
        return rows

    return [
        {
            "uid": "",
            "reunion": meeting,
            "frecuencia": frequency,
            "participantes": participants,
            "canal": channel,
            "notas": "",
        }
        for meeting, frequency, participants, channel in DEFAULT_GOVERNANCE
    ]


def documents(store: AerStore, project: str) -> list[JsonObject]:
    """Documentos y vinculos del cliente."""
    rows = [
        {
            "uid": text(row.get("UID")),
            "nombre": text(row.get("Nombre")),
            "tipo": text(row.get("Tipo")),
            "url": text(row.get("URL")),
            "accion": text(row.get("Accion")) or "Abrir",
            "notas": text(row.get("Notas")),
        }
        for row in project_rows(store, SHEET_DOCUMENTS, text(project))
    ]

    return [row for row in rows if row["nombre"] or row["url"]]


def client_summary(
    store: AerStore,
    project: str,
    project_row: Mapping[str, Any],
) -> JsonObject:
    """Contactos, informacion, gobierno, documentos y resumen."""
    contact_rows = contacts(store, project)
    info = client_info(store, project, project_row)
    areas = list(
        dict.fromkeys(row["area"] for row in contact_rows if row["area"])
    )
    contact_channels = ", ".join(
        row["canal"] for row in contact_rows if row["canal"]
    )
    channels = [
        part.strip()
        for part in CHANNEL_SEPARATOR.split(
            text(info["canales"] or contact_channels)
        )
        if part.strip()
    ]

    return {
        "contactos": contact_rows,
        "info": info,
        "gobierno": governance(store, project),
        "documentos": documents(store, project),
        "resumen": {
            "contactosClave": sum(
                1 for row in contact_rows if row["estado"].lower() != "inactivo"
            ),
            "decisores": sum(
                1
                for row in contact_rows
                if row["esDecisor"] or row["nivelDecision"].lower() == "alto"
            ),
            "areas": len(areas),
            "canales": len(dict.fromkeys(channels)),
            "proximaReunion": info["proximaReunion"] or "",
        },
    }


def payload_of(value: object) -> dict[str, Any]:
    """Formulario recibido como diccionario."""
    return dict(value) if isinstance(value, dict) else {}


def save_document(store: AerStore, payload_value: object) -> JsonObject:
    """guardarDocumentoClienteAER()."""
    payload = payload_of(payload_value)
    project = text(payload.get("ID_Proyecto"))

    if not project:
        raise AerError("Falta ID de proyecto.")

    if not text(payload.get("Nombre")):
        raise AerError("Captura el nombre del documento o link.")

    if not text(payload.get("URL")):
        raise AerError("Captura la URL o vínculo.")

    uid = store.upsert(
        SHEET_DOCUMENTS,
        {
            "UID": text(payload.get("UID")),
            "ID_Proyecto": project,
            "Nombre": text(payload.get("Nombre")),
            "Tipo": text(payload.get("Tipo") or "Referencia"),
            "URL": text(payload.get("URL")),
            "Accion": text(payload.get("Accion") or "Abrir"),
            "Notas": text(payload.get("Notas")),
        },
    )

    return {"ok": True, "uid": uid, "documentos": documents(store, project)}


def delete_document(
    store: AerStore, uid: object, project: object
) -> JsonObject:
    """eliminarDocumentoClienteAER()."""
    return {
        "ok": store.delete(SHEET_DOCUMENTS, uid),
        "documentos": documents(store, text(project)),
    }


def save_governance(
    store: AerStore,
    project_value: object,
    rows_value: object,
) -> JsonObject:
    """
    Reemplaza las reuniones de gobierno (guardarGobiernoClienteAER).

    Returns:
        {"ok", "gobierno"}.
    """
    project = text(project_value)

    if not project:
        raise AerError("Falta ID_Proyecto.")

    rows = rows_value if isinstance(rows_value, list) else []
    store.ensure_sheets()
    values = store.values(SHEET_GOVERNANCE)

    if len(values) >= 2:
        headers = store.headers(SHEET_GOVERNANCE)

        if "ID_Proyecto" in headers:
            column = headers.index("ID_Proyecto")
            store.delete_rows(
                SHEET_GOVERNANCE,
                [
                    number
                    for number, row in enumerate(values[1:], start=2)
                    if text(row[column] if column < len(row) else "") == project
                ],
            )

    for raw in rows:
        item = raw if isinstance(raw, dict) else {}
        meeting = text(item.get("Reunion") or item.get("reunion"))

        if not meeting:
            continue

        store.upsert(
            SHEET_GOVERNANCE,
            {
                "ID_Proyecto": project,
                "Reunion": meeting,
                "Frecuencia": text(
                    item.get("Frecuencia") or item.get("frecuencia")
                ),
                "Participantes": text(
                    item.get("Participantes") or item.get("participantes"),
                ),
                "Canal": text(item.get("Canal") or item.get("canal")),
                "Notas": text(item.get("Notas") or item.get("notas")),
            },
        )

    return {"ok": True, "gobierno": governance(store, project)}


def save_contact(store: AerStore, payload_value: object) -> JsonObject:
    """guardarContactoAER()."""
    payload = payload_of(payload_value)
    project = text(payload.get("ID_Proyecto"))

    if not project:
        raise AerError("Falta ID_Proyecto.")

    if not text(payload.get("Nombre")):
        raise AerError("Captura el nombre del contacto.")

    payload["Nivel_Decision"] = text(payload.get("Nivel_Decision")) or "Bajo"
    payload["Estado"] = text(payload.get("Estado")) or "Activo"

    for flag in CONTACT_FLAGS:
        payload[flag] = "TRUE" if to_bool(payload.get(flag)) else "FALSE"

    uid = store.upsert(SHEET_CONTACTS, payload)

    return {
        "ok": True,
        "uid": uid,
        "cliente": {"contactos": contacts(store, project)},
    }


def delete_contact(store: AerStore, uid: object, project: object) -> JsonObject:
    """eliminarContactoAER()."""
    return {
        "ok": store.delete(SHEET_CONTACTS, uid),
        "cliente": {"contactos": contacts(store, text(project))},
    }


def save_client_info(store: AerStore, payload_value: object) -> JsonObject:
    """guardarClienteInfoAER(): una sola fila por proyecto."""
    payload = payload_of(payload_value)
    project = text(payload.get("ID_Proyecto"))

    if not project:
        raise AerError("Falta ID_Proyecto.")

    payload["Proxima_Reunion"] = date_iso(payload.get("Proxima_Reunion"))
    current = project_rows(store, SHEET_CLIENT_INFO, project)

    if not text(payload.get("UID")) and current:
        payload["UID"] = text(current[0].get("UID"))

    return {"ok": True, "uid": store.upsert(SHEET_CLIENT_INFO, payload)}


def save_vacation(store: AerStore, payload_value: object) -> JsonObject:
    """guardarVacacionAER()."""
    payload = payload_of(payload_value)
    project = text(payload.get("ID_Proyecto"))

    if not project:
        raise AerError("Falta ID_Proyecto.")

    if not text(payload.get("Recurso")):
        raise AerError("Falta recurso.")

    start, end = date_iso(payload.get("Inicio")), date_iso(payload.get("Fin"))

    if not start or not end:
        raise AerError("Captura Inicio y Fin.")

    if end < start:
        raise AerError("Fin no puede ser menor que Inicio.")

    if not text(payload.get("Estado")):
        payload["Estado"] = "Aprobada"

    if not date_iso(payload.get("Fecha_Registro")):
        payload["Fecha_Registro"] = store.today().isoformat()

    uid = store.upsert(SHEET_VACATIONS, payload)

    return {"ok": True, "uid": uid, "vacaciones": vacations(store, project)}


def delete_vacation(
    store: AerStore, uid: object, project: object
) -> JsonObject:
    """eliminarVacacionAER()."""
    return {
        "ok": store.delete(SHEET_VACATIONS, uid),
        "vacaciones": vacations(store, text(project)),
    }


def save_evaluation(store: AerStore, payload_value: object) -> JsonObject:
    """guardarEvaluacionAER(): puntaje = promedio de las cinco dimensiones."""
    payload = payload_of(payload_value)
    project = text(payload.get("ID_Proyecto"))

    if not project:
        raise AerError("Falta ID_Proyecto.")

    if not text(payload.get("Recurso")):
        raise AerError("Falta recurso.")

    if not date_iso(payload.get("Fecha_Evaluacion")):
        payload["Fecha_Evaluacion"] = store.today().isoformat()

    values = [
        clamp(payload.get(name), 0, 100) for name in EVALUATION_DIMENSIONS
    ]

    for name, value in zip(EVALUATION_DIMENSIONS, values, strict=True):
        payload[name] = value

    payload["Score"] = js_round(sum(values) / len(values))
    payload["Categoria"] = evaluation_category(payload["Score"])

    if not text(payload.get("Periodo")):
        day = date_obj(payload.get("Fecha_Evaluacion"))
        payload["Periodo"] = (
            f"{MONTHS[day.month - 1]} {day.year}" if day else ""
        )

    uid = store.upsert(SHEET_EVALUATIONS, payload)

    return {"ok": True, "uid": uid, "evaluaciones": evaluations(store, project)}


def delete_evaluation(
    store: AerStore, uid: object, project: object
) -> JsonObject:
    """eliminarEvaluacionAER()."""
    return {
        "ok": store.delete(SHEET_EVALUATIONS, uid),
        "evaluaciones": evaluations(store, text(project)),
    }
