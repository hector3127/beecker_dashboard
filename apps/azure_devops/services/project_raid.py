"""RAID del dashboard ejecutivo por proyecto."""

import logging
from collections.abc import Callable, Mapping, Sequence
from datetime import datetime
from typing import Any

from apps.azure_devops.constants import AZURE_DEVOPS_BASE_URL
from apps.azure_devops.services.azure_client import encode_url_part
from apps.azure_devops.services.portfolio_risks import format_changed_date
from apps.azure_devops.services.project_resolver import (
    normalize_azure_name,
    resolve_azure_project,
)
from apps.azure_devops.services.risk_severity import (
    label_risk_severity,
    severity_order,
)
from core.exceptions import DashboardError, describe_error
from core.utils.js_values import js_number, js_or_text
from core.utils.text import extract_base_id

"""BKD.030.010 - RAID ejecutivo por proyecto
Equivale a obtenerRaidProyectoEjecutivoAzure() de ResumenAltoNivelService.gs:
- Riesgos y oportunidades Active/Proposed del Team Project del ID.
- Top 5 riesgos por severidad y fecha de cambio.
- Pendientes no completados de Pendientes_Daily del ID, su base o el
  Team Project.
Solo consulta; no cambia el proyecto activo del panel Daily.
"""

logger = logging.getLogger(__name__)

JsonObject = dict[str, Any]

TOP_RISKS = 5
SEVERITY_FIELD = "Microsoft.VSTS.Common.Severity"
PROBABILITY_NAMES = ("probability", "probabilidad")
PROBABILITY_LABELS = {1: "Alta", 2: "Media", 3: "Baja", 4: "Muy baja"}
OPEN_STATES = ("ACTIVE", "PROPOSED")
DONE_STATES = ("COMPLETADO", "COMPLETED")
EMPTY_TOTALS = {
    "riesgos": [],
    "totalRiesgos": 0,
    "totalOportunidades": 0,
    "totalPendientes": 0,
}


def blank(value: object) -> bool:
    """undefined, null o cadena vacia."""
    return value is None or value == ""


def first_matching_key(fields: Mapping[str, Any], word: str) -> str | None:
    """Primer campo cuyo nombre contiene la palabra (sin mayusculas)."""
    return next((key for key in fields if word in key.lower()), None)


def probability_reference(risk_fields: Sequence[Mapping[str, Any]]) -> str:
    """Reference name del campo de probabilidad del proceso."""
    field = next(
        (
            item
            for item in risk_fields
            if normalize_azure_name(js_or_text(item.get("name"))).lower()
            in PROBABILITY_NAMES
        ),
        None,
    ) or next(
        (
            item
            for item in risk_fields
            if "probab" in js_or_text(item.get("name")).lower()
        ),
        None,
    )

    return js_or_text(field.get("referenceName")) if field else ""


def probability_label(value: object) -> str:
    """1 Alta, 2 Media, 3 Baja, 4 Muy baja; el texto tal cual si no."""
    text = "" if value is None else str(value).strip()

    if not text:
        return "—"

    number = js_number(text)

    if number in PROBABILITY_LABELS:
        return PROBABILITY_LABELS[int(number)]

    return text


def raw_field(
    fields: Mapping[str, Any],
    reference: str,
    word: str,
) -> object:
    """Valor del campo; si viene vacio, el primero que contenga la palabra."""
    value = fields.get(reference) if reference else ""

    if blank(value):
        key = first_matching_key(fields, word)

        if key:
            value = fields[key]

    return value


def build_risk(
    work_item: Mapping[str, Any],
    probability_ref: str,
    organization: str,
    azure_project: str,
) -> JsonObject:
    """Riesgo con el formato del RAID ejecutivo."""
    fields = work_item.get("fields") or {}
    severity = raw_field(fields, SEVERITY_FIELD, "severity")
    probability = raw_field(fields, probability_ref, "probab")
    work_item_id = work_item.get("id")

    return {
        "id": work_item_id,
        "descripcion": js_or_text(fields.get("System.Title")).strip(),
        "estado": js_or_text(fields.get("System.State")).strip(),
        "severity": js_or_text(severity),
        "impacto": label_risk_severity(severity),
        "probabilidad": probability_label(probability),
        "fechaCambio": format_changed_date(fields.get("System.ChangedDate")),
        "url": (
            f"{AZURE_DEVOPS_BASE_URL}/{encode_url_part(organization)}/"
            f"{encode_url_part(azure_project)}/_workitems/edit/{work_item_id}"
        ),
    }


def changed_ms(risk: Mapping[str, Any]) -> float:
    """Fecha de cambio en milisegundos (0 sin fecha)."""
    text = risk.get("fechaCambio")

    if not text:
        return 0

    moment = datetime.fromisoformat(str(text).replace("Z", "+00:00"))

    return moment.timestamp() * 1000


def count_pending(
    rows: Sequence[Mapping[str, Any]],
    candidates: Sequence[str],
) -> int:
    """Pendientes no completados del proyecto, su base o su Team Project."""
    keys = {
        normalize_azure_name(js_or_text(value))
        for value in candidates
        if normalize_azure_name(js_or_text(value))
    }
    total = 0

    for row in rows:
        if normalize_azure_name(js_or_text(row.get("Estado"))) in DONE_STATES:
            continue

        project = js_or_text(row.get("Proyecto")).strip()

        if not project:
            continue

        if (
            normalize_azure_name(project) in keys
            or normalize_azure_name(extract_base_id(project)) in keys
        ):
            total += 1

    return total


def resolve_project(
    internal_id: str,
    project_names: Sequence[str],
    active_project: str,
) -> str:
    """
    Team Project del ID (_altoNivelResolverProyectoAzure).

    Exacto, por base y, como respaldo, el proyecto activo del Daily si
    coincide por base.
    """
    found = resolve_azure_project(internal_id, project_names)

    if found:
        return found

    base = normalize_azure_name(extract_base_id(internal_id))

    if normalize_azure_name(extract_base_id(active_project)) == base:
        return active_project

    return ""


AzureSource = Callable[[str], tuple[list[JsonObject], list[JsonObject]]]


def build_project_raid(
    project_value: object,
    project_names: Sequence[str],
    active_project: str,
    load_items: AzureSource | None,
    pending_rows: Callable[[], Sequence[Mapping[str, Any]]],
    organization: str,
) -> JsonObject:
    """
    RAID del proyecto (obtenerRaidProyectoEjecutivoAzure).

    Args:
        project_value: ID interno del proyecto.
        project_names: Team Projects de la organizacion.
        active_project: Proyecto activo del panel Daily.
        load_items: (work items RAID, campos de Risk) de un Team
            Project; None si Azure no esta configurado.
        pending_rows: Filas de Pendientes_Daily.
        organization: Organizacion de Azure DevOps.

    Returns:
        {ok, proyectoAzure, riesgos (top 5), totalRiesgos,
        totalOportunidades, totalPendientes}.
    """
    internal_id = js_or_text(project_value).strip()

    if not internal_id:
        return {"ok": False, **EMPTY_TOTALS, "error": "Falta ID de proyecto."}

    try:
        base_id = extract_base_id(internal_id)
        azure_project = resolve_project(
            internal_id,
            project_names,
            active_project,
        ) or resolve_project(base_id, project_names, active_project)

        if not azure_project:
            return {
                "ok": True,
                "proyectoAzure": "",
                **EMPTY_TOTALS,
                "errorAzure": "No se encontró Team Project Azure vinculado.",
            }

        if load_items is None:
            return {
                "ok": False,
                "proyectoAzure": azure_project,
                **EMPTY_TOTALS,
                "error": "Conecta Azure DevOps primero.",
            }

        work_items, risk_fields = load_items(azure_project)
        reference = probability_reference(risk_fields)
        risks = []
        opportunities = 0

        for work_item in work_items:
            fields = work_item.get("fields") or {}
            item_type = normalize_azure_name(
                js_or_text(fields.get("System.WorkItemType")),
            )
            state = normalize_azure_name(js_or_text(fields.get("System.State")))

            if state not in OPEN_STATES:
                continue

            if item_type == "OPPORTUNITY":
                opportunities += 1
            elif item_type == "RISK":
                risks.append(
                    build_risk(
                        work_item, reference, organization, azure_project
                    ),
                )

        risks.sort(key=changed_ms, reverse=True)
        risks.sort(
            key=lambda risk: severity_order(risk["impacto"]), reverse=True
        )

        try:
            pending = count_pending(
                pending_rows(),
                [
                    internal_id,
                    base_id,
                    azure_project,
                    extract_base_id(azure_project),
                ],
            )
        except DashboardError as error:
            logger.info("Pendientes_Daily no disponible: %s", error.detail)
            pending = 0

        return {
            "ok": True,
            "proyectoAzure": azure_project,
            "riesgos": risks[:TOP_RISKS],
            "totalRiesgos": len(risks),
            "totalOportunidades": opportunities,
            "totalPendientes": pending,
        }
    except DashboardError as error:
        return {"ok": False, **EMPTY_TOTALS, "error": describe_error(error)}
