"""Carga de las pantallas EVA (solo lectura)."""

import logging
from dataclasses import dataclass, replace
from typing import Any

from django.core.cache import cache
from django.utils import timezone

from apps.ejecutivo.rpc import (
    get_aer_tym_consumption,
    get_ixb_raas_summary,
    load_aer_tym_summary,
    load_ixb_raas_summary,
)
from apps.ejecutivo.services.ixb_summary import IxbSources, build_ixb_summary
from apps.ejecutivo.services.project_dashboard import build_history_block_rows
from apps.portal.constants import (
    EVA2_CACHE_KEY,
    EVA2_CACHE_SECONDS,
    EVA2_CLOSED_CACHE_KEY,
)
from apps.portal.schemas import Eva1View, Eva2View, EvaCard, TimeCost
from apps.portal.services.eva1 import build_eva1_view
from apps.portal.services.eva2 import build_eva2_view
from apps.portal.services.time_cost import average
from core.exceptions import DashboardError
from core.sheets import sheet_names
from core.sheets.factory import build_sheet_repository

"""BKD.120.015 - Carga de EVA
Lee la hoja MPB con el mismo servicio de apps/ejecutivo (que ya guarda
90 segundos en cache). Si falla, la pantalla muestra el aviso.
"""

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class Eva1Load:
    """Resultado de cargar EVA 1."""

    view: Eva1View
    error: str


def load_eva1(enrich: bool = True) -> Eva1Load:
    """
    Carga EVA 1 desde la hoja MPB.

    Returns:
        La pantalla armada, o una vacia y el motivo si no se pudo leer.
    """
    try:
        summary = load_aer_tym_summary(build_sheet_repository())
    except DashboardError as error:
        logger.warning("No se pudo cargar EVA 1: %s", error)

        return Eva1Load(view=build_eva1_view([]), error=error.build_message())

    raw_rows = summary.get("filas")
    rows = (
        [dict(row) for row in raw_rows if isinstance(row, dict)]
        if isinstance(raw_rows, list)
        else []
    )
    consumption_errors = []
    for offset in range(0, len(rows) if enrich else 0, 2):
        batch = rows[offset : offset + 2]
        missing = [row for row in batch if row.get("burn") is None]
        if not missing:
            continue
        ids = [row["idProyecto"] for row in missing]
        key = "portal:eva3:consumption:" + "|".join(ids)
        result = cache.get(key)
        if result is None:
            result = get_aer_tym_consumption(ids)
            complete_ids = {
                str(item.get("id", "")).casefold()
                for item in result.get("items", [])
                if isinstance(item.get("burn"), (int, float))
            }
            if result.get("ok") and all(
                str(pid).casefold() in complete_ids for pid in ids
            ):
                cache.set(key, result, 300)
        for row in missing:
            item: dict[str, Any] = next(
                (
                    item
                    for item in result.get("items", [])
                    if str(item.get("id", "")).casefold()
                    == row["idProyecto"].casefold()
                ),
                {},
            )
            if isinstance(item.get("burn"), (int, float)):
                row["burn"] = item["burn"]
                row["etc"] = round(
                    float(row.get("budget") or 0) - item["burn"], 2
                )
                row["avance"] = (
                    round(item["burn"] / float(row["budget"]) * 100, 1)
                    if row.get("budget")
                    else None
                )
            else:
                consumption_errors.append(str(row["idProyecto"]))

    return Eva1Load(
        view=build_eva1_view(rows if isinstance(rows, list) else []),
        error=(
            "Consumo AER/T&M incompleto: " + ", ".join(consumption_errors)
            if consumption_errors
            else ""
        ),
    )


@dataclass(frozen=True, slots=True)
class Eva2Load:
    """Resultado de cargar EVA 2."""

    view: Eva2View
    error: str


def load_eva2(enrich: bool = True) -> Eva2Load:
    """
    Carga EVA 2 con el resumen IXB/RaaS (Sheets, Clockify y Azure, lectura).

    La consulta es lenta porque revisa Azure DevOps y Clockify proyecto por
    proyecto, por eso el resumen se guarda 10 minutos en cache.

    Returns:
        La pantalla armada, o una vacia y el motivo si no se pudo leer.
    """
    summary = cache.get(EVA2_CACHE_KEY)

    if not isinstance(summary, dict) and not enrich:
        return _load_eva2_base()
    if not isinstance(summary, dict):
        summary = get_ixb_raas_summary()

        if summary.get("ok") is True:
            cache.set(EVA2_CACHE_KEY, summary, EVA2_CACHE_SECONDS)

    if summary.get("ok") is not True:
        return Eva2Load(
            view=build_eva2_view([]),
            error=str(summary.get("error") or "No se pudo leer IXB y RaaS."),
        )

    rows = summary.get("filas")

    return Eva2Load(
        view=build_eva2_view(rows if isinstance(rows, list) else []),
        error="",
    )


def _load_eva2_base() -> Eva2Load:
    """Proyectos y estados desde Sheets, sin horas ni llamadas a Azure."""
    key = "portal:eva2:base:v1"
    cached = cache.get(key)
    if isinstance(cached, Eva2Load):
        return cached
    try:
        reader = build_sheet_repository()
        reader.prefetch(
            [
                sheet_names.SHEET_PROJECTS,
                sheet_names.SHEET_PROJECTS_HISTORY,
            ]
        )
        history = build_history_block_rows(
            reader.read_values(sheet_names.SHEET_PROJECTS_HISTORY),
            [],
        )
        sources = IxbSources(
            reader.read_as_objects(sheet_names.SHEET_PROJECTS),
            history,
            lambda project_id: [],
            None,
        )
        summary = build_ixb_summary(
            sources,
            timezone.localtime().replace(tzinfo=None),
        )
        view = build_eva2_view(summary["filas"])
        result = Eva2Load(
            replace(
                view, time_cost=TimeCost(time_days=view.time_cost.time_days)
            ),
            "",
        )
        cache.set(key, result, 300)
        return result
    except DashboardError as error:
        return Eva2Load(build_eva2_view([]), error.build_message())


def load_eva2_closed() -> Eva2Load:
    """
    Carga los proyectos IXB/RaaS que ya estan cerrados en el historico.

    Es el complemento de EVA 2 (que los excluye) y se guarda 10 minutos.

    Returns:
        La pantalla con solo los proyectos cerrados, o el motivo del error.
    """
    summary = cache.get(EVA2_CLOSED_CACHE_KEY)

    if not isinstance(summary, dict):
        summary = load_ixb_raas_summary(closed=True)

        if summary.get("ok") is True:
            cache.set(EVA2_CLOSED_CACHE_KEY, summary, EVA2_CACHE_SECONDS)

    if summary.get("ok") is not True:
        return Eva2Load(
            view=build_eva2_view([]),
            error=str(summary.get("error") or "No se pudo leer el historico."),
        )

    rows = summary.get("filas")

    return Eva2Load(
        view=build_eva2_view(rows if isinstance(rows, list) else []),
        error="",
    )


def build_eva1_card(load: Eva1Load) -> EvaCard:
    """
    Cifras de la tarjeta EVA 1 en Operativa.

    Args:
        load: Resultado de load_eva1().

    Returns:
        TP y C; sin datos cuando no se pudo leer MPB.
    """
    if load.error:
        return EvaCard(available=False)

    return EvaCard(
        available=True,
        total_projects=load.view.total_projects,
        time_cost=TimeCost(
            time_days=average(p.renewal_days for p in load.view.projects),
            cost_percent=load.view.cost_percent,
        ),
    )


def peek_eva2_card() -> EvaCard:
    """
    Cifras de la tarjeta EVA 2 solo si ya estan en cache.

    EVA 2 consulta Azure DevOps y Clockify; para no hacer lenta la pagina
    Operativa, la tarjeta solo usa el resultado guardado al abrir EVA 2.

    Returns:
        TP, T y C, o una tarjeta sin datos si no hay cache.
    """
    summary = cache.get(EVA2_CACHE_KEY)

    if not isinstance(summary, dict) or summary.get("ok") is not True:
        return EvaCard(available=False)

    rows = summary.get("filas")
    view = build_eva2_view(rows if isinstance(rows, list) else [])

    return EvaCard(
        available=True,
        total_projects=view.total_projects,
        time_cost=view.time_cost,
    )
