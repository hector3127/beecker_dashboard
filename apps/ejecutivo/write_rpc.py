"""Funciones que escriben hitos y riesgos, expuestas al frontend por RPC."""

import logging
import time
from collections.abc import Callable
from typing import Any

from django.utils import timezone

from apps.dashboard.cache import clear_cached_dashboard
from apps.ejecutivo.services.additional_milestones import list_milestone_types
from apps.ejecutivo.services.manual_risks import add_manual_risk, read_text
from apps.ejecutivo.services.milestone_writer import (
    MilestoneSheet,
    delete_milestone,
    edit_milestone,
    save_milestones,
)
from core.exceptions import DashboardError, describe_error
from core.rpc.registry import register_rpc
from core.sheets import sheet_names
from core.sheets.factory import build_sheet_repository

"""BKD.040.017 - RPC de escritura del ejecutivo
Registra obtenerTiposHitosExistentes, guardarHitosAdicionalesLote,
guardarHitoAdicional, editarHitoAdicional, eliminarHitoAdicional y
agregarRiesgoManual con los mismos nombres y respuestas que en Apps
Script.
"""

logger = logging.getLogger(__name__)

JsonObject = dict[str, Any]

MilestoneAction = Callable[[MilestoneSheet], list[JsonObject]]


@register_rpc("obtenerTiposHitosExistentes")
def get_milestone_types() -> list[str]:
    """
    Lista los tipos de hito ya usados en la hoja Proyectos.

    Returns:
        Los encabezados desde la columna L; vacio si hay error.
    """
    try:
        repository = build_sheet_repository()
        return list_milestone_types(
            repository.read_values(sheet_names.SHEET_PROJECTS),
        )
    except DashboardError as error:
        logger.warning("Tipos de hito no disponibles: %s", error.detail)
        return []


@register_rpc("guardarHitosAdicionalesLote")
def save_milestone_batch(
    project_id: object = "",
    milestones: object = None,
) -> JsonObject:
    """
    Guarda varios hitos adicionales de un proyecto.

    Args:
        project_id: ID del proyecto.
        milestones: Lista de {tipo, fechaISO, observacion}.

    Returns:
        {"ok", "hitos"} o {"ok": False, "error", "hitos": []}.
    """
    items = milestones if isinstance(milestones, list) else []

    return run_milestone_action(
        lambda sheet: save_milestones(sheet, read_text(project_id), items),
    )


@register_rpc("guardarHitoAdicional")
def save_milestone(
    project_id: object = "",
    milestone_type: object = "",
    date_value: object = "",
    note: object = "",
) -> JsonObject:
    """
    Guarda un solo hito adicional.

    Args:
        project_id: ID del proyecto.
        milestone_type: Tipo de hito.
        date_value: Fecha del hito.
        note: Observacion.

    Returns:
        La misma respuesta que guardarHitosAdicionalesLote.
    """
    return save_milestone_batch(
        project_id,
        [{"tipo": milestone_type, "fechaISO": date_value, "observacion": note}],
    )


@register_rpc("editarHitoAdicional")
def edit_milestone_entry(
    project_id: object = "",
    milestone_type: object = "",
    index: object = None,
    date_value: object = "",
    note: object = "",
) -> JsonObject:
    """
    Edita la fecha y observacion de una entrada.

    Args:
        project_id: ID del proyecto.
        milestone_type: Tipo de hito.
        index: Indice de la entrada en la celda.
        date_value: Fecha nueva.
        note: Observacion nueva.

    Returns:
        {"ok", "hitos"} o {"ok": False, "error", "hitos": []}.
    """
    return run_milestone_action(
        lambda sheet: edit_milestone(
            sheet,
            (read_text(project_id), read_text(milestone_type), index),
            date_value,
            note,
        ),
    )


@register_rpc("eliminarHitoAdicional")
def delete_milestone_entry(
    project_id: object = "",
    milestone_type: object = "",
    index: object = None,
) -> JsonObject:
    """
    Elimina una entrada de un tipo de hito.

    Args:
        project_id: ID del proyecto.
        milestone_type: Tipo de hito.
        index: Indice de la entrada en la celda.

    Returns:
        {"ok", "hitos"} o {"ok": False, "error", "hitos": []}.
    """
    return run_milestone_action(
        lambda sheet: delete_milestone(
            sheet,
            read_text(project_id),
            read_text(milestone_type),
            index,
        ),
    )


@register_rpc("agregarRiesgoManual")
def add_risk(
    project_id: object = "",
    description: object = "",
    impact: object = "",
    probability: object = "",
    owner: object = "",
) -> JsonObject:
    """
    Agrega un riesgo manual al proyecto.

    Args:
        project_id: ID del proyecto.
        description: Descripcion del riesgo.
        impact: Alto, Medio o Bajo.
        probability: Alta, Media o Baja.
        owner: Responsable.

    Returns:
        {"ok": True} o {"ok": False, "error"}.
    """
    try:
        repository = build_sheet_repository()
        add_manual_risk(
            (repository, repository),
            (project_id, description, impact, probability, owner),
            (
                timezone.localtime().replace(tzinfo=None),
                time.time_ns() // 10**6,
            ),
        )
    except DashboardError as error:
        logger.warning("Riesgo manual no guardado: %s", error.detail)
        return {"ok": False, "error": describe_error(error)}

    clear_cached_dashboard()

    return {"ok": True}


def run_milestone_action(action: MilestoneAction) -> JsonObject:
    """
    Ejecuta una escritura de hitos y arma la respuesta del original.

    Args:
        action: Escritura a ejecutar sobre la hoja Proyectos.

    Returns:
        {"ok", "hitos"} o {"ok": False, "error", "hitos": []}.
    """
    try:
        repository = build_sheet_repository()
        milestones = action(MilestoneSheet(repository, repository))
    except DashboardError as error:
        logger.warning("Hitos adicionales no guardados: %s", error.detail)
        return {"ok": False, "error": describe_error(error), "hitos": []}

    return {"ok": True, "hitos": milestones}
