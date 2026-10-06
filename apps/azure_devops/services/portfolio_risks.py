"""Top riesgos del portafolio a partir de Azure DevOps."""

import logging
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from apps.azure_devops.constants import (
    AZURE_DEVOPS_BASE_URL,
    OPEN_RISK_STATES,
    RISK_WORK_ITEM_TYPE,
    SEVERITY_FIELD,
    SEVERITY_HIGH,
)
from apps.azure_devops.exceptions import AzureDevOpsRequestError
from apps.azure_devops.services.azure_client import encode_url_part
from apps.azure_devops.services.project_resolver import (
    normalize_azure_name,
    resolve_azure_project,
)
from apps.azure_devops.services.risk_severity import (
    label_risk_severity,
    severity_order,
)
from core.utils.cell_types import SheetRow
from core.utils.text import extract_base_id, get_flexible_value, to_text

"""BKD.030.006 - Top riesgos del portafolio
Equivale a obtenerTopRiesgosPortafolioAzure():
- Work Item Type = Risk, solo en estado Active o Proposed.
- La prioridad sale del campo Severity de Azure.
- Se recorre cada Team Project vinculado a los proyectos del portafolio.
- Orden: Alto, Medio, Bajo; dentro de cada uno, el mas reciente primero.
"""

logger = logging.getLogger(__name__)

JsonObject = dict[str, Any]


@dataclass(slots=True)
class AzureProjectGroup:
    """Proyectos internos que comparten un Team Project de Azure."""

    azure_project: str
    internal_ids: list[str] = field(default_factory=list)
    names: list[str] = field(default_factory=list)
    clients: list[str] = field(default_factory=list)


def group_projects_by_azure(
    project_rows: Sequence[SheetRow],
    azure_project_names: Sequence[str],
) -> dict[str, AzureProjectGroup]:
    """
    Agrupa los proyectos internos por su Team Project de Azure.

    Args:
        project_rows: Filas de la hoja Proyectos.
        azure_project_names: Proyectos de la organizacion.

    Returns:
        Team Project -> grupo de proyectos internos.
    """
    groups: dict[str, AzureProjectGroup] = {}

    for project_row in project_rows:
        internal_id = to_text(project_row.get("ID_Proyecto")).strip()

        if not internal_id:
            continue

        azure_project = resolve_azure_project(
            internal_id,
            azure_project_names,
        ) or resolve_azure_project(
            extract_base_id(internal_id),
            azure_project_names,
        )

        if not azure_project:
            continue

        group = groups.setdefault(
            azure_project,
            AzureProjectGroup(azure_project=azure_project),
        )
        add_unique(group.internal_ids, internal_id)
        add_unique(group.names, to_text(project_row.get("Nombre")).strip())
        add_unique(
            group.clients,
            to_text(
                get_flexible_value(project_row, ["Cliente", "Account"]),
            ).strip(),
        )

    return groups


def build_portfolio_risks(
    groups: dict[str, AzureProjectGroup],
    load_work_items: Callable[[str], list[JsonObject]],
    organization: str,
) -> JsonObject:
    """
    Construye la respuesta de obtenerTopRiesgosPortafolioAzure().

    Args:
        groups: Proyectos agrupados por Team Project.
        load_work_items: Funcion que lee los work items de un proyecto.
        organization: Organizacion de Azure DevOps, para los enlaces.

    Returns:
        {"ok", "riesgos", "total", "riesgosAltos"} como el original.
    """
    risks: list[JsonObject] = []

    for azure_project, group in groups.items():
        try:
            work_items = load_work_items(azure_project)
        except AzureDevOpsRequestError as error:
            # Igual que el original: un Team Project inaccesible no
            # impide mostrar los riesgos de los demas.
            logger.warning(
                "Riesgos omitidos de %s: %s",
                azure_project,
                error.detail,
            )
            continue

        risks.extend(
            build_risk(work_item, group, organization)
            for work_item in work_items
            if is_open_risk(work_item.get("fields") or {})
        )

    # Las fechas ISO en UTC se ordenan bien como texto.
    risks.sort(key=lambda risk: risk["fechaCambio"] or "", reverse=True)
    risks.sort(key=lambda risk: severity_order(risk["impacto"]), reverse=True)

    return {
        "ok": True,
        "riesgos": risks,
        "total": len(risks),
        "riesgosAltos": sum(
            1 for risk in risks if risk["impacto"] == SEVERITY_HIGH
        ),
    }


def is_open_risk(fields: JsonObject) -> bool:
    """
    Indica si el work item es un riesgo Active o Proposed.

    Args:
        fields: Campos del work item.

    Returns:
        True para riesgos abiertos.
    """
    work_item_type = normalize_azure_name(
        to_text(fields.get("System.WorkItemType"))
    )
    state = normalize_azure_name(to_text(fields.get("System.State")))

    return work_item_type == RISK_WORK_ITEM_TYPE and state in OPEN_RISK_STATES


def build_risk(
    work_item: JsonObject,
    group: AzureProjectGroup,
    organization: str,
) -> JsonObject:
    """
    Convierte un work item de riesgo al formato del panel.

    Args:
        work_item: Work item de Azure.
        group: Proyectos internos del Team Project.
        organization: Organizacion de Azure DevOps.

    Returns:
        El riesgo con las llaves que usa js_main.html.
    """
    fields: JsonObject = work_item.get("fields") or {}
    raw_severity = read_severity(fields)
    assigned_to = fields.get("System.AssignedTo") or {}
    work_item_id = work_item.get("id")

    return {
        "id": work_item_id,
        "descripcion": to_text(fields.get("System.Title")).strip(),
        "proyecto": ", ".join(group.internal_ids) or group.azure_project,
        "nombreProyecto": ", ".join(group.names),
        "cliente": ", ".join(group.clients),
        "clientes": list(group.clients),
        "proyectoAzure": group.azure_project,
        "estado": to_text(fields.get("System.State")).strip(),
        "severity": str(raw_severity) if raw_severity else "",
        "impacto": label_risk_severity(raw_severity),
        "responsable": (
            assigned_to.get("displayName")
            or assigned_to.get("uniqueName")
            or ""
            if isinstance(assigned_to, dict)
            else ""
        ),
        "fechaCambio": format_changed_date(fields.get("System.ChangedDate")),
        "url": (
            f"{AZURE_DEVOPS_BASE_URL}/{encode_url_part(organization)}/"
            f"{encode_url_part(group.azure_project)}/_workitems/edit/"
            f"{work_item_id}"
        ),
    }


def read_severity(fields: JsonObject) -> object:
    """
    Lee Severity; si el proceso usa otro nombre, busca un campo similar.

    Args:
        fields: Campos del work item.

    Returns:
        El valor crudo de la severidad, o None.
    """
    raw_severity = fields.get(SEVERITY_FIELD)

    if raw_severity not in (None, ""):
        return raw_severity

    for field_name, field_value in fields.items():
        if "severity" in field_name.lower() and field_value not in (None, ""):
            return field_value

    return None


def format_changed_date(raw_date: object) -> str | None:
    """
    Normaliza la fecha de cambio como Date.toISOString().

    Args:
        raw_date: Fecha ISO devuelta por Azure.

    Returns:
        La fecha UTC con milisegundos y sufijo Z, o None.
    """
    if not isinstance(raw_date, str) or not raw_date:
        return None

    try:
        moment = datetime.fromisoformat(raw_date.replace("Z", "+00:00"))
    except ValueError:
        # Azure no envio una fecha ISO; el riesgo queda sin fecha.
        return None

    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=UTC)

    utc_text = moment.astimezone(UTC).isoformat(timespec="milliseconds")

    return utc_text.replace("+00:00", "Z")


def add_unique(values: list[str], value: str) -> None:
    """
    Agrega un texto no vacio si todavia no esta en la lista.

    Args:
        values: Lista destino.
        value: Valor a agregar.
    """
    if value and value not in values:
        values.append(value)
