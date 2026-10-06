"""Riesgos y acciones del proyecto AER."""

from collections.abc import Callable, Mapping, Sequence
from typing import Any

from apps.aer.constants import SHEET_ACTIONS, SHEET_RISKS
from apps.aer.services.aer_values import (
    date_iso,
    date_obj,
    js_round,
    normalize_state,
    number_or_zero,
    text,
)
from apps.aer.services.manual_store import AerStore, Row, copy_row, project_rows
from apps.aer.services.plan import AerError, field, is_closed
from core.utils.js_values import js_locale_key, js_str

"""BKD.080.006 - Riesgos y acciones AER
Equivale a _aertymRiesgosProyecto(), _aertymAccionesProyecto(), sus
limpiezas de duplicados y guardarRiesgoAER(), guardarAccionAER(),
actualizarCampoAccionAER() y sus lecturas y bajas. Al leer se borran las
filas repetidas del proyecto (se conserva la mas completa), como el
original.
"""

JsonObject = dict[str, Any]

FAR_DATE = "9999-12-31"
ACTION_FIELDS = {
    "accion": "Accion",
    "responsable": "Responsable",
    "fechaInicio": "Fecha_Inicio",
    "fechaLimite": "Fecha_Limite",
    "fechaReal": "Fecha_Real",
    "estado": "Estado",
    "dependencia": "Dependencia",
    "prioridad": "Prioridad",
    "comentarios": "Notas",
}


def risk_key(row: Mapping[str, Any]) -> str:
    """Proyecto + riesgo + responsable + fecha limite."""
    return "|".join(
        [
            text(field(row, "ID_Proyecto", "idProyecto")),
            normalize_state(field(row, "Riesgo", "riesgo")),
            normalize_state(field(row, "Responsable", "responsable")),
            date_iso(field(row, "Fecha_Limite", "fechaLimite")),
        ],
    )


def risk_loose_key(row: Mapping[str, Any]) -> str:
    """Proyecto + riesgo."""
    return "|".join(
        [
            text(field(row, "ID_Proyecto", "idProyecto")),
            normalize_state(field(row, "Riesgo", "riesgo")),
        ],
    )


def risk_completeness(row: Mapping[str, Any]) -> int:
    """Cuantos datos tiene el riesgo."""
    values = [
        field(row, "Impacto", "impacto"),
        field(row, "Probabilidad", "probabilidad"),
        field(row, "Responsable", "responsable"),
        field(row, "Fecha_Limite", "fechaLimite"),
        field(row, "Accion", "accion"),
        field(row, "Estado", "estado"),
        field(row, "Notas", "notas"),
    ]

    return sum(1 for value in values if text(value) != "")


def merge(previous: Row, current: Row, score: Callable[[Row], int]) -> Row:
    """La mas completa (o la de mas abajo si empatan) gana los valores."""
    previous_score, current_score = score(previous), score(current)

    if current_score > previous_score or (
        current_score == previous_score
        and number_or_zero(current.get("_row"))
        > number_or_zero(previous.get("_row"))
    ):
        return {**previous, **current}

    return {**current, **previous}


def dedup_risks(rows: Sequence[Row]) -> list[Row]:
    """Riesgos sin repetir: llave exacta y luego llave flexible."""
    exact: dict[str, Row] = {}

    for row in rows:
        key = risk_key(row)

        if not key.replace("|", "").strip():
            continue

        previous = exact.get(key)
        exact[key] = (
            merge(previous, row, risk_completeness) if previous else row
        )

    loose: dict[str, Row] = {}

    for row in exact.values():
        key = risk_loose_key(row)

        if not key.replace("|", "").strip():
            continue

        previous = loose.get(key)

        if not previous:
            loose[key] = row
            continue

        owners = (
            normalize_state(field(previous, "Responsable", "responsable")),
            normalize_state(field(row, "Responsable", "responsable")),
        )
        dates = (
            date_iso(field(previous, "Fecha_Limite", "fechaLimite")),
            date_iso(field(row, "Fecha_Limite", "fechaLimite")),
        )
        compatible = (
            not owners[0] or not owners[1] or owners[0] == owners[1]
        ) and (not dates[0] or not dates[1] or dates[0] == dates[1])

        if compatible:
            loose[key] = merge(previous, row, risk_completeness)

    return list(loose.values())


def clean_duplicates(
    store: AerStore,
    sheet: str,
    project: str,
    key: Callable[[Row], str],
    score: Callable[[Row], int],
) -> int:
    """
    Borra las filas repetidas del proyecto; queda la mas completa.

    Equivale a _aertymLimpiarDuplicadosRiesgos() y ...Acciones().
    """
    if len(store.values(sheet)) < 2:
        return 0

    groups: dict[str, list[Row]] = {}

    for row in project_rows(store, sheet, project):
        groups.setdefault(key(row), []).append(row)

    rows: list[int] = []

    for group in groups.values():
        if len(group) <= 1:
            continue

        ordered = sorted(
            group,
            key=lambda row: (-score(row), -number_or_zero(row.get("_row"))),
        )
        rows.extend(int(row["_row"]) for row in ordered[1:])

    store.delete_rows(sheet, rows)

    return len(rows)


def risk_score_value(value: object) -> int:
    """3 critico/alto, 2 medio, 1 bajo."""
    state = normalize_state(value)

    if "CRIT" in state or state in ("ALTO", "ALTA"):
        return 3

    return 2 if state in ("MEDIO", "MEDIA") else 1


def sort_by_date(rows: list[JsonObject], date_key: str, name_key: str) -> None:
    """Por fecha (sin fecha al final) y luego por nombre."""
    rows.sort(
        key=lambda row: (
            js_locale_key(str(row[date_key] or FAR_DATE)),
            js_locale_key(str(row[name_key])),
        ),
    )


def risks_summary(store: AerStore, project: str) -> JsonObject:
    """
    Riesgos del proyecto con criticos y puntaje (_aertymRiesgosProyecto).

    Returns:
        {"filas", "activos", "criticos", "score"}.
    """
    clean_duplicates(store, SHEET_RISKS, project, risk_key, risk_completeness)
    rows = [
        {
            "uid": text(row.get("UID")),
            "riesgo": text(row.get("Riesgo")),
            "impacto": text(row.get("Impacto")) or "Medio",
            "probabilidad": text(row.get("Probabilidad")) or "Media",
            "responsable": text(row.get("Responsable")),
            "fechaLimite": date_iso(row.get("Fecha_Limite")),
            "accion": text(row.get("Accion")),
            "estado": text(row.get("Estado")) or "Abierto",
            "notas": text(row.get("Notas")),
        }
        for row in dedup_risks(project_rows(store, SHEET_RISKS, project))
    ]
    sort_by_date(rows, "fechaLimite", "riesgo")
    active = [row for row in rows if not is_closed(row["estado"])]
    critical = [
        row
        for row in active
        if risk_score_value(row["impacto"]) >= 3
        and risk_score_value(row["probabilidad"]) >= 2
    ]
    score = max(
        0,
        100
        - sum(
            risk_score_value(row["impacto"])
            * risk_score_value(row["probabilidad"])
            * 4
            for row in active
        ),
    )

    return {
        "filas": rows,
        "activos": active,
        "criticos": critical,
        "score": js_round(score),
    }


def project_id(value: object, message: str) -> str:
    """ID de proyecto obligatorio."""
    project = text(value)

    if not project:
        raise AerError(message)

    return project


def save_risk(store: AerStore, payload_value: object) -> JsonObject:
    """
    Crea o edita un riesgo (guardarRiesgoAER).

    Returns:
        {"ok", "uid", "duplicadosEliminados", "riesgos"}.
    """
    payload: dict[str, Any] = (
        dict(payload_value) if isinstance(payload_value, dict) else {}
    )
    project = project_id(payload.get("ID_Proyecto"), "Falta ID_Proyecto.")

    if not text(payload.get("Riesgo")):
        raise AerError("Falta Riesgo.")

    if not text(payload.get("UID")):
        key = risk_key(payload)
        match = next(
            (
                row
                for row in dedup_risks(
                    project_rows(store, SHEET_RISKS, project)
                )
                if risk_key(row) == key
            ),
            None,
        )

        if match and text(match.get("UID")):
            payload["UID"] = text(match.get("UID"))

    uid = store.upsert(SHEET_RISKS, payload)
    removed = clean_duplicates(
        store,
        SHEET_RISKS,
        project,
        risk_key,
        risk_completeness,
    )

    return {
        "ok": True,
        "uid": uid,
        "duplicadosEliminados": removed,
        "riesgos": risks_summary(store, project),
    }


def get_risks(store: AerStore, project_value: object) -> JsonObject:
    """getRiesgosAERProyecto()."""
    project = project_id(project_value, "Falta proyecto.")

    return {"ok": True, "riesgos": risks_summary(store, project)}


def clean_risks(store: AerStore, project_value: object) -> JsonObject:
    """limpiarDuplicadosRiesgosAER()."""
    project = project_id(project_value, "Falta proyecto.")
    removed = clean_duplicates(
        store,
        SHEET_RISKS,
        project,
        risk_key,
        risk_completeness,
    )

    return {
        "ok": True,
        "eliminados": removed,
        "riesgos": risks_summary(store, project),
    }


def delete_risk(store: AerStore, uid: object) -> JsonObject:
    """eliminarRiesgoAER()."""
    return {"ok": store.delete(SHEET_RISKS, uid)}


def action_key(row: Mapping[str, Any]) -> str:
    """Proyecto + accion + responsable + fecha limite."""
    return "|".join(
        [
            text(field(row, "ID_Proyecto", "idProyecto")),
            normalize_state(field(row, "Accion", "accion")),
            normalize_state(field(row, "Responsable", "responsable")),
            date_iso(field(row, "Fecha_Limite", "fechaLimite")),
        ],
    )


def action_completeness(row: Mapping[str, Any]) -> int:
    """Cuantos datos tiene la accion."""
    values = [
        field(row, "Fecha_Inicio", "fechaInicio"),
        field(row, "Fecha_Real", "fechaReal"),
        field(row, "Estado", "estado"),
        field(row, "Dependencia", "dependencia"),
        field(row, "Prioridad", "prioridad"),
        field(row, "Notas", "comentarios", "notas"),
    ]

    return sum(1 for value in values if text(value) != "")


def dedup_actions(rows: Sequence[Row]) -> list[Row]:
    """Acciones sin repetir; la mas completa gana."""
    chosen: dict[str, Row] = {}

    for row in rows:
        key = action_key(row)

        if not key.replace("|", "").strip():
            continue

        previous = chosen.get(key)

        if not previous:
            chosen[key] = row
        elif action_completeness(row) > action_completeness(previous):
            chosen[key] = {**previous, **row}
        else:
            chosen[key] = {**row, **previous}

    return list(chosen.values())


def action_state(value: object) -> str:
    """Completado, Detenido, En progreso o Pendiente."""
    state = normalize_state(value)

    if state in ("COMPLETADO", "COMPLETED", "CERRADO", "CLOSED"):
        return "Completado"

    if state in ("DETENIDO", "STUCK", "BLOQUEADO", "BLOCKED"):
        return "Detenido"

    if state in ("EN PROGRESO", "IN PROGRESS", "CURSO"):
        return "En progreso"

    return "Pendiente"


def actions_summary(store: AerStore, project: str) -> JsonObject:
    """
    Acciones del proyecto (_aertymAccionesProyecto).

    Returns:
        {"filas", "abiertas", "vencidas", "completadas", "detenidas"}.
    """
    clean_duplicates(
        store,
        SHEET_ACTIONS,
        project,
        action_key,
        action_completeness,
    )
    rows = [
        {
            "uid": text(row.get("UID")),
            "idProyecto": project,
            "accion": text(row.get("Accion")),
            "responsable": text(row.get("Responsable")),
            "fechaInicio": date_iso(row.get("Fecha_Inicio")),
            "fechaLimite": date_iso(row.get("Fecha_Limite")),
            "fechaReal": date_iso(row.get("Fecha_Real")),
            "estado": action_state(row.get("Estado")),
            "dependencia": text(row.get("Dependencia")),
            "prioridad": text(row.get("Prioridad")) or "Media",
            "riesgoUid": text(row.get("Riesgo_UID")),
            "comentarios": text(row.get("Notas")),
            "notas": text(row.get("Notas")),
            "actualizado": text(row.get("Actualizado")),
        }
        for row in dedup_actions(project_rows(store, SHEET_ACTIONS, project))
    ]
    sort_by_date(rows, "fechaLimite", "accion")
    today = store.today()
    open_rows = [row for row in rows if not is_closed(row["estado"])]

    return {
        "filas": rows,
        "abiertas": open_rows,
        "vencidas": [
            row
            for row in open_rows
            if (limit := date_obj(row["fechaLimite"])) is not None
            and limit < today
        ],
        "completadas": [row for row in rows if is_closed(row["estado"])],
        "detenidas": [
            row
            for row in open_rows
            if normalize_state(row["estado"]) == "DETENIDO"
        ],
    }


def save_action(store: AerStore, payload_value: object) -> JsonObject:
    """
    Crea o edita una accion (guardarAccionAER).

    Returns:
        {"ok", "uid", "acciones"}.
    """
    payload: dict[str, Any] = (
        dict(payload_value) if isinstance(payload_value, dict) else {}
    )
    project = project_id(payload.get("ID_Proyecto"), "Falta ID_Proyecto.")

    if not text(payload.get("Accion")):
        raise AerError("Falta Acción.")

    payload["Estado"] = action_state(payload.get("Estado"))
    payload["Prioridad"] = text(payload.get("Prioridad")) or "Media"

    if payload["Estado"] == "Completado" and not date_iso(
        payload.get("Fecha_Real")
    ):
        payload["Fecha_Real"] = store.today().isoformat()

    if not text(payload.get("UID")):
        key = action_key(payload)
        match = next(
            (
                row
                for row in dedup_actions(
                    project_rows(store, SHEET_ACTIONS, project)
                )
                if action_key(row) == key
            ),
            None,
        )

        if match and text(match.get("UID")):
            payload["UID"] = text(match.get("UID"))

    uid = store.upsert(SHEET_ACTIONS, payload)
    clean_duplicates(
        store, SHEET_ACTIONS, project, action_key, action_completeness
    )

    return {"ok": True, "uid": uid, "acciones": actions_summary(store, project)}


def update_action_field(
    store: AerStore,
    request: tuple[object, object, object, object],
) -> JsonObject:
    """
    Cambia un campo de la accion (actualizarCampoAccionAER).

    Args:
        store: Hojas AER.
        request: ID del proyecto, UID, campo y valor.

    Returns:
        {"ok", "acciones"}.
    """
    project_value, uid_value, field_name, value = request
    project, uid = text(project_value), text(uid_value)

    if not project or not uid:
        raise AerError("Falta proyecto o UID.")

    column = (
        ACTION_FIELDS.get(field_name) if isinstance(field_name, str) else None
    )

    if not column:
        name = "undefined" if field_name is None else js_str(field_name)
        raise AerError(f"Campo no permitido: {name}")

    current = next(
        (
            row
            for row in store.read(SHEET_ACTIONS)
            if text(row.get("UID")) == uid
            and text(row.get("ID_Proyecto")) == project
        ),
        None,
    )

    if current is None:
        raise AerError("No se encontró la acción.")

    payload = copy_row(current)
    payload["UID"] = uid
    payload["ID_Proyecto"] = project
    payload[column] = value

    if field_name == "estado":
        payload["Estado"] = action_state(value)

        if payload["Estado"] == "Completado" and not date_iso(
            payload.get("Fecha_Real")
        ):
            payload["Fecha_Real"] = store.today().isoformat()

        if payload["Estado"] != "Completado":
            payload["Fecha_Real"] = ""

    if field_name == "fechaReal" and date_iso(value):
        payload["Estado"] = "Completado"

    store.upsert(SHEET_ACTIONS, payload)
    clean_duplicates(
        store, SHEET_ACTIONS, project, action_key, action_completeness
    )

    return {"ok": True, "acciones": actions_summary(store, project)}


def get_actions(store: AerStore, project_value: object) -> JsonObject:
    """getAccionesAERProyecto()."""
    project = project_id(project_value, "Falta proyecto.")

    return {"ok": True, "acciones": actions_summary(store, project)}


def clean_actions(store: AerStore, project_value: object) -> JsonObject:
    """limpiarDuplicadosAccionesAER()."""
    project = text(project_value)
    removed = clean_duplicates(
        store,
        SHEET_ACTIONS,
        project,
        action_key,
        action_completeness,
    )

    return {
        "ok": True,
        "eliminados": removed,
        "acciones": actions_summary(store, project),
    }


def delete_action(store: AerStore, uid: object) -> JsonObject:
    """eliminarAccionAER()."""
    return {"ok": store.delete(SHEET_ACTIONS, uid)}
