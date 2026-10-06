"""Planeacion del proyecto AER: actividades, hitos y compromisos."""

from collections.abc import Mapping, Sequence
from datetime import date
from typing import Any

from apps.aer.constants import MAX_EFFORT, SHEET_PLAN
from apps.aer.services.aer_values import (
    clamp,
    date_iso,
    date_obj,
    js_round,
    normalize_state,
    number_or_zero,
    pct,
    round2,
    text,
)
from apps.aer.services.manual_store import AerStore, Row, copy_row
from core.exceptions import DashboardError
from core.utils.js_values import js_locale_key, js_or, js_truthy

"""BKD.080.005 - Planeacion AER
Equivale a _aertymPlanProyecto(), guardarPlaneacionAER(),
guardarLotePlaneacionAER(), actualizarEsfuerzoPlaneacionAER(),
actualizarEstadoCierrePlaneacionAER(), marcarCierrePlaneacionAER(),
eliminarPlaneacionAER() y eliminarLotePlaneacionAER(). La identidad de una
actividad es proyecto + actividad + responsable + fechas compromiso; los
duplicados fisicos de la misma identidad se limpian al editar.
"""

JsonObject = dict[str, Any]

CLOSED_STATES = frozenset(
    {
        "COMPLETADO",
        "COMPLETED",
        "CERRADO",
        "CLOSED",
        "CANCELADO",
        "CANCELLED",
        "REJECTED",
        "RECHAZADO",
        "NOT APPLICABLE",
        "INACTIVE",
        "INACTIVO",
    },
)
STOPPED_STATES = frozenset(
    {"DETENIDO", "DETENIDA", "PAUSADO", "PAUSADA", "ON HOLD", "HOLD"},
)
VALIDATE_STATES = frozenset(
    {"POR VALIDAR", "VALIDAR", "PENDIENTE VALIDACION", "SIN ASIGNAR"},
)
PROGRESS_STATES = frozenset({"EN PROGRESO", "PROGRESO", "IN PROGRESS", "CURSO"})
RESOLVED_DEPENDENCY = frozenset(
    {"RESUELTA", "RESUELTO", "CERRADA", "CERRADO", "COMPLETADA", "COMPLETADO"},
)
STOPPED_DEPENDENCY = frozenset(
    {"DETENIDA", "DETENIDO", "PAUSADA", "PAUSADO", "HOLD", "ON HOLD"},
)
OPEN_DEPENDENCY = frozenset(
    {"ABIERTA", "ABIERTO", "ACTIVA", "ACTIVO", "EN PROGRESO"},
)
UPCOMING_LIMIT = 6


class AerError(DashboardError):
    """Error del dashboard AER con el mensaje del original."""

    code = "ERR_AER"
    expose_detail = True


def is_closed(value: object) -> bool:
    """Estado cerrado (_aertymEstaCerrado)."""
    return normalize_state(value) in CLOSED_STATES


def plan_state(value: object, real_end: object, progress: object) -> str:
    """Estado canonico de una actividad (_aertymEstadoPlanCanonico)."""
    state = normalize_state(value)

    if (
        is_closed(state)
        or date_iso(real_end)
        or number_or_zero(progress) >= 100
    ):
        return "Completado"

    if state in STOPPED_STATES:
        return "Detenido"

    if state in VALIDATE_STATES:
        return "Por validar"

    if state in PROGRESS_STATES:
        return "En progreso"

    return "Por iniciar"


def dependency_state(
    value: object,
    dependency: object,
    activity_state: object,
    real_end: object,
) -> str:
    """Estado de la dependencia (_aertymEstadoDependenciaCanonico)."""
    if not text(dependency):
        return ""

    state = normalize_state(value)

    if state in RESOLVED_DEPENDENCY:
        return "Resuelta"

    if state in STOPPED_DEPENDENCY:
        return "Detenida"

    if state in OPEN_DEPENDENCY:
        return "Abierta"

    canonical = plan_state(activity_state, real_end, 0)

    if canonical == "Completado":
        return "Resuelta"

    return "Detenida" if canonical == "Detenido" else "Abierta"


def field(row: Mapping[str, Any], *keys: str) -> Any:
    """x.A || x.b (el ultimo aunque sea falso)."""
    value: Any = None

    for key in keys:
        value = row.get(key)

        if js_truthy(value):
            return value

    return value


def identity_key(row: Mapping[str, Any]) -> str:
    """Identidad estable de la actividad (_aertymPlanIdentityKey)."""
    return "|".join(
        [
            text(field(row, "ID_Proyecto", "idProyecto")),
            normalize_state(field(row, "Actividad", "actividad")),
            normalize_state(field(row, "Responsable", "responsable")),
            date_iso(field(row, "Inicio_Plan", "inicioPlan")),
            date_iso(field(row, "Fin_Plan", "finPlan")),
        ],
    )


def completeness(row: Mapping[str, Any]) -> int:
    """Cuantos datos de avance tiene la fila (_aertymPlanCompleteness)."""
    progress = (
        row.get("Avance")
        if row.get("Avance") is not None
        else row.get(
            "avance",
        )
    )
    values = [
        field(row, "Inicio_Real", "inicioReal"),
        field(row, "Fin_Real", "finReal"),
        field(row, "Estado", "estado"),
        field(row, "Notas", "notas"),
        field(row, "Dependencia", "dependencia"),
        "1" if number_or_zero(progress) > 0 else "",
    ]

    return sum(1 for value in values if js_truthy(value))


def updated_value(row: Mapping[str, Any] | None) -> str:
    """Texto de Actualizado."""
    return text(field(row, "Actualizado", "actualizado")) if row else ""


def prefer(first: Row | None, second: Row) -> Row:
    """
    La fila mas reciente, luego la mas completa, luego la de mas abajo.

    Equivale a _aertymPlanPreferir().
    """
    if not first:
        return second

    first_updated, second_updated = updated_value(first), updated_value(second)

    if first_updated != second_updated:
        return second if second_updated > first_updated else first

    first_score, second_score = completeness(first), completeness(second)

    if first_score != second_score:
        return second if second_score > first_score else first

    return (
        second
        if number_or_zero(second.get("_row"))
        > number_or_zero(first.get("_row"))
        else first
    )


def dedup_rows(rows: Sequence[Row]) -> list[Row]:
    """Una fila por identidad (_aertymDedupPlanRows)."""
    chosen: dict[str, Row] = {}

    for row in rows:
        key = identity_key(row)

        if not key.replace("|", "").strip():
            continue

        chosen[key] = prefer(chosen.get(key), row)

    return list(chosen.values())


def keep_uid(
    store: AerStore,
    project: str,
    uid: str,
    identities: Sequence[str],
) -> int:
    """
    Borra los clones fisicos de las identidades salvo el UID canonico.

    Equivale a _aertymConservarUidPlan().
    """
    if len(store.values(SHEET_PLAN)) < 2:
        return 0

    wanted = {identity for identity in identities if identity}

    if not wanted:
        return 0

    rows = [
        int(row["_row"])
        for row in store.read(SHEET_PLAN)
        if text(row.get("ID_Proyecto")) == text(project)
        and identity_key(row) in wanted
        and text(row.get("UID")) != text(uid)
        and row.get("_row")
    ]
    store.delete_rows(SHEET_PLAN, rows)

    return len(rows)


def plan_row(row: Row) -> JsonObject:
    """Fila de la hoja como la usa el panel."""
    real_end = date_iso(row.get("Fin_Real"))
    progress = clamp(row.get("Avance"), 0, 100)
    state = plan_state(row.get("Estado"), real_end, progress)
    effort = clamp(row.get("Orden"), 0, MAX_EFFORT)

    return {
        "uid": text(row.get("UID")),
        "idProyecto": text(row.get("ID_Proyecto")),
        "tipo": text(row.get("Tipo")) or "Actividad",
        "actividad": text(row.get("Actividad")),
        "responsable": text(row.get("Responsable")),
        "inicioPlan": date_iso(row.get("Inicio_Plan")),
        "finPlan": date_iso(row.get("Fin_Plan")),
        "inicioReal": date_iso(row.get("Inicio_Real")),
        "finReal": real_end,
        "avance": progress,
        "estado": state,
        "dependencia": text(row.get("Dependencia")),
        "estadoDependencia": dependency_state(
            row.get("Estado_Dependencia"),
            row.get("Dependencia"),
            state,
            real_end,
        ),
        "notas": text(row.get("Notas")),
        "orden": effort,
        "esfuerzo": effort,
        "actualizado": text(row.get("Actualizado")),
        "_row": row.get("_row"),
    }


def planned_progress(row: Mapping[str, Any], today: date) -> float:
    """Avance esperado por fechas de una actividad."""
    start, end = date_obj(row["inicioPlan"]), date_obj(row["finPlan"])

    if not start or not end or today < start:
        return 0

    if today >= end:
        return 100

    total = max(1, (end - start).days)

    return js_round((today - start).days / total * 1000) / 10


def is_open_commitment(row: Mapping[str, Any]) -> bool:
    """Compromiso abierto que no esta por validar ni detenido."""
    state = row["estado"]

    return not (
        is_closed(state)
        or row["finReal"]
        or normalize_state(state) == "POR VALIDAR"
        or normalize_state(state) == "DETENIDO"
    )


def brief(row: Mapping[str, Any]) -> JsonObject:
    """Detalle corto de un compromiso."""
    return {
        "uid": row["uid"],
        "actividad": row["actividad"],
        "responsable": row["responsable"],
        "fecha": row["finPlan"],
        "estado": row["estado"],
    }


def plan_summary(store: AerStore, project: str) -> JsonObject:
    """
    Planeacion del proyecto con avance y compromisos (_aertymPlanProyecto).

    Args:
        store: Hojas AER.
        project: ID del proyecto.

    Returns:
        Filas, actividades, hitos y metricas de compromisos.
    """
    rows = [
        plan_row(row)
        for row in store.read(SHEET_PLAN)
        if text(row.get("ID_Proyecto")) == project
    ]
    rows = sorted(
        dedup_rows(rows),
        key=lambda row: (
            row["orden"],
            js_locale_key(str(row["inicioPlan"] or row["finPlan"] or "")),
            js_locale_key(str(row["actividad"])),
        ),
    )
    activities = [row for row in rows if normalize_state(row["tipo"]) != "HITO"]
    milestones = [row for row in rows if normalize_state(row["tipo"]) == "HITO"]
    today = store.today()
    planned = (
        round2(
            sum(planned_progress(row, today) for row in activities)
            / len(activities),
        )
        if activities
        else 0
    )
    real = (
        round2(
            sum(number_or_zero(row["avance"]) for row in activities)
            / len(activities)
        )
        if activities
        else 0
    )
    milestone_rows = [
        {**row, "statusCalculado": milestone_status(row, today)}
        for row in milestones
    ]
    commitments = [row for row in rows if row["finPlan"]]
    closed = [
        row for row in commitments if is_closed(row["estado"]) or row["finReal"]
    ]
    on_time = [
        row
        for row in closed
        if date_obj(row["finPlan"])
        and date_obj(row["finReal"])
        and date_obj(row["finReal"]) <= date_obj(row["finPlan"])  # type: ignore[operator]
    ]
    overdue = [
        row
        for row in commitments
        if is_open_commitment(row)
        and date_obj(row["finPlan"])
        and date_obj(row["finPlan"]) < today  # type: ignore[operator]
    ]
    due_today = [
        row
        for row in commitments
        if is_open_commitment(row) and date_obj(row["finPlan"]) == today
    ]
    upcoming = sorted(
        [
            row
            for row in commitments
            if not is_closed(row["estado"])
            and not row["finReal"]
            and date_obj(row["finPlan"])
            and date_obj(row["finPlan"]) >= today  # type: ignore[operator]
        ],
        key=lambda row: js_locale_key(str(row["finPlan"])),
    )[:UPCOMING_LIMIT]

    return {
        "filas": rows,
        "actividades": activities,
        "hitos": milestone_rows,
        "avancePlan": planned,
        "avanceReal": real,
        "desviacion": round2(real - planned),
        "hitosCumplidos": sum(
            1 for row in milestone_rows if row["statusCalculado"] == "En tiempo"
        ),
        "hitosTotal": len(milestones),
        "proximosHitos": sorted(
            [
                row
                for row in milestone_rows
                if row["statusCalculado"] not in ("En tiempo", "Atrasado")
            ],
            key=lambda row: js_locale_key(str(row["finPlan"])),
        )[:UPCOMING_LIMIT],
        "compromisosTotal": len(commitments),
        "cerradosTotal": len(closed),
        "cerradosATiempo": len(on_time),
        "vencidosAbiertos": len(overdue),
        "vencenHoy": len(due_today),
        "vencidosDetalle": [brief(row) for row in overdue],
        "vencenHoyDetalle": [brief(row) for row in due_today],
        "proximosCompromisos": upcoming,
        "pctCerrados": pct(len(closed), len(commitments)),
        "pctCerradosATiempo": pct(len(on_time), len(closed)),
    }


def milestone_status(row: Mapping[str, Any], today: date) -> str:
    """En tiempo, Atrasado, Riesgo o Pendiente."""
    end = date_obj(row["finPlan"])
    finished = (
        is_closed(row["estado"])
        or number_or_zero(row["avance"]) >= 100
        or bool(row["finReal"])
    )

    if finished:
        real = date_obj(row["finReal"]) or end
        return "En tiempo" if not end or not real or real <= end else "Atrasado"

    return "Riesgo" if end and end < today else "Pendiente"


def project_plan_rows(store: AerStore, project: str) -> list[Row]:
    """Filas de AER_Planeacion del proyecto."""
    return [
        row
        for row in store.read(SHEET_PLAN)
        if text(row.get("ID_Proyecto")) == project
    ]


def save_plan(store: AerStore, payload_value: object) -> JsonObject:
    """
    Crea o edita una actividad o hito (guardarPlaneacionAER).

    Args:
        store: Hojas AER.
        payload_value: Fila con los nombres de columna de la hoja.

    Returns:
        {"ok", "uid", "duplicadosEliminados", "plan"}.
    """
    payload: dict[str, Any] = (
        dict(payload_value) if isinstance(payload_value, dict) else {}
    )
    project = text(payload.get("ID_Proyecto"))

    if not project:
        raise AerError("Falta ID_Proyecto.")

    if not text(payload.get("Actividad")):
        raise AerError("Falta Actividad/Hito.")

    payload["Tipo"] = text(payload.get("Tipo")) or "Actividad"
    payload["Estado"] = plan_state(
        payload.get("Estado"),
        payload.get("Fin_Real"),
        payload.get("Avance"),
    )
    payload["Estado_Dependencia"] = dependency_state(
        payload.get("Estado_Dependencia"),
        payload.get("Dependencia"),
        payload["Estado"],
        payload.get("Fin_Real"),
    )
    payload["Orden"] = clamp(payload.get("Orden"), 0, MAX_EFFORT)

    if payload["Estado"] == "Completado":
        if not date_iso(payload.get("Fin_Real")):
            payload["Fin_Real"] = store.today().isoformat()

        payload["Avance"] = 100
    else:
        payload["Fin_Real"] = ""
        payload["Inicio_Real"] = ""
        payload["Avance"] = 0

    existing = project_plan_rows(store, project)
    uid_value = text(payload.get("UID"))
    original: Row | None = None

    if uid_value:
        original = next(
            (row for row in existing if text(row.get("UID")) == uid_value),
            None,
        )
    else:
        identity = identity_key(payload)
        candidates = [row for row in existing if identity_key(row) == identity]

        for candidate in candidates:
            original = prefer(original, candidate)

        if original and text(original.get("UID")):
            payload["UID"] = text(original.get("UID"))

    previous_identity = identity_key(original) if original else ""
    new_identity = identity_key(payload)
    uid = store.upsert(SHEET_PLAN, payload)
    removed = keep_uid(store, project, uid, [previous_identity, new_identity])

    return {
        "ok": True,
        "uid": uid,
        "duplicadosEliminados": removed,
        "plan": plan_summary(store, project),
    }


def clean_plan_duplicates(store: AerStore, project_value: object) -> int:
    """
    Deja una fila por identidad (_aertymLimpiarDuplicadosPlanProyecto).

    Returns:
        Cuantas filas se borraron (0 si algo falla, como el original).
    """
    try:
        project = text(project_value)

        if not project or len(store.values(SHEET_PLAN)) < 3:
            return 0

        groups: dict[str, list[Row]] = {}

        for row in project_plan_rows(store, project):
            groups.setdefault(identity_key(row), []).append(row)

        rows: list[int] = []

        for group in groups.values():
            if len(group) <= 1:
                continue

            ordered = sorted(
                group,
                key=lambda row: (
                    -completeness(row),
                    descending(text(row.get("Actualizado"))),
                    -number_or_zero(row.get("_row")),
                ),
            )
            rows.extend(
                int(row["_row"]) for row in ordered[1:] if row.get("_row")
            )

        store.delete_rows(SHEET_PLAN, rows)
    except DashboardError:
        return 0

    return len(rows)


class descending(str):  # noqa: N801 - llave de orden inversa
    """Texto que se ordena de mayor a menor (localeCompare inverso)."""

    def __lt__(self, other: str) -> bool:
        return js_locale_key(str(self)) > js_locale_key(str(other))


def save_plan_batch(
    store: AerStore,
    project_value: object,
    items_value: object,
) -> JsonObject:
    """
    Importa varias actividades (guardarLotePlaneacionAER).

    Returns:
        Conteos de recibidos, guardados, nuevos, actualizados, omitidos y
        duplicados eliminados.
    """
    project = text(project_value)

    if not project:
        raise AerError("Falta proyecto.")

    items = items_value if isinstance(items_value, list) else []

    if not items:
        raise AerError("No se recibieron filas para importar.")

    existing_uids = {
        identity_key(row): text(row.get("UID"))
        for row in dedup_rows(project_plan_rows(store, project))
    }
    counts = {"guardados": 0, "omitidos": 0, "actualizados": 0, "nuevos": 0}

    for raw in items:
        item: dict[str, Any] = raw if isinstance(raw, dict) else {}

        if not text(item.get("Actividad")):
            counts["omitidos"] += 1
            continue

        item["ID_Proyecto"] = project

        if not js_truthy(item.get("Tipo")):
            item["Tipo"] = "Actividad"

        if item.get("Orden") in ("", None):
            item["Orden"] = 0

        if item.get("Avance") in ("", None):
            item["Avance"] = 0

        default_state = (
            "Completado"
            if number_or_zero(js_or(item.get("Avance"), 0)) >= 100
            else "Por iniciar"
        )
        item["Estado"] = plan_state(
            js_or(item.get("Estado"), default_state),
            item.get("Fin_Real"),
            item.get("Avance"),
        )
        key = identity_key(item)

        if text(item.get("UID")):
            counts["actualizados"] += 1
        elif existing_uids.get(key):
            item["UID"] = existing_uids[key]
            counts["actualizados"] += 1
        else:
            counts["nuevos"] += 1

        existing_uids[key] = store.upsert(SHEET_PLAN, item)
        counts["guardados"] += 1

    return {
        "ok": True,
        "recibidos": len(items),
        "guardados": counts["guardados"],
        "nuevos": counts["nuevos"],
        "actualizados": counts["actualizados"],
        "omitidos": counts["omitidos"],
        "duplicadosEliminados": clean_plan_duplicates(store, project),
    }


def find_plan_row(
    store: AerStore,
    project: str,
    uid: str,
    required: Sequence[str],
) -> tuple[list[str], Row, list[Row]]:
    """
    Fila del UID en el proyecto con los encabezados de AER_Planeacion.

    Raises:
        AerError: Si falta la hoja, una columna o la fila.
    """
    if len(store.values(SHEET_PLAN)) < 2:
        raise AerError("No existe AER_Planeacion.")

    headers = store.headers(SHEET_PLAN)

    if any(name not in headers for name in required):
        raise AerError(
            "AER_Planeacion no tiene las columnas requeridas para Esfuerzo."
            if "Orden" in required
            else "AER_Planeacion no tiene las columnas requeridas.",
        )

    rows = store.read(SHEET_PLAN)
    target = next(
        (
            row
            for row in rows
            if text(row.get("UID")) == uid
            and text(row.get("ID_Proyecto")) == project
        ),
        None,
    )

    if target is None:
        raise AerError(
            "No se encontró la actividad seleccionada."
            if "Orden" in required
            else "No se encontró el compromiso seleccionado.",
        )

    return headers, target, rows


def write_cells(
    store: AerStore,
    row_number: int,
    headers: Sequence[str],
    values: Mapping[str, Any],
) -> None:
    """Escribe celdas de la fila por encabezado (si la columna existe)."""
    for name, value in values.items():
        if name in headers:
            store.writer.write_cell(
                SHEET_PLAN, row_number, headers.index(name) + 1, value
            )


def update_effort(
    store: AerStore,
    project_value: object,
    uid_value: object,
    effort_value: object,
) -> JsonObject:
    """
    Cambia solo el esfuerzo 0-6 (actualizarEsfuerzoPlaneacionAER).

    Returns:
        {"ok", "uid", "esfuerzo", "plan"}.
    """
    project, uid = text(project_value), text(uid_value)
    effort = clamp(effort_value, 0, MAX_EFFORT)

    if not project:
        raise AerError("Falta ID_Proyecto.")

    if not uid:
        raise AerError("Falta UID.")

    store.ensure_sheets()
    headers, target, _ = find_plan_row(
        store,
        project,
        uid,
        ("UID", "ID_Proyecto", "Orden"),
    )
    write_cells(
        store,
        int(target["_row"]),
        headers,
        {"Orden": effort, "Actualizado": store.now_text()},
    )

    return {
        "ok": True,
        "uid": uid,
        "esfuerzo": effort,
        "plan": plan_summary(store, project),
    }


def update_close_state(
    store: AerStore,
    request: tuple[object, object, object, object],
) -> JsonObject:
    """
    Cambia estado y fecha de cierre (actualizarEstadoCierrePlaneacionAER).

    Se actualizan todas las filas fisicas de la misma actividad y luego se
    borran los clones.

    Args:
        store: Hojas AER.
        request: ID del proyecto, UID, estado y fecha de cierre.

    Returns:
        {"ok", "uid", "estado", "fechaCierre", "filasActualizadas",
        "duplicadosEliminados", "plan"}.
    """
    project_value, uid_value, state_value, close_value = request
    project, uid = text(project_value), text(uid_value)

    if not project:
        raise AerError("Falta ID_Proyecto.")

    if not uid:
        raise AerError("Falta UID.")

    store.ensure_sheets()
    headers, target, rows = find_plan_row(
        store,
        project,
        uid,
        ("UID", "ID_Proyecto", "Estado", "Fin_Real"),
    )
    state = plan_state(state_value, "", 0)
    close_date = date_iso(close_value)

    if state == "Completado":
        close_date = close_date or store.today().isoformat()
    else:
        close_date = ""

    identity = identity_key(target)
    now_text = store.now_text()
    updated = 0

    for row in rows:
        if (
            text(row.get("ID_Proyecto")) != project
            or identity_key(row) != identity
        ):
            continue

        write_cells(
            store,
            int(row["_row"]),
            headers,
            {
                "Estado": state,
                "Fin_Real": close_date,
                "Avance": 100 if state == "Completado" else 0,
                "Actualizado": now_text,
            },
        )
        updated += 1

    removed = keep_uid(store, project, uid, [identity])

    return {
        "ok": True,
        "uid": uid,
        "estado": state,
        "fechaCierre": close_date,
        "filasActualizadas": updated,
        "duplicadosEliminados": removed,
        "plan": plan_summary(store, project),
    }


def mark_closed(
    store: AerStore,
    project_value: object,
    uid_value: object,
    closed_value: object,
) -> JsonObject:
    """
    Marca o desmarca el cierre desde el Roadmap (marcarCierrePlaneacionAER).

    Al reabrir, el estado queda Por validar (sin responsable), En progreso
    (si ya inicio) o Por iniciar.
    """
    project, uid = text(project_value), text(uid_value)
    closed = js_truthy(closed_value)

    if not project:
        raise AerError("Falta ID_Proyecto.")

    if not uid:
        raise AerError("Falta UID.")

    headers, target, _ = find_plan_row(
        store,
        project,
        uid,
        ("UID", "ID_Proyecto", "Estado", "Fin_Real"),
    )
    today = store.today().isoformat()
    start = (
        date_iso(target.get("Inicio_Plan")) if "Inicio_Plan" in headers else ""
    )
    owner = text(target.get("Responsable")) if "Responsable" in headers else ""
    open_state = "Por iniciar"

    if not owner or normalize_state(owner) == "PENDIENTE":
        open_state = "Por validar"
    elif start and start <= today:
        open_state = "En progreso"

    write_cells(
        store,
        int(target["_row"]),
        headers,
        {
            "Estado": "Completado" if closed else open_state,
            "Fin_Real": today if closed else "",
            "Avance": 100 if closed else 0,
            "Actualizado": store.now_text(),
        },
    )

    return {
        "ok": True,
        "uid": uid,
        "cerrado": closed,
        "fechaCierre": today if closed else "",
    }


def delete_plan(store: AerStore, uid_value: object) -> JsonObject:
    """
    Borra la actividad y sus clones (eliminarPlaneacionAER).

    Returns:
        {"ok", "eliminados"} o {"ok": False, "error"}.
    """
    uid = text(uid_value)

    if not uid:
        return {"ok": False, "error": "Falta UID."}

    rows = store.read(SHEET_PLAN)
    target = next((row for row in rows if text(row.get("UID")) == uid), None)

    if target is None:
        return {"ok": False, "error": "No se encontró el registro."}

    identity = identity_key(target)
    numbers = [
        int(row["_row"])
        for row in rows
        if text(row.get("ID_Proyecto")) == text(target.get("ID_Proyecto"))
        and identity_key(row) == identity
        and row.get("_row")
    ]
    store.delete_rows(SHEET_PLAN, numbers)

    return {"ok": True, "eliminados": len(numbers)}


def delete_plan_batch(
    store: AerStore,
    project_value: object,
    uids_value: object,
) -> JsonObject:
    """
    Borra varias actividades y sus clones (eliminarLotePlaneacionAER).

    Returns:
        Conteos de filas y grupos eliminados y UID no encontrados.
    """
    project = text(project_value)
    wanted_list = list(
        dict.fromkeys(
            uid
            for uid in (
                text(item.get("uid"))
                if isinstance(item, dict) and item.get("uid") is not None
                else text(item)
                for item in (uids_value if isinstance(uids_value, list) else [])
            )
            if uid
        ),
    )

    if not project:
        raise AerError("Falta ID_Proyecto.")

    if not wanted_list:
        return {
            "ok": True,
            "eliminados": 0,
            "eliminadosFisicos": 0,
            "gruposEliminados": 0,
            "solicitados": 0,
            "omitidos": 0,
            "mensaje": "No había filas seleccionadas.",
        }

    store.ensure_sheets()

    if len(store.values(SHEET_PLAN)) < 2:
        return {
            "ok": True,
            "eliminados": 0,
            "eliminadosFisicos": 0,
            "gruposEliminados": 0,
            "solicitados": len(wanted_list),
            "omitidos": len(wanted_list),
            "mensaje": "AER_Planeacion no contiene registros.",
        }

    headers = store.headers(SHEET_PLAN)

    if "UID" not in headers or "ID_Proyecto" not in headers:
        raise AerError("AER_Planeacion no tiene UID o ID_Proyecto.")

    wanted = set(wanted_list)
    rows = [
        row
        for row in store.read(SHEET_PLAN)
        if text(row.get("ID_Proyecto")) == project
    ]
    found = {
        text(row.get("UID")) for row in rows if text(row.get("UID")) in wanted
    }
    selected_keys = {
        identity_key(row) for row in rows if text(row.get("UID")) in wanted
    }
    to_delete: list[int] = []
    deleted_keys: set[str] = set()

    for row in rows:
        key = identity_key(row)

        if text(row.get("UID")) in wanted or key in selected_keys:
            to_delete.append(int(row["_row"]))

            if key:
                deleted_keys.add(key)

    store.delete_rows(SHEET_PLAN, to_delete)
    missing = [uid for uid in wanted_list if uid not in found]

    return {
        "ok": True,
        "eliminados": len(to_delete),
        "eliminadosFisicos": len(to_delete),
        "gruposEliminados": len(deleted_keys),
        "solicitados": len(wanted_list),
        "omitidos": len(missing),
        "uidsNoEncontrados": missing,
        "mensaje": (
            f"Se eliminaron {len(to_delete)} fila(s) física(s) de "
            f"{len(deleted_keys)} elemento(s) seleccionado(s)."
            if to_delete
            else "No se encontró ninguna fila física para eliminar."
        ),
    }


def plan_payload(row: Row) -> dict[str, Any]:
    """Copia editable de una fila."""
    return copy_row(row)
