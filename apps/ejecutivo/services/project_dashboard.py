"""Dashboard ejecutivo de un solo proyecto."""

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from apps.dashboard.constants import CATEGORY_CLOSED, CATEGORY_PAUSED
from apps.dashboard.services.project_status import categorize_project_status
from apps.ejecutivo.services.additional_milestones import (
    read_additional_milestones,
)
from apps.ejecutivo.services.history_stages import (
    STATE_COMPLETED,
    StageProgress,
    estimate_stage_progress,
    milestones_from_stages,
    read_history_stages,
)
from apps.ejecutivo.services.project_detail import (
    calculate_elapsed_pct,
    find_project_row,
)
from apps.ejecutivo.services.project_milestones import (
    calculate_project_milestones,
    safe_iso,
)
from core.exceptions import InvalidRequestError
from core.time_entries.models import TimeEntry
from core.utils.cell_types import CellValue, SheetRow
from core.utils.dates import to_datetime
from core.utils.numbers import round_half_up, round_half_up_int, to_number
from core.utils.text import to_text

"""BKD.040.013 - Dashboard ejecutivo del proyecto
Equivale a getDashboardEjecutivoProyecto():
- Burn = horas facturables del proyecto en las horas del portafolio.
- En IXB/RaaS/SaaS el avance sale de las etapas; en el resto, del
  consumo presupuestal.
- El estado general marca riesgo por sobreconsumo, no por eficiencia.
"""

JsonObject = dict[str, Any]

MILESTONE_SERVICES = re.compile(r"^(ixb|raas|saas)$")
IMPACT_ORDER = {"Alto": 3, "Medio": 2, "Bajo": 1}
TOP_RISKS = 5
TOP_RESOURCES = 5
OPEN_STATE = "Abierto"
OVER_BUDGET_PCT = 100
RISK_CONSUMPTION_INDEX = 1.3
WARNING_CONSUMPTION_INDEX = 1.1
MIN_ELAPSED_FOR_PACE = 20
SLOW_PACE_INDEX = 0.9
HISTORY_BLOCK_WIDTH = 9
MIN_HISTORY_ROWS = 2
DATE_RISK_WARNING_DAYS = 15
SECONDS_PER_DAY = 86400


@dataclass(slots=True)
class ExecutiveSources:
    """Datos ya leidos que necesita el dashboard ejecutivo."""

    project_rows: Sequence[SheetRow]
    project_values: Sequence[Sequence[CellValue]]
    history_rows: Sequence[SheetRow]
    history_values: Sequence[Sequence[CellValue]]
    portfolio_entries: Sequence[TimeEntry]
    detail: JsonObject
    risk_rows: Sequence[SheetRow]
    pending_rows: Sequence[SheetRow]
    stage_work_items: Mapping[str, tuple[int, int]] = field(
        default_factory=dict,
    )


@dataclass(slots=True)
class ProgressInfo:
    """Avance, fuente y ritmo del proyecto."""

    pct: float | None
    uses_milestones: bool
    stage_progress: StageProgress | None
    elapsed_pct: float | None
    pace_index: float | None
    consumption_index: float | None


def build_executive_dashboard(
    project_id: str,
    sources: ExecutiveSources,
    now: datetime,
) -> JsonObject:
    """
    Construye el dashboard ejecutivo de un proyecto.

    Args:
        project_id: ID exacto del proyecto en la hoja Proyectos.
        sources: Datos ya leidos.
        now: Fecha y hora local actual.

    Returns:
        El mismo objeto que regresaba getDashboardEjecutivoProyecto().

    Raises:
        InvalidRequestError: Cuando el proyecto no esta en Proyectos.
    """
    project = find_project_row(sources.project_rows, project_id)

    if project is None:
        raise InvalidRequestError(
            f'No se encontro el proyecto "{project_id}" en la hoja Proyectos.',
        )

    project_entries = [
        entry
        for entry in sources.portfolio_entries
        if entry.project_id == project_id
    ]
    budget = to_number(project.get("Budget_Hrs"))
    burn = round_half_up(
        sum(
            entry.duration_hours
            for entry in project_entries
            if entry.is_billable
        ),
        2,
    )
    raw_consumption_pct = round_half_up(burn / budget * 100, 1) if budget else 0
    executed_pct = min(100, raw_consumption_pct)
    milestones = load_milestones(project, project_id, sources, now)
    phases: list[JsonObject] = milestones.get("lista") or []
    progress = calculate_progress(
        project,
        milestones,
        phases,
        (executed_pct, raw_consumption_pct),
        now,
        sources.stage_work_items,
    )
    general_status, status_color = calculate_general_status(
        project,
        raw_consumption_pct,
        progress,
    )
    risks = [
        row
        for row in sources.risk_rows
        if row.get("ID_Proyecto") == project_id
        and row.get("Estado") == OPEN_STATE
    ]
    detail = sources.detail
    resource_rows: list[JsonObject] = detail.get("filas") or []
    totals: JsonObject = detail.get("totales") or {}

    return {
        "proyecto": {
            "id": project_id,
            "nombre": project.get("Nombre") or project_id,
            "cliente": project.get("Cliente") or "",
            "sponsor": project.get("Sponsor") or "",
            "pm": project.get("Scrum_Master") or "",
            "deliveryManager": milestones.get("deliveryManager") or "",
            "fechaCorte": safe_iso(now),
            "fechaInicio": safe_iso(project.get("Fecha_Inicio")),
            "fechaFinEstimada": safe_iso(project.get("Fecha_Fin_Estimada")),
            "estadoGeneral": general_status,
            "estadoColor": status_color,
            "nivelRiesgoFecha": calculate_date_risk(
                project.get("Fecha_Fin_Estimada"),
                now,
            ),
        },
        "avance": {
            "pct": progress.pct,
            "fuente": progress_source(progress, phases),
            "hitosCompletados": sum(
                1
                for phase in phases
                if to_text(phase.get("estado") or "").lower()
                == STATE_COMPLETED.lower()
            ),
            "hitosTotal": len(phases),
            "etapaActualPct": (
                progress.stage_progress.current_stage_pct
                if progress.stage_progress
                else None
            ),
            "pctTiempoTranscurrido": progress.elapsed_pct,
            "indiceRitmo": progress.pace_index,
        },
        "presupuesto": {
            "budget": budget,
            "burn": burn,
            "etc": round_half_up(budget - burn, 2),
            "pctEjecutado": executed_pct,
            "pctConsumoRaw": raw_consumption_pct,
            "fuente": "Registros_Tiempo",
            "consumoDisponible": len(project_entries) > 0,
            "registros": len(project_entries),
        },
        "kpisExtra": build_extra_kpis(resource_rows, detail),
        "distribucionArea": detail.get("distribucionCategoria") or [],
        "filasRecursosTop": sorted(
            resource_rows,
            key=lambda row: -row["horasReales"],
        )[:TOP_RESOURCES],
        "filasRecursosCompleto": resource_rows,
        "totalesRecursos": totals,
        "porRol": detail.get("porRol") or [],
        "riesgosCriticos": select_critical_risks(risks),
        "raid": {
            "riesgosCriticos": len(risks),
            "asuntosPendientes": sum(
                1
                for row in sources.pending_rows
                if row.get("ID_Proyecto") == project_id
                and row.get("Estado") == OPEN_STATE
            ),
        },
        "hitos": phases,
        "hitosAdicionales": read_additional_milestones(
            sources.project_values,
            project_id,
        ),
        "proximosHitos": milestones.get("proximos") or [],
        "periodosSuspension": milestones.get("periodosSuspension") or [],
        "historialCompleto": milestones.get("historialCompleto") or [],
        "suspensiones": milestones.get("suspensiones") or [],
    }


def read_service(project: SheetRow, milestones: JsonObject) -> str:
    """
    Servicio del proyecto: el del historico o el de Proyectos.

    Args:
        project: Fila de Proyectos.
        milestones: Hitos del historico.

    Returns:
        El servicio en minusculas.
    """
    service = (
        milestones.get("servicio")
        or project.get("Servicio")
        or project.get("Service")
        or ""
    )

    return to_text(service).strip().lower()


def load_milestones(
    project: SheetRow,
    project_id: str,
    sources: ExecutiveSources,
    now: datetime,
) -> JsonObject:
    """
    Calcula los hitos; IXB/RaaS sin hitos usa las etapas A:I.

    Args:
        project: Fila de Proyectos.
        project_id: ID del proyecto.
        sources: Datos ya leidos.
        now: Fecha y hora local actual.

    Returns:
        Los hitos con la forma de calcularHitosProyecto().
    """
    milestones = calculate_project_milestones(
        read_history_block_rows(sources),
        project_id,
        now,
    ).to_json()

    if not MILESTONE_SERVICES.match(read_service(project, milestones)):
        return milestones

    if milestones["lista"]:
        return milestones

    stages = read_history_stages(sources.history_values, project_id)

    if stages is None or not stages.milestones:
        return milestones

    return milestones_from_stages(stages, milestones, now.date())


def read_history_block_rows(sources: ExecutiveSources) -> list[SheetRow]:
    """
    Filas del historico solo con las columnas A:I, por posicion.

    La hoja comparte espacio con la tabla de proyectos (columnas K en
    adelante, con Project ID y Service repetidos). Si se leyera toda la
    fila por encabezado, esos valores pisarian a los del historico.

    Args:
        sources: Datos ya leidos.

    Returns:
        Las filas A:I como diccionarios; las filas por encabezado
        originales cuando no hay valores crudos.
    """
    values = sources.history_values

    if len(values) < MIN_HISTORY_ROWS:
        return list(sources.history_rows)

    headers = [to_text(header) for header in values[0][:HISTORY_BLOCK_WIDTH]]

    return [
        {
            header: row[index] if index < len(row) else ""
            for index, header in enumerate(headers)
        }
        for row in values[1:]
        if any(cell not in ("", None) for cell in row[:HISTORY_BLOCK_WIDTH])
    ]


def calculate_progress(
    project: SheetRow,
    milestones: JsonObject,
    phases: list[JsonObject],
    consumption: tuple[float, float],
    now: datetime,
    work_items: Mapping[str, tuple[int, int]] | None = None,
) -> ProgressInfo:
    """
    Calcula avance, tiempo transcurrido e indices de ritmo y consumo.

    Args:
        project: Fila de Proyectos.
        milestones: Hitos del proyecto.
        phases: Lista de hitos.
        consumption: Porcentaje ejecutado (tope 100) y consumo real.
        now: Fecha y hora local actual.
        work_items: Work items (cerrados, total) por etapa en Azure.

    Returns:
        El avance y sus indices.
    """
    executed_pct, raw_consumption_pct = consumption
    uses_milestones = bool(
        MILESTONE_SERVICES.match(read_service(project, milestones)),
    )
    stage_progress = (
        estimate_stage_progress(phases, now, work_items)
        if uses_milestones
        else None
    )
    progress_pct = (
        stage_progress.pct if stage_progress is not None else executed_pct
    )
    elapsed_pct = calculate_elapsed_pct(
        project.get("Fecha_Inicio"),
        project.get("Fecha_Fin_Estimada"),
        now,
    )
    numerator = progress_pct if uses_milestones else raw_consumption_pct
    has_elapsed = elapsed_pct is not None and elapsed_pct > 0

    return ProgressInfo(
        pct=progress_pct,
        uses_milestones=uses_milestones,
        stage_progress=stage_progress,
        elapsed_pct=elapsed_pct,
        pace_index=(
            round_half_up(numerator / elapsed_pct, 2)
            if numerator is not None and has_elapsed and elapsed_pct
            else None
        ),
        consumption_index=(
            raw_consumption_pct / elapsed_pct
            if has_elapsed and elapsed_pct
            else None
        ),
    )


def calculate_general_status(
    project: SheetRow,
    raw_consumption_pct: float,
    progress: ProgressInfo,
) -> tuple[str, str]:
    """
    Estado general y color: el sobreconsumo es riesgo, no la eficiencia.

    Args:
        project: Fila de Proyectos.
        raw_consumption_pct: Consumo real del presupuesto.
        progress: Avance e indices.

    Returns:
        El estado general y su color.
    """
    category = categorize_project_status(project.get("Estado"))
    consumption_index = progress.consumption_index

    if category == CATEGORY_CLOSED:
        return "CERRADO", "gris"

    if category == CATEGORY_PAUSED:
        return "SUSPENDIDO", "amarillo"

    if raw_consumption_pct > OVER_BUDGET_PCT:
        return "EN RIESGO", "rojo"

    if consumption_index is not None:
        if consumption_index > RISK_CONSUMPTION_INDEX:
            return "EN RIESGO", "rojo"

        if consumption_index > WARNING_CONSUMPTION_INDEX:
            return "ATENCIÓN", "amarillo"

    if (
        progress.uses_milestones
        and progress.pace_index is not None
        and progress.elapsed_pct is not None
        and progress.elapsed_pct >= MIN_ELAPSED_FOR_PACE
        and progress.pace_index < SLOW_PACE_INDEX
    ):
        return "ATENCIÓN", "amarillo"

    return "EN CONTROL", "verde"


def calculate_date_risk(end_value: CellValue, now: datetime) -> str:
    """
    Riesgo de la fecha de salida segun los dias que faltan.

    Args:
        end_value: Fecha fin estimada.
        now: Fecha y hora local actual.

    Returns:
        Alto si ya paso, Medio si faltan 15 dias o menos, si no Bajo.
    """
    end = to_datetime(end_value) if end_value else None

    if end is None:
        return "Bajo"

    days_left = round_half_up_int((end - now).total_seconds() / SECONDS_PER_DAY)

    if days_left < 0:
        return "Alto"

    if days_left <= DATE_RISK_WARNING_DAYS:
        return "Medio"

    return "Bajo"


def progress_source(
    progress: ProgressInfo, phases: Sequence[JsonObject]
) -> str:
    """
    Describe de donde sale el avance.

    Args:
        progress: Avance e indices.
        phases: Hitos del proyecto.

    Returns:
        El texto de la fuente.
    """
    if not progress.uses_milestones:
        return "Consumo presupuestal"

    return "Hitos y fechas de etapa" if phases else "Sin hitos planificados"


def build_extra_kpis(
    resource_rows: Sequence[JsonObject],
    detail: JsonObject,
) -> JsonObject:
    """
    KPIs de recursos y costos tomados del detalle del proyecto.

    Args:
        resource_rows: Filas por recurso.
        detail: Detalle del proyecto.

    Returns:
        Recursos asignados, costos, cumplimiento y horas no facturables.
    """
    totals = detail.get("totales")
    kpis: JsonObject = {"recursosAsignados": len(resource_rows)}

    for key in (
        "costoEstimado",
        "costoReal",
        "pctCumplimientoFinanciero",
        "horasNoFact",
    ):
        if totals is None:
            kpis[key] = 0
        elif key in totals:
            # El original omitia la llave cuando el detalle no la traia.
            kpis[key] = totals[key]

    return kpis


def select_critical_risks(risks: Sequence[SheetRow]) -> list[JsonObject]:
    """
    Top 5 de riesgos abiertos ordenados por impacto.

    Args:
        risks: Riesgos abiertos del proyecto.

    Returns:
        Descripcion, impacto y probabilidad de cada riesgo.
    """
    ordered = sorted(
        risks,
        key=lambda risk: -IMPACT_ORDER.get(to_text(risk.get("Impacto")), 0),
    )

    return [
        {
            "descripcion": risk.get("Descripcion") or "",
            "impacto": risk.get("Impacto") or "",
            "probabilidad": risk.get("Probabilidad") or "",
        }
        for risk in ordered[:TOP_RISKS]
    ]
