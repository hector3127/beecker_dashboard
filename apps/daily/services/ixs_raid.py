"""Gestion RAID (Risk, Issue, Opportunity) de la vista IXS."""

import json
import re
import unicodedata
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any, cast

from apps.azure_devops.services.azure_client import encode_url_part
from apps.daily.constants import AZURE_BASE_URL, UNASSIGNED
from apps.daily.exceptions import AzureHttpError
from apps.daily.services.daily_azure_client import DailyAzureClient
from apps.daily.services.ixs_panel import (
    LAST_OK_CACHE_SECONDS,
    IxsAzure,
    copy_notice,
    is_transient,
    load_panel,
)
from core.exceptions import DashboardError
from core.utils.text import to_text

"""BKD.070.013 - RAID de la vista IXS
Equivale a ixsRaidListarProyecto(), ixsRaidCamposTipo(),
ixsRaidAltaOpciones() e ixsRaidCrearRegistro(): lista los registros
RAID del proyecto con sus campos de detalle y crea Risk, Issue u
Opportunity validando los campos y valores reales del proceso de Azure.
"""

JsonObject = dict[str, Any]

RAID_TYPES = ("Risk", "Issue", "Opportunity")
RAID_TYPES_UPPER = frozenset({"RISK", "ISSUE", "OPPORTUNITY"})
CLOSED_STATES = frozenset(
    {
        "NOT APPLICABLE",
        "CANCELLED",
        "CLOSED",
        "REJECTED",
        "COMPLETED",
        "INACTIVE",
    },
)
RELATION_BATCH_SIZE = 130
OPTIONS_BATCH_SIZE = 140
OPTIONS_MAX_ITEMS = 350
MAX_RELATED = 8
MAX_DESCRIPTION = 3000
FETCH_ERROR_CHARS = 380
SEVERITY_NUMBER = re.compile(r"^(\d+)(?=\s*[-–—]\s*|\s*$)", re.ASCII)
RELATED_REL = re.compile(r"LinkTypes.Related|Hierarchy", re.IGNORECASE)
TRAILING_ID = re.compile(r"/(\d+)(?:\?.*)?$", re.ASCII)
HTML_TAG = re.compile(r"<[^>]*>")
DIGITS = re.compile(r"[0-9]+")
NUMERIC_TYPE = re.compile(r"^(integer|double|number|float)$", re.IGNORECASE)
DATE_TYPE = re.compile(r"^(dateTime)$", re.IGNORECASE)
ISO_DAY = re.compile(r"\d{4}-\d{2}-\d{2}", re.ASCII)
LIST_BULLETS = re.compile(r"\s*[•●▪]\s*")
LIST_MARKERS = re.compile(r"(?:^|\n)\s*(?:\*|-|\d+[.)])\s+")
BR_TAG = re.compile(r"<br\s*/?\s*>", re.IGNORECASE)
PARENT_REL = "System.LinkTypes.Hierarchy-Reverse"

FieldSpec = tuple[Sequence[str], Sequence[str]]

ISSUE_FIELDS: dict[str, FieldSpec] = {
    "plan": (
        (
            "Corrective Action Plan",
            "Plan de mitigación",
            "Plan de mitigacion",
            "Mitigation Plan",
            "Plan",
        ),
        ("corrective action plan", "plan de mitigacion", "mitigation plan"),
    ),
    "escalationContact": (
        (
            "Persona a la que se escala",
            "Escalation Contact",
            "Contacto de escalamiento",
            "Escalate To",
        ),
        (
            "persona a la que se escala",
            "escalation contact",
            "contacto de escalamiento",
            "escalate to",
        ),
    ),
    "detectionDate": (
        ("Detection Date", "Fecha de detección", "Fecha de deteccion"),
        ("detection date", "fecha de deteccion"),
    ),
    "reporter": (
        ("Persona que reporta", "Reporter", "Reportado por", "Reported By"),
        ("persona que reporta", "reportado por", "reported by", "reporter"),
    ),
    "relatedSoftware": (
        ("Software relacionado", "Related Software"),
        ("software relacionado", "related software"),
    ),
}

OPTION_FIELDS: dict[str, FieldSpec] = {
    "plan": ISSUE_FIELDS["plan"],
    "escalate": (("Escalate", "¿Escalar?"), ("escalate",)),
    "escalationContact": ISSUE_FIELDS["escalationContact"],
    "detectionDate": ISSUE_FIELDS["detectionDate"],
    "reporter": ISSUE_FIELDS["reporter"],
    "closureDate": (
        ("Closure Date", "Fecha de cierre"),
        ("closure date", "fecha de cierre"),
    ),
    "relatedSoftware": ISSUE_FIELDS["relatedSoftware"],
    "state": (("State", "Estado"), ("state",)),
    "reason": (("Reason", "Motivo"), ("reason",)),
    "originalEstimate": (
        ("Original Estimate", "Estimación original"),
        ("original estimate",),
    ),
    "effortCompleted": (
        ("Effort completed", "Completed Work", "Trabajo completado"),
        ("effort completed", "completed work"),
    ),
    "improvementPlan": (
        ("Improvement plan", "Plan de aprovechamiento"),
        ("improvement plan", "plan de aprovechamiento"),
    ),
    "triggers": (
        ("Triggers", "Señal de alerta"),
        ("triggers", "senal de alerta"),
    ),
    "actionPlan": (
        ("Action plan", "Plan de acción"),
        ("action plan", "plan de accion"),
    ),
    "followUp": (("Follow up", "Seguimiento"), ("follow up", "seguimiento")),
    "managementStrategy": (
        ("Estrategia de gestión", "Management Strategy"),
        ("estrategia de gestion", "management strategy"),
    ),
    "stakeholders": (
        ("Partes interesadas afectadas", "Stakeholders Affected"),
        ("partes interesadas afectadas", "stakeholders affected"),
    ),
    "riskSource": (
        ("Fuente del riesgo", "Risk Source"),
        ("fuente del riesgo", "risk source"),
    ),
    "opportunitySource": (
        ("Fuente de la oportunidad", "Opportunity Source"),
        ("fuente de la oportunidad", "opportunity source"),
    ),
    "category": (("Categoría", "Category"), ("categoria", "category")),
    "followUpDate": (
        ("Fecha de seguimiento", "Follow-up Date"),
        ("fecha de seguimiento", "follow-up date"),
    ),
    "escalationPerson": (
        ("Persona a la que se escala", "Escalation Contact", "Escalate To"),
        ("persona a la que se escala", "escalation contact", "escalate to"),
    ),
}


class RaidError(DashboardError):
    """Error del RAID con el mensaje del original."""

    code = "ERR_IXS_RAID"
    expose_detail = True


@dataclass(frozen=True, slots=True)
class RaidContext:
    """Proyecto interno, Team Project y cliente (ixsRaidContexto_)."""

    project_id: str
    organization: str
    azure_project: str
    client: DailyAzureClient

    @property
    def url(self) -> str:
        """URL base de las APIs de work items del Team Project."""
        return self.client.project_url(self.azure_project)


def strip_marks(value: object) -> str:
    """Quita acentos (NFD sin marcas combinantes)."""
    text = unicodedata.normalize("NFD", js_text(value))

    return "".join(
        character
        for character in text
        if not 0x0300 <= ord(character) <= 0x036F
    )


def js_text(value: object) -> str:
    """Texto como String(x || '')."""
    if value is None or value is False or value == "":
        return ""

    if isinstance(value, float) and value.is_integer():
        return str(int(value))

    if value is True:
        return "true"

    return str(value)


def build_context(azure: IxsAzure, project_value: object) -> RaidContext:
    """
    Resuelve el Team Project del proyecto, como ixsRaidContexto_().

    Args:
        azure: Configuracion del panel.
        project_value: ID interno.

    Returns:
        El contexto.

    Raises:
        RaidError: Sin proyecto, sin conexion o sin Team Project.
    """
    project_id = js_text(project_value).strip()

    if not project_id:
        raise RaidError("Selecciona un proyecto.")

    if not azure.organization or not azure.personal_access_token:
        raise RaidError("Conecta Azure DevOps desde Configuración.")

    azure_project = azure.resolve_project(project_id)

    if not azure_project:
        raise RaidError(
            f"No se pudo resolver el Team Project de Azure para {project_id}.",
        )

    return RaidContext(
        project_id,
        azure.organization,
        azure_project,
        azure.build_client(),
    )


def raid_fetch(
    context: RaidContext,
    method: str,
    url: str,
    **kwargs: Any,
) -> JsonObject:
    """
    Llamada a Azure con los reintentos y el mensaje de ixsRaidFetch_().

    Las lecturas (GET y WIQL) se reintentan; las altas no.

    Args:
        context: Contexto del proyecto.
        method: GET o POST.
        url: URL completa.
        **kwargs: Parametros de requests.

    Returns:
        El JSON de la respuesta.

    Raises:
        RaidError: "Azure DevOps HTTP <codigo>: <cuerpo>".
    """
    is_read = method == "GET" or url.endswith("/wiql")

    try:
        return context.client.send(method, url, retry=is_read, **kwargs)
    except AzureHttpError as error:
        raise RaidError(
            f"Azure DevOps HTTP {error.status_code}: "
            f"{error.body[:FETCH_ERROR_CHARS]}",
        ) from error


def field_by_name(fields: Mapping[str, Any], candidates: Sequence[str]) -> Any:
    """
    Valor del campo cuyo nombre corto coincide, como ixsRaidCampoPorNombre_().

    Args:
        fields: Campos del work item.
        candidates: Nombres posibles.

    Returns:
        El valor, o cadena vacia.
    """

    def normalize(text: object) -> str:
        return re.sub(r"[^a-z0-9]", "", strip_marks(text).lower())

    names = [normalize(candidate) for candidate in candidates]
    keys = list(fields)
    found = next(
        (key for key in keys if normalize(key.split(".")[-1]) in names),
        None,
    ) or next(
        (
            key
            for key in keys
            if any(name in normalize(key.split(".")[-1]) for name in names)
        ),
        None,
    )

    return fields[found] if found else ""


def severity_number(value: object) -> str:
    """
    Numero de Severity ("2 - Medium" -> "2"), como ixsRaidNumeroSeveridad_().

    Args:
        value: Valor de Severity.

    Returns:
        El numero como texto, o cadena vacia.
    """
    text = to_text(value) if isinstance(value, str | int | float) else ""
    match = SEVERITY_NUMBER.match(text.strip())

    return str(int(match.group(1))) if match else ""


def list_raid(
    azure: IxsAzure,
    project_value: object,
    force_refresh: object,
    now_ms: int,
) -> JsonObject:
    """
    Registros RAID del proyecto (ixsRaidListarProyecto).

    Args:
        azure: Configuracion del panel.
        project_value: ID interno.
        force_refresh: Ignora la cache del panel.
        now_ms: Milisegundos actuales.

    Returns:
        {"ok", "registros", "proyectoAzure", "aviso", "obtenidoEn"} o
        {"ok": False, "error"}.
    """
    last_ok_key = ""

    try:
        context = build_context(azure, project_value)
        last_ok_key = "ixs_raid_lastok_v96_" + re.sub(
            r"[^a-zA-Z0-9_-]",
            "_",
            f"{context.organization}_{context.azure_project}_{context.project_id}",
        )
        panel = load_panel(
            azure, context.project_id, bool(force_refresh), now_ms
        )

        if not panel.get("ok"):
            raise RaidError(str(panel.get("error") or "Azure no respondió."))

        basic = [
            item
            for item in panel["allItems"]
            if str(item.get("tipo") or "").upper() in RAID_TYPES_UPPER
        ]
        details = load_relation_details(
            context,
            [item["id"] for item in basic if item.get("id")],
        )
        result = {
            "ok": True,
            "registros": [
                build_raid_row(
                    item, details.get(str(item["id"])) or {}, context
                )
                for item in basic
            ],
            "proyectoAzure": context.azure_project,
            "aviso": panel.get("aviso") or "",
            "obtenidoEn": now_ms,
        }
        result = cast(JsonObject, json.loads(json.dumps(result)))

        if "última consulta completa" not in str(panel.get("aviso") or ""):
            azure.cache.set(last_ok_key, result, LAST_OK_CACHE_SECONDS)

        return result
    except DashboardError as error:
        if last_ok_key and is_transient(error):
            last_ok = azure.cache.get(last_ok_key)

            if (
                isinstance(last_ok, dict)
                and last_ok.get("ok")
                and isinstance(last_ok.get("registros"), list)
            ):
                return {**last_ok, "aviso": copy_notice(last_ok)}

        return {"ok": False, "error": error.detail}


def load_relation_details(
    context: RaidContext,
    ids: Sequence[Any],
) -> dict[str, JsonObject]:
    """
    Work items con todos sus campos y relaciones, en lotes de 130.

    Args:
        context: Contexto del proyecto.
        ids: IDs RAID.

    Returns:
        ID -> work item.
    """
    details: dict[str, JsonObject] = {}

    for start in range(0, len(ids), RELATION_BATCH_SIZE):
        end = start + RELATION_BATCH_SIZE
        payload = raid_fetch(
            context,
            "GET",
            f"{context.url}workitems",
            params={
                "ids": ",".join(str(item_id) for item_id in ids[start:end]),
                "$expand": "relations",
                "api-version": "7.1",
            },
        )

        for work_item in payload.get("value") or []:
            details[str(work_item.get("id"))] = work_item

    return details


def build_raid_row(
    item: Mapping[str, Any],
    work_item: Mapping[str, Any],
    context: RaidContext,
) -> JsonObject:
    """
    Registro RAID con su detalle por tipo.

    Args:
        item: Work item del panel.
        work_item: Work item completo con relaciones.
        context: Contexto del proyecto.

    Returns:
        El registro como lo regresaba el original.
    """
    fields: Mapping[str, Any] = work_item.get("fields") or {}

    def value(names: Sequence[str]) -> Any:
        return field_by_name(fields, names) or ""

    work_item_type = fields.get("System.WorkItemType") or item.get("tipo") or ""
    type_upper = str(work_item_type).strip().upper()
    severity = value(
        ["Severity", "Severidad", "Risk Level", "Nivel del Riesgo"]
    )
    severity_code = severity_number(severity)
    person = fields.get("System.AssignedTo")

    return {
        "id": item.get("id"),
        "titulo": fields.get("System.Title") or item.get("titulo") or "",
        "tipo": work_item_type,
        "estado": fields.get("System.State") or item.get("estado") or "",
        "asignadoA": assigned_text(person, item.get("asignadoA")),
        "iterationPath": (
            fields.get("System.IterationPath")
            or item.get("iterationPath")
            or ""
        ),
        "areaPath": fields.get("System.AreaPath") or "",
        "ultimaActualizacion": (
            fields.get("System.ChangedDate")
            or item.get("ultimoSeguimiento")
            or ""
        ),
        "diasSinActualizar": item.get("diasSinActualizar"),
        "descripcion": clean_description(fields.get("System.Description")),
        "severidad": severity,
        "impacto": severity_code,
        "probabilidad": (
            severity_code
            if type_upper == "ISSUE"
            else value(["Probability", "Probabilidad"])
        ),
        "prioridad": value(["Priority", "Prioridad"]),
        "riskDetalle": risk_detail(value) if type_upper == "RISK" else None,
        "issueDetalle": issue_detail(value) if type_upper == "ISSUE" else None,
        "opportunityDetalle": (
            opportunity_detail(value) if type_upper == "OPPORTUNITY" else None
        ),
        "url": item.get("url")
        or f"{AZURE_BASE_URL}/{encode_url_part(context.organization)}/"
        f"{encode_url_part(context.azure_project)}/_workitems/edit/{item.get('id')}",
        "relacionados": related_items(work_item.get("relations")),
        "cerrado": js_text(fields.get("System.State") or item.get("estado"))
        .strip()
        .upper()
        in CLOSED_STATES,
    }


def assigned_text(person: object, fallback: object) -> str:
    """Nombre del asignado, como en el RAID original."""
    if not person:
        return str(fallback or UNASSIGNED)

    if isinstance(person, dict):
        return str(
            person.get("displayName")
            or person.get("uniqueName")
            or "[object Object]",
        )

    return str(person)


def clean_description(value: object) -> str:
    """Descripcion sin etiquetas HTML ni &nbsp;, hasta 3000 caracteres."""
    text = HTML_TAG.sub(" ", js_text(value)).replace("&nbsp;", " ")

    return text.strip()[:MAX_DESCRIPTION]


def related_items(relations: object) -> list[JsonObject]:
    """Hasta 8 relaciones Related o Hierarchy con su ID."""
    items: list[JsonObject] = []

    for relation in relations if isinstance(relations, list) else []:
        if not RELATED_REL.search(str(relation.get("rel") or "")):
            continue

        url = str(relation.get("url") or "")
        match = TRAILING_ID.search(url)
        items.append({"url": url, "id": match.group(1) if match else ""})

        if len(items) == MAX_RELATED:
            break

    return items


def risk_detail(value: Callable[[Sequence[str]], Any]) -> JsonObject:
    """Campos de detalle de un Risk."""
    return {
        "planMitigacion": value(
            ["Mitigation Plan", "Plan de mitigación", "Improvement Plan"],
        ),
        "triggers": value(["Triggers"]),
        "contingencyPlan": value(["Contingency Plan"]),
        "estrategiaGestion": value(
            ["Management Strategy", "Estrategia de gestión"],
        ),
        "partesInteresadas": value(
            [
                "Stakeholders Affected",
                "Partes interesadas afectadas",
                "Partes interesadas",
            ],
        ),
        "fuenteRiesgo": value(["Risk Source", "Fuente del riesgo"]),
        "categoria": value(["Category", "Categoría"]),
        "escalate": value(["Escalate"]),
        "personaEscala": value(["Escalate To", "Persona a la que se escala"]),
        "fechaSeguimiento": value(["Follow-up Date", "Fecha de seguimiento"]),
        "originalEstimate": value(["Original Estimate", "Estimación original"]),
    }


def issue_detail(value: Callable[[Sequence[str]], Any]) -> JsonObject:
    """Campos de detalle de un Issue."""
    return {
        "plan": value(
            ["Corrective Action Plan", "Plan de mitigación", "Mitigation Plan"],
        ),
        "escalate": value(["Escalate"]),
        "escalationContact": value(
            ["Persona a la que se escala", "Escalation Contact"],
        ),
        "detectionDate": value(["Detection Date", "Fecha de detección"]),
        "reporter": value(["Persona que reporta", "Reporter"]),
        "closureDate": value(["Closure Date", "Fecha de cierre"]),
        "relatedSoftware": value(["Software relacionado", "Related Software"]),
        "originalEstimate": value(["Original Estimate", "Estimación original"]),
        "effortCompleted": value(
            ["Effort completed", "Completed Work", "Trabajo completado"],
        ),
    }


def opportunity_detail(value: Callable[[Sequence[str]], Any]) -> JsonObject:
    """Campos de detalle de una Opportunity."""
    return {
        "improvementPlan": value(
            ["Improvement plan", "Plan de aprovechamiento"]
        ),
        "triggers": value(["Triggers", "Señal de alerta"]),
        "actionPlan": value(["Action plan", "Plan de acción"]),
        "followUp": value(["Follow up", "Seguimiento"]),
        "originalEstimate": value(["Original Estimate", "Estimación original"]),
        "fechaSeguimiento": value(["Fecha de seguimiento", "Follow-up Date"]),
        "escalate": value(["Escalate"]),
        "personaEscala": value(
            ["Persona a la que se escala", "Escalation Contact", "Escalate To"],
        ),
        "estrategiaGestion": value(
            ["Estrategia de gestión", "Management Strategy"],
        ),
        "partesInteresadas": value(
            ["Partes interesadas afectadas", "Stakeholders Affected"],
        ),
        "fuenteOportunidad": value(
            ["Fuente de la oportunidad", "Opportunity Source"],
        ),
        "categoria": value(["Categoría", "Category"]),
    }


def type_definition(
    context: RaidContext, raid_type: object
) -> list[JsonObject]:
    """
    Campos del tipo RAID con tipo, valores permitidos y solo lectura.

    Args:
        context: Contexto del proyecto.
        raid_type: Risk, Issue u Opportunity.

    Returns:
        La definicion de campos.

    Raises:
        RaidError: Cuando el tipo no esta permitido.
    """
    if raid_type not in RAID_TYPES:
        raise RaidError("Tipo no permitido.")

    payload = raid_fetch(
        context,
        "GET",
        f"{context.url}workitemtypes/{encode_url_part(str(raid_type))}/fields",
        params={"api-version": "7.1", "$expand": "allowedValues"},
    )

    return [
        {
            "referenceName": field.get("referenceName"),
            "name": field.get("name"),
            "type": field.get("type") or "",
            "allowedValues": field.get("allowedValues") or [],
            "readOnly": bool(field.get("readOnly")),
        }
        for field in payload.get("value") or []
    ]


def raid_field_types(
    azure: IxsAzure,
    project_value: object,
    raid_type: object,
) -> JsonObject:
    """
    Opciones de los campos principales del tipo (ixsRaidCamposTipo).

    Args:
        azure: Configuracion del panel.
        project_value: ID interno.
        raid_type: Risk, Issue u Opportunity.

    Returns:
        {"ok", "proyectoAzure", "campos"} o {"ok": False, "error"}.
    """
    try:
        context = build_context(azure, project_value)
        definition = type_definition(context, raid_type)
    except DashboardError as error:
        return {"ok": False, "error": error.detail}

    def normalize(text: object) -> str:
        return strip_marks(text).lower()

    def find(keys: Sequence[str]) -> JsonObject | None:
        wanted = [normalize(key) for key in keys]
        field = next(
            (f for f in definition if normalize(f["name"]) in wanted),
            None,
        ) or next(
            (
                f
                for f in definition
                if any(key in normalize(f["name"]) for key in wanted)
            ),
            None,
        )
        return (
            {"nombre": field["name"], "opciones": field["allowedValues"]}
            if field
            else None
        )

    return {
        "ok": True,
        "proyectoAzure": context.azure_project,
        "campos": {
            "severidad": find(["Severity", "Severidad"]),
            "impacto": find(["Impact", "Impacto"]),
            "probabilidad": find(["Probability", "Probabilidad"]),
            "prioridad": find(["Priority", "Prioridad"]),
            "escalate": find(["Escalate"]),
            "estrategiaGestion": find(
                ["Management Strategy", "Estrategia de gestión"],
            ),
            "partesInteresadas": find(
                [
                    "Stakeholders Affected",
                    "Partes interesadas afectadas",
                    "Partes interesadas",
                ],
            ),
            "fuenteRiesgo": find(["Risk Source", "Fuente del riesgo"]),
            "categoria": find(["Category", "Categoría"]),
        },
    }


def iteration_paths(context: RaidContext) -> list[str]:
    """
    Rutas reales de iteracion del Team Project, como ixsRaidAltaIteraciones_().

    Args:
        context: Contexto del proyecto.

    Returns:
        El Team Project seguido de cada ruta, sin repetir.
    """
    tree = raid_fetch(
        context,
        "GET",
        f"{context.url}classificationnodes/iterations",
        params={"$depth": 15, "api-version": "7.1"},
    )
    paths = [context.azure_project]
    seen = {context.azure_project.lower()}

    def walk(node: Mapping[str, Any], parent: str) -> None:
        for child in node.get("children") or []:
            name = js_text(child.get("name")).strip()
            path = f"{parent}\\{name}"

            if name and path.lower() not in seen:
                paths.append(path)
                seen.add(path.lower())

            walk(child, path)

    walk(tree, context.azure_project)

    return paths


def normalize_path(value: object) -> str:
    """Ruta con diagonales invertidas simples y en minusculas."""
    text = js_text(value).strip().replace("/", "\\")

    return re.sub(r"\\{2,}", r"\\", text).lower()


def find_editable_field(
    definition: Sequence[JsonObject],
    exact_names: Sequence[str],
    partial_names: Sequence[str],
) -> JsonObject | None:
    """
    Campo editable por nombre visible, como ixsRaidAltaCampo_().

    Args:
        definition: Campos del tipo.
        exact_names: Nombres exactos.
        partial_names: Fragmentos de respaldo.

    Returns:
        El campo, o None.
    """

    def normalize(text: object) -> str:
        return re.sub(r"[^a-z0-9]+", " ", strip_marks(text).lower()).strip()

    eligible = [
        field
        for field in definition
        if field.get("referenceName")
        and not field.get("readOnly")
        and field.get("referenceName") != "System.CreatedDate"
    ]
    exact = [normalize(name) for name in exact_names]
    partial = [normalize(name) for name in partial_names]

    return next(
        (field for field in eligible if normalize(field.get("name")) in exact),
        None,
    ) or next(
        (
            field
            for field in eligible
            if any(name in normalize(field.get("name")) for name in partial)
        ),
        None,
    )


def locale_key(text: str) -> tuple[str, str, str]:
    """Orden como localeCompare('es')."""
    return strip_marks(text).lower(), text.lower(), text.swapcase()


def raid_creation_options(
    azure: IxsAzure,
    project_value: object,
    raid_type: object,
) -> JsonObject:
    """
    Iteraciones, usuarios, relacionados y campos para dar de alta.

    Args:
        azure: Configuracion del panel.
        project_value: ID interno.
        raid_type: Risk, Issue u Opportunity.

    Returns:
        Las opciones del formulario o {"ok": False, "error"}.
    """
    try:
        context = build_context(azure, project_value)

        if raid_type not in RAID_TYPES:
            return {"ok": False, "error": "Tipo de registro no permitido."}

        paths = iteration_paths(context)
        definition = type_definition(context, raid_type)
        fields: dict[str, JsonObject | None] = {}

        for key, (exact, partial) in OPTION_FIELDS.items():
            field = find_editable_field(definition, exact, partial)
            fields[key] = (
                {
                    "nombre": field["name"],
                    "opciones": field.get("allowedValues") or [],
                    "tipo": field.get("type"),
                    "referenceName": field["referenceName"],
                }
                if field
                else None
            )

        escaped = context.azure_project.replace("'", "''")
        query = raid_fetch(
            context,
            "POST",
            f"{context.url}wiql",
            params={"api-version": "7.1"},
            json={
                "query": "SELECT [System.Id] FROM WorkItems WHERE "
                f"[System.TeamProject] = '{escaped}' ORDER BY "
                "[System.ChangedDate] DESC",
            },
        )
        ids = [
            item["id"]
            for item in query.get("workItems") or []
            if item.get("id")
        ][:OPTIONS_MAX_ITEMS]
        users: dict[str, JsonObject] = {}
        related: list[JsonObject] = []

        for start in range(0, len(ids), OPTIONS_BATCH_SIZE):
            end = start + OPTIONS_BATCH_SIZE
            page = raid_fetch(
                context,
                "GET",
                f"{context.url}workitems",
                params={
                    "ids": ",".join(str(item_id) for item_id in ids[start:end]),
                    "fields": "System.Id,System.Title,System.AssignedTo,"
                    "System.WorkItemType",
                    "api-version": "7.1",
                },
            )

            for work_item in page.get("value") or []:
                add_option_item(work_item, users, related)
    except DashboardError as error:
        return {"ok": False, "error": error.detail}

    return {
        "ok": True,
        "proyectoAzure": context.azure_project,
        "iteracionDefault": context.azure_project,
        "iteraciones": paths,
        "usuarios": sorted(
            users.values(),
            key=lambda user: locale_key(str(user["nombre"])),
        ),
        "relacionados": related,
        "campos": fields,
    }


def add_option_item(
    work_item: Mapping[str, Any],
    users: dict[str, JsonObject],
    related: list[JsonObject],
) -> None:
    """Agrega el asignado (sin repetir) y el work item relacionable."""
    fields = work_item.get("fields") or {}
    assigned = fields.get("System.AssignedTo")

    if assigned:
        person = assigned if isinstance(assigned, dict) else {}
        email = js_text(
            person.get("uniqueName") or person.get("mailAddress"),
        ).strip()
        name = js_text(person.get("displayName") or email).strip()
        key = (email or name).lower()

        if key and key not in users:
            users[key] = {
                "nombre": name,
                "email": email,
                "valor": email or name,
            }

    related.append(
        {
            "id": work_item.get("id"),
            "titulo": js_text(fields.get("System.Title")),
            "tipo": js_text(fields.get("System.WorkItemType")),
        },
    )


def format_plan_list(value: object, field_type: object) -> str:
    """
    Acciones como lista HTML o con viñetas (ixsRaidIssuePlanFormato_).

    Args:
        value: Texto con viñetas, guiones o numeros.
        field_type: Tipo del campo en Azure.

    Returns:
        <ul><li>…</li></ul> para campos HTML; "• …" por linea en otro caso.
    """
    raw = BR_TAG.sub("\n", js_text(value).replace("\r", ""))
    raw = LIST_BULLETS.sub("\n• ", raw)
    raw = LIST_MARKERS.sub("\n• ", raw)
    lines = [
        re.sub(r"^•\s*", "", line.strip()).strip()
        for line in re.split(r"\n+", raw)
    ]
    lines = [line for line in lines if line]

    if not lines:
        return ""

    if re.search("html", js_text(field_type), re.IGNORECASE):
        return (
            "<ul>"
            + "".join(f"<li>{escape_html(line)}</li>" for line in lines)
            + "</ul>"
        )

    return "\n".join(f"• {line}" for line in lines)


def escape_html(text: object) -> str:
    """Escapa &, <, > y comillas dobles."""
    return (
        js_text(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def escape_description(text: object) -> str:
    """Escapa &, <, > y convierte saltos de linea en <br>."""
    escaped = (
        js_text(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )

    return re.sub(r"\r?\n", "<br>", escaped)


class OperationBuilder:
    """Arma el JSON Patch validando campos y valores reales del proceso."""

    def __init__(
        self,
        definition: Sequence[JsonObject],
        raid_type: str,
        operations: list[JsonObject],
    ) -> None:
        self._definition = definition
        self._raid_type = raid_type
        self.operations = operations
        self._added = {
            "System.Title",
            "System.AreaPath",
            "System.IterationPath",
            "System.Description",
            "System.AssignedTo",
        }

    def field(
        self,
        exact: Sequence[str],
        partial: Sequence[str] | None = None,
    ) -> JsonObject | None:
        """Campo editable por nombre visible."""
        return find_editable_field(self._definition, exact, partial or exact)

    def put(
        self,
        value: object,
        exact: Sequence[str],
        partial: Sequence[str] | None = None,
    ) -> bool:
        """
        Agrega el campo si existe y el valor es valido.

        Raises:
            RaidError: Valor fuera de las opciones (salvo en Risk).
        """
        if is_blank(value):
            return False

        field = self.field(exact, partial or exact)

        if field is None or field["referenceName"] in self._added:
            return False

        final_value: Any = value
        allowed = field.get("allowedValues") or []

        if allowed:
            match = find_allowed(allowed, value)

            if match is None:
                if self._raid_type == "Risk":
                    return False

                options = ", ".join(js_text(option) for option in allowed)
                raise RaidError(
                    f"Valor «{js_text(value)}» no permitido para "
                    f"{field['name']}. Opciones: {options}",
                )

            final_value = match

        final_value = convert_by_type(final_value, field.get("type"))
        self._added.add(field["referenceName"])
        self.operations.append(
            {
                "op": "add",
                "path": f"/fields/{field['referenceName']}",
                "value": final_value,
            },
        )

        return True


def find_allowed(allowed: Sequence[Any], value: object) -> Any:
    """Opcion permitida igual al valor, o por numero de Severity."""

    def normalize(text: object) -> str:
        return strip_marks(text).lower().strip()

    wanted = normalize(value)
    match = next(
        (option for option in allowed if normalize(option) == wanted), None
    )

    if match is None and DIGITS.fullmatch(js_text(value).strip()):
        number = js_text(value).strip()
        match = next(
            (option for option in allowed if severity_number(option) == number),
            None,
        )

    return match


def str_value(value: object) -> str:
    """Texto como String(x), sin tratar los vacios."""
    if isinstance(value, str | int | float) or value is None:
        return to_text(value)

    return str(value)


def is_blank(value: object) -> bool:
    """Como value == null || String(value).trim() === ''."""
    return value is None or str_value(value).strip() == ""


def js_number(value: object) -> int | float | None:
    """
    Number(x) de JavaScript; NaN se serializa como null.

    Args:
        value: Valor a convertir.

    Returns:
        El numero (entero si no tiene decimales) o None si es NaN.
    """
    if isinstance(value, bool):
        return int(value)

    if isinstance(value, int | float):
        number = float(value)
    else:
        text = str_value(value).strip()

        try:
            number = float(text) if text else 0.0
        except ValueError:
            return None

    if number != number or abs(number) == float("inf"):
        return None

    return int(number) if number.is_integer() else number


def convert_by_type(value: Any, field_type: object) -> Any:
    """Numeros a numero y fechas YYYY-MM-DD a mediodia UTC."""
    type_text = js_text(field_type)

    if NUMERIC_TYPE.match(type_text) and str_value(value).strip() != "":
        return js_number(value)

    if DATE_TYPE.match(type_text) and ISO_DAY.fullmatch(str_value(value)):
        return f"{value}T12:00:00Z"

    return value


def create_raid_record(
    azure: IxsAzure,
    project_value: object,
    raid_type: object,
    data_value: object,
) -> JsonObject:
    """
    Crea un Risk, Issue u Opportunity (ixsRaidCrearRegistro).

    Args:
        azure: Configuracion del panel.
        project_value: ID interno.
        raid_type: Risk, Issue u Opportunity.
        data_value: Datos del formulario.

    Returns:
        {"ok", "id", "iterationPath", ...} o {"ok": False, "error"}.
    """
    try:
        return create_raid_record_or_raise(
            azure,
            project_value,
            raid_type,
            data_value,
        )
    except DashboardError as error:
        return {"ok": False, "error": error.detail}


def create_raid_record_or_raise(
    azure: IxsAzure,
    project_value: object,
    raid_type: object,
    data_value: object,
) -> JsonObject:
    """Cuerpo de create_raid_record; los errores se convierten afuera."""
    context = build_context(azure, project_value)

    if raid_type not in RAID_TYPES:
        return {"ok": False, "error": "Tipo no permitido."}

    raid_type_text = str(raid_type)
    data: dict[str, Any] = (
        dict(data_value) if isinstance(data_value, dict) else {}
    )
    title = js_text(data.get("titulo")).strip()

    if not title:
        return {"ok": False, "error": "Escribe el título."}

    if not js_text(data.get("descripcion")).strip():
        return {"ok": False, "error": "Escribe la descripción."}

    definition = type_definition(context, raid_type_text)
    root = context.azure_project
    paths = iteration_paths(context)
    typed_path = js_text(data.get("iterationPath")).strip() or root
    iteration = next(
        (
            path
            for path in paths
            if normalize_path(path) == normalize_path(typed_path)
        ),
        "",
    )

    if not iteration:
        examples = " | ".join(paths[:5])
        return {
            "ok": False,
            "error": f"Iteration Path no existe en el Team Project «{root}»: "
            f"«{typed_path}». Selecciona una ruta sugerida por Azure. "
            f"Ejemplos: {examples}",
        }

    description_parts = [escape_description(data.get("descripcion"))]

    if raid_type_text == "Issue":
        for label, key in (
            ("Causa", "causa"),
            ("Impacto real", "impacto"),
            ("Acción correctiva", "accionCorrectiva"),
        ):
            if js_text(data.get(key)).strip():
                description_parts.append(
                    f"<p><strong>{escape_description(label)}:</strong><br>"
                    f"{escape_description(data.get(key))}</p>",
                )

    operations: list[JsonObject] = [
        {"op": "add", "path": "/fields/System.Title", "value": title},
        {"op": "add", "path": "/fields/System.AreaPath", "value": root},
        {
            "op": "add",
            "path": "/fields/System.IterationPath",
            "value": iteration,
        },
    ]

    if js_text(data.get("responsable")).strip():
        operations.append(
            {
                "op": "add",
                "path": "/fields/System.AssignedTo",
                "value": js_text(data.get("responsable")).strip(),
            },
        )

    builder = OperationBuilder(definition, raid_type_text, operations)
    severity = data.get("severidad") or data.get("nivel")
    severity_code = severity_number(severity)

    if js_text(severity).strip() and not severity_code:
        return {
            "ok": False,
            "error": "Severity debe comenzar con un numero, por ejemplo: "
            "2 - Medium. Selecciona el valor real de Azure.",
        }

    builder.put(severity, ["Severity", "Severidad"], ["severity", "severidad"])
    builder.put(
        data.get("prioridad"),
        ["Priority", "Prioridad"],
        ["priority", "prioridad"],
    )
    builder.put(
        severity_code
        if raid_type_text == "Issue"
        else data.get("probabilidad"),
        ["Probability", "Probabilidad"],
        ["probability", "probabilidad"],
    )
    builder.put(severity_code, ["Impact", "Impacto"], ["impact"])
    extra: list[tuple[str, Any]] = []

    if raid_type_text == "Risk":
        add_risk_fields(builder, data)
    elif raid_type_text == "Issue":
        extra = add_issue_fields(builder, data, root)
    else:
        add_opportunity_fields(builder, data, root)

    for label, value in extra:
        if js_text(value).strip():
            description_parts.append(
                f"<p><strong>{escape_description(label)}:</strong><br>"
                f"{escape_description(value)}</p>",
            )

    operations.append(
        {
            "op": "add",
            "path": "/fields/System.Description",
            "value": "<br>".join(description_parts),
        },
    )
    related_id = re.sub(
        r"^#", "", js_text(data.get("relatedWorkItemId")).strip()
    )

    if related_id:
        if not DIGITS.fullmatch(related_id):
            return {
                "ok": False,
                "error": "El Work Item relacionado debe ser un ID numerico "
                "valido de Azure.",
            }

        try:
            raid_fetch(
                context,
                "GET",
                f"{context.url}workitems/{related_id}",
                params={"api-version": "7.1"},
            )
        except DashboardError as error:
            return {
                "ok": False,
                "error": f"No se puede relacionar con #{related_id}: "
                f"{error.detail}",
            }

        operations.append(
            {
                "op": "add",
                "path": "/relations/-",
                "value": {
                    "rel": PARENT_REL,
                    "url": f"{AZURE_BASE_URL}/"
                    f"{encode_url_part(context.organization)}"
                    f"/_apis/wit/workItems/{related_id}",
                },
            },
        )

    created = raid_fetch(
        context,
        "POST",
        f"{context.url}workitems/${encode_url_part(raid_type_text)}",
        params={"api-version": "7.1"},
        data=json.dumps(operations),
        headers={"Content-Type": "application/json-patch+json"},
    )
    confirmed, notice = verify_parent_link(
        context, created.get("id"), related_id
    )

    return {
        "ok": True,
        "id": created.get("id"),
        "iterationPath": iteration,
        "parentId": related_id or "",
        "childId": created.get("id"),
        "vinculoConfirmado": confirmed,
        "aviso": notice,
        "url": f"{AZURE_BASE_URL}/{encode_url_part(context.organization)}/"
        f"{encode_url_part(context.azure_project)}/_workitems/edit/"
        f"{created.get('id')}",
    }


def add_risk_fields(builder: OperationBuilder, data: Mapping[str, Any]) -> None:
    """Campos propios de un Risk."""
    builder.put(
        data.get("planMitigacion"),
        ["Mitigation Plan", "Plan de mitigación"],
        ["mitigation plan", "mitigacion"],
    )
    builder.put(data.get("triggers"), ["Triggers"], ["trigger"])
    builder.put(
        data.get("contingencyPlan"), ["Contingency Plan"], ["contingency"]
    )
    builder.put(
        data.get("categoria"),
        ["Category", "Categoría"],
        ["category", "categoria"],
    )
    builder.put(
        data.get("fuenteRiesgo"),
        ["Risk Source", "Fuente del riesgo"],
        ["risk source", "fuente del riesgo"],
    )
    builder.put(
        data.get("estrategiaGestion"),
        ["Management Strategy", "Estrategia de gestión"],
        ["management strategy", "estrategia"],
    )
    builder.put(
        data.get("partesInteresadas"),
        ["Stakeholders Affected", "Partes interesadas"],
        ["stakeholders", "partes interesadas"],
    )
    builder.put(
        data.get("personaEscala"),
        ["Escalate To", "Persona a la que se escala"],
        ["escalate to", "persona a la que se escala"],
    )
    builder.put(data.get("escalate"), ["Escalate"], ["escalate"])
    builder.put(
        data.get("fechaSeguimiento"),
        ["Follow-up Date", "Fecha de seguimiento"],
        ["follow-up date", "fecha de seguimiento"],
    )


def require(
    builder: OperationBuilder,
    value: object,
    spec: FieldSpec,
    message: str,
) -> None:
    """Agrega un campo obligatorio cuando trae valor; si no existe, falla."""
    if is_blank(value):
        return

    if not builder.put(value, spec[0], spec[1]):
        raise RaidError(message)


def add_issue_fields(
    builder: OperationBuilder,
    data: Mapping[str, Any],
    root: str,
) -> list[tuple[str, Any]]:
    """
    Campos propios de un Issue.

    Returns:
        Los opcionales que no existen en el proceso (van a Description).
    """

    def missing(label: str) -> str:
        return (
            f"No se encontró el campo editable «{label}» en el tipo Issue de "
            f"«{root}». Revisa que exista en Azure DevOps → Process → Issue. "
            "No se creó el Issue para evitar guardar ese dato solo en "
            "Description."
        )

    plan_field = builder.field(ISSUE_FIELDS["plan"][0], ISSUE_FIELDS["plan"][1])
    require(
        builder,
        format_plan_list(
            data.get("planMitigacion"),
            plan_field.get("type") if plan_field else None,
        ),
        ISSUE_FIELDS["plan"],
        missing("Corrective Action Plan (Plan de mitigación)"),
    )
    require(
        builder,
        data.get("escalationContact"),
        ISSUE_FIELDS["escalationContact"],
        missing("Persona a la que se escala"),
    )
    require(
        builder,
        data.get("detectionDate"),
        ISSUE_FIELDS["detectionDate"],
        missing("Detection Date (Fecha de detección)"),
    )
    require(
        builder,
        data.get("reporter"),
        ISSUE_FIELDS["reporter"],
        missing("Persona que reporta"),
    )
    require(
        builder,
        data.get("relatedSoftware"),
        ISSUE_FIELDS["relatedSoftware"],
        missing("Software relacionado"),
    )
    extra: list[tuple[str, Any]] = []

    for key, exact, partial, label in (
        ("state", ["State", "Estado"], ["state"], "State"),
        ("reason", ["Reason", "Motivo"], ["reason"], "Reason"),
        ("escalate", ["Escalate", "¿Escalar?"], ["escalate"], "Escalate"),
        (
            "closureDate",
            ["Closure Date", "Fecha de cierre"],
            ["closure date"],
            "Closure Date",
        ),
        (
            "originalEstimate",
            ["Original Estimate", "Estimación original"],
            ["original estimate"],
            "Original Estimate",
        ),
        (
            "effortCompleted",
            ["Effort completed", "Completed Work", "Trabajo completado"],
            ["effort completed", "completed work"],
            "Effort completed",
        ),
    ):
        if not builder.put(data.get(key), exact, partial):
            extra.append((label, data.get(key)))

    return extra


def add_opportunity_fields(
    builder: OperationBuilder,
    data: Mapping[str, Any],
    root: str,
) -> None:
    """Campos propios de una Opportunity (todos obligatorios si traen valor)."""

    def required(
        value: object, exact: list[str], partial: list[str], label: str
    ) -> None:
        require(
            builder,
            value,
            (exact, partial),
            f"No se encontró el campo editable «{label}» en Opportunity de "
            f"«{root}». No se creó el WI.",
        )

    improvement = builder.field(
        ["Improvement plan", "Plan de aprovechamiento"],
        ["improvement plan", "plan de aprovechamiento"],
    )
    action = builder.field(
        ["Action plan", "Plan de acción"],
        ["action plan", "plan de accion"],
    )
    required(
        format_plan_list(
            data.get("planAprovechamiento"),
            improvement.get("type") if improvement else None,
        ),
        ["Improvement plan", "Plan de aprovechamiento"],
        ["improvement plan", "plan de aprovechamiento"],
        "Improvement plan",
    )
    required(
        data.get("senalAlerta"),
        ["Triggers", "Señal de alerta"],
        ["triggers", "senal de alerta"],
        "Triggers",
    )
    required(
        format_plan_list(
            data.get("planAccion"),
            action.get("type") if action else None,
        ),
        ["Action plan", "Plan de acción"],
        ["action plan", "plan de accion"],
        "Action plan",
    )

    for key, exact, partial, label in (
        (
            "followUp",
            ["Follow up", "Seguimiento"],
            ["follow up", "seguimiento"],
            "Follow up",
        ),
        (
            "originalEstimate",
            ["Original Estimate", "Estimación original"],
            ["original estimate"],
            "Original Estimate",
        ),
        (
            "fechaSeguimiento",
            ["Fecha de seguimiento", "Follow-up Date"],
            ["fecha de seguimiento", "follow-up date"],
            "Fecha de seguimiento",
        ),
        ("escalate", ["Escalate", "¿Escalar?"], ["escalate"], "Escalate"),
        (
            "personaEscala",
            ["Persona a la que se escala", "Escalation Contact", "Escalate To"],
            ["persona a la que se escala", "escalation contact", "escalate to"],
            "Persona a la que se escala",
        ),
        (
            "estrategiaGestion",
            ["Estrategia de gestión", "Management Strategy"],
            ["estrategia de gestion", "management strategy"],
            "Estrategia de gestión",
        ),
        (
            "partesInteresadas",
            ["Partes interesadas afectadas", "Stakeholders Affected"],
            ["partes interesadas afectadas", "stakeholders affected"],
            "Partes interesadas afectadas",
        ),
        (
            "fuenteOportunidad",
            ["Fuente de la oportunidad", "Opportunity Source"],
            ["fuente de la oportunidad", "opportunity source"],
            "Fuente de la oportunidad",
        ),
        (
            "categoria",
            ["Categoría", "Category"],
            ["categoria", "category"],
            "Categoría",
        ),
        ("state", ["State", "Estado"], ["state"], "State"),
        ("reason", ["Reason", "Motivo"], ["reason"], "Reason"),
    ):
        required(data.get(key), exact, partial, label)


def verify_parent_link(
    context: RaidContext,
    created_id: object,
    related_id: str,
) -> tuple[bool, str]:
    """
    Confirma que el nuevo work item quedo como hijo del relacionado.

    Args:
        context: Contexto del proyecto.
        created_id: ID creado.
        related_id: ID padre ("" si no hay).

    Returns:
        Si se confirmo y el aviso para el usuario.
    """
    if not related_id:
        return True, ""

    try:
        created = raid_fetch(
            context,
            "GET",
            f"{context.url}workitems/{created_id}",
            params={"$expand": "relations", "api-version": "7.1"},
        )
    except DashboardError as error:
        return False, (
            f"Azure creó el WI #{created_id} con el enlace Parent solicitado, "
            "pero no fue posible consultar las relaciones para verificarlo: "
            f"{error.detail}"
        )

    confirmed = any(
        relation.get("rel") == PARENT_REL
        and str(relation.get("url") or "")
        .split("?")[0]
        .removesuffix("/")
        .endswith(f"/{related_id}")
        for relation in created.get("relations") or []
    )

    if confirmed:
        return True, ""

    return False, (
        f"Azure creó el WI #{created_id}, pero la consulta posterior no "
        "confirmó el enlace Parent → Child. Revísalo en Azure; no vuelvas a "
        "crear el registro para evitar duplicarlo."
    )
