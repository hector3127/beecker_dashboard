"""Formulario y alta de riesgos en Azure DevOps desde el panel Daily."""

import re
import unicodedata
from collections.abc import Callable, Mapping
from datetime import datetime
from typing import Any

from apps.azure_devops.services.azure_client import encode_url_part
from apps.azure_devops.services.raid_cache import clear_raid_cache
from apps.daily.constants import (
    AZURE_BASE_URL,
    ERROR_BODY_CHARS,
    MAX_WORK_ITEMS,
    RISK_TYPE,
)
from apps.daily.exceptions import AzureHttpError
from apps.daily.services.work_items import (
    CONNECT_FIRST,
    DailyAzure,
    wiql_project_filter,
    work_item_url,
)
from core.exceptions import DashboardError
from core.utils.dates import to_utc_iso

"""BKD.070.011 - Riesgos en Azure del Daily
Equivale a obtenerFormularioRiesgoAzure() (con _autoMapearCamposRiesgo),
buscarIteraciones(), buscarUsuariosAzureDevOps(),
buscarWorkItemsParaRelacionar(), crearWorkItemRiesgoAzure() y
agregarComentarioWorkItem().
"""

JsonObject = dict[str, Any]

FIELDS_CACHE_SECONDS = 3600
ITERATIONS_CACHE_SECONDS = 3600
ASSIGNEES_CACHE_SECONDS = 1800
SEARCHABLE_CACHE_SECONDS = 600
SEARCH_LIMIT = 8
CREATE_ERROR_CHARS = 500
WRITE_DENIED_STATUSES = frozenset({401, 403})
WRITE_DENIED_MESSAGE = (
    "Tu token no tiene permiso de escritura. Regenera tu PAT con scope "
    '"Work Items > Read & Write".'
)
DIGITS_ONLY = re.compile(r"[0-9]+")

# Llave logica -> (nombres exactos, palabras clave de respaldo).
RISK_FIELD_RULES: dict[str, tuple[tuple[str, ...], tuple[str, ...]]] = {
    "severidad": (("Severity", "Severidad"), ("severity", "severidad")),
    "prioridad": (("Priority", "Prioridad"), ("priority", "prioridad")),
    "planMitigacion": (
        ("Mitigation Plan", "Plan de mitigación", "Plan de mitigacion"),
        ("mitigation plan", "mitigation", "mitigacion"),
    ),
    "triggers": (("Triggers", "Trigger"), ("trigger",)),
    "contingencyPlan": (("Contingency Plan",), ("contingency",)),
    "probabilidad": (
        ("Probability", "Probabilidad"),
        ("probability", "probabilidad"),
    ),
    "categoria": (
        ("Categoria", "Categoría", "Category"),
        ("category", "categoria"),
    ),
    "fuenteRiesgo": (
        ("Fuente del riesgo", "Risk Source"),
        ("risk source", "fuente del riesgo", "fuente"),
    ),
    "partesInteresadas": (
        ("Partes interesadas afectada", "Stakeholders Affected"),
        ("stakeholder", "partes interesadas"),
    ),
    "personaEscala": (
        ("Persona a la que se escala", "Escalate To"),
        ("escalate to", "persona a la que se escala", "persona escala"),
    ),
    "estrategiaGestion": (
        ("Estrategia de gestión", "Management Strategy"),
        ("management strategy", "estrategia de gestion", "estrategia"),
    ),
    "fechaSeguimiento": (
        ("Fecha de seguimiento", "Follow-up Date"),
        ("follow-up date", "fecha de seguimiento", "seguimiento"),
    ),
    "escalate": (("Escalate",), ("escalate",)),
}


def normalize_field_name(value: object) -> str:
    """
    Normaliza un nombre: minusculas, sin acentos, sin espacios externos.

    Args:
        value: Nombre del campo.

    Returns:
        El nombre normalizado.
    """
    text = unicodedata.normalize("NFD", str(value or "").lower())

    return "".join(
        character
        for character in text
        if not 0x0300 <= ord(character) <= 0x036F
    ).strip()


def cached_result(
    azure: DailyAzure,
    cache_suffix: str,
    timeout: int,
    load: Callable[[], JsonObject],
) -> JsonObject:
    """
    Lee un resultado de cache; solo los exitosos se guardan.

    Args:
        azure: Conexion del panel.
        cache_suffix: Variante de cache.
        timeout: Segundos de cache.
        load: Consulta a Azure.

    Returns:
        El resultado.
    """
    cache_key = f"{azure.connection.cache_prefix}{cache_suffix}"
    cached = azure.cache.get(cache_key)

    if isinstance(cached, dict):
        return cached

    result = load()

    if result.get("ok"):
        azure.cache.set(cache_key, result, timeout)

    return result


def load_type_fields(azure: DailyAzure, work_item_type: str) -> JsonObject:
    """
    Campos del tipo de work item con sus valores permitidos (1 hora).

    Args:
        azure: Conexion del panel.
        work_item_type: Tipo de work item.

    Returns:
        {"ok", "campos"} o {"ok": False, "error"}.
    """
    if not azure.connection.is_complete:
        return {"ok": False, "error": CONNECT_FIRST}

    def load() -> JsonObject:
        try:
            payload = azure.build_client().get_type_fields(
                azure.connection.project,
                work_item_type,
            )
        except AzureHttpError as error:
            return {
                "ok": False,
                "error": "No se pudo leer la definición de campos: "
                f"{error.status_code}",
            }

        return {
            "ok": True,
            "campos": [
                {
                    "referenceName": field.get("referenceName"),
                    "name": field.get("name"),
                    "allowedValues": field.get("allowedValues") or [],
                }
                for field in payload.get("value") or []
            ],
        }

    return cached_result(
        azure,
        f"_campos_{work_item_type}",
        FIELDS_CACHE_SECONDS,
        load,
    )


def map_risk_fields(azure: DailyAzure) -> JsonObject:
    """
    Ubica los campos logicos del riesgo por su nombre visible.

    Args:
        azure: Conexion del panel.

    Returns:
        {"ok", "mapa", "camposCrudos"} o {"ok": False, "error"}.
    """
    definition = load_type_fields(azure, RISK_TYPE)

    if not definition.get("ok"):
        return {"ok": False, "error": definition.get("error")}

    fields: list[JsonObject] = definition["campos"]
    used: set[str] = set()
    mapping: dict[str, JsonObject | None] = {}

    for key, (exact_names, keywords) in RISK_FIELD_RULES.items():
        exact = {normalize_field_name(name) for name in exact_names}
        partial = [normalize_field_name(word) for word in keywords]
        available = [
            field for field in fields if field.get("referenceName") not in used
        ]
        field = next(
            (
                field
                for field in available
                if normalize_field_name(field.get("name")) in exact
            ),
            None,
        ) or next(
            (
                field
                for field in available
                if any(
                    word in normalize_field_name(field.get("name"))
                    for word in partial
                )
            ),
            None,
        )

        if field is not None:
            used.add(str(field.get("referenceName")))

        mapping[key] = field

    return {"ok": True, "mapa": mapping, "camposCrudos": fields}


def build_risk_form(azure: DailyAzure) -> JsonObject:
    """
    Campos del formulario de riesgo con las opciones reales de Azure.

    Args:
        azure: Conexion del panel.

    Returns:
        {"ok", "campos"} o {"ok": False, "error"}.
    """
    mapped = map_risk_fields(azure)

    if not mapped.get("ok"):
        return mapped

    return {
        "ok": True,
        "campos": {
            key: (
                {
                    "referenceName": field.get("referenceName"),
                    "nombreVisible": field.get("name"),
                    "opciones": field.get("allowedValues"),
                }
                if field
                else None
            )
            for key, field in mapped["mapa"].items()
        },
    }


def load_iterations(azure: DailyAzure) -> JsonObject:
    """
    Iteration Paths del proyecto con sus fechas (1 hora).

    Args:
        azure: Conexion del panel.

    Returns:
        {"ok", "iteraciones"} o {"ok": False, "error", "iteraciones": []}.
    """
    if not azure.connection.is_complete:
        return {"ok": False, "error": CONNECT_FIRST, "iteraciones": []}

    def load() -> JsonObject:
        try:
            root = azure.build_client().get_iteration_tree(
                azure.connection.project,
            )
        except AzureHttpError as error:
            return {
                "ok": False,
                "error": f"No se pudo leer iteraciones: {error.status_code}",
                "iteraciones": [],
            }

        iterations: list[JsonObject] = []
        collect_iterations(root, "", iterations)

        return {"ok": True, "iteraciones": iterations}

    return cached_result(azure, "_iteraciones", ITERATIONS_CACHE_SECONDS, load)


def collect_iterations(
    node: Mapping[str, Any],
    parent_path: str,
    iterations: list[JsonObject],
) -> None:
    """
    Recorre el arbol de iteraciones y agrega cada ruta.

    Args:
        node: Nodo del arbol.
        parent_path: Ruta del padre.
        iterations: Lista donde se agregan.
    """
    path = (
        f"{parent_path}\\{node.get('name')}"
        if parent_path
        else str(
            node.get("name"),
        )
    )
    attributes = node.get("attributes") or {}
    iterations.append(
        {
            "path": path,
            "fechaInicio": iso_or_none(attributes.get("startDate")),
            "fechaFin": iso_or_none(attributes.get("finishDate")),
        },
    )

    for child in node.get("children") or []:
        collect_iterations(child, path, iterations)


def iso_or_none(value: object) -> str | None:
    """
    Normaliza una fecha ISO de Azure como fechaSeguraRecursos().

    Args:
        value: Texto ISO.

    Returns:
        La fecha ISO UTC con milisegundos, o None.
    """
    if not isinstance(value, str) or not value:
        return None

    try:
        moment = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None

    return to_utc_iso(moment)


def search_text(query: object) -> str:
    """
    Texto de busqueda en minusculas y sin espacios externos.

    Args:
        query: Texto recibido.

    Returns:
        El texto normalizado.
    """
    return str(query).lower().strip() if query else ""


def search_iterations(azure: DailyAzure, query: object) -> JsonObject:
    """
    Busca Iteration Paths que contienen el texto (maximo 8).

    Args:
        azure: Conexion del panel.
        query: Texto buscado.

    Returns:
        {"ok", "iteraciones"}.
    """
    result = load_iterations(azure)

    if not result.get("ok"):
        return result

    text = search_text(query)
    iterations: list[JsonObject] = result["iteraciones"]

    return {
        "ok": True,
        "iteraciones": [
            iteration
            for iteration in iterations
            if not text or text in str(iteration["path"]).lower()
        ][:SEARCH_LIMIT],
    }


def query_field_values(
    azure: DailyAzure,
    query: str,
    fields: str,
) -> list[JsonObject]:
    """
    Ejecuta la WIQL y lee campos de hasta 200 work items.

    Args:
        azure: Conexion del panel.
        query: Consulta WIQL.
        fields: Campos separados por coma.

    Returns:
        Los work items.

    Raises:
        DashboardError: Con el mensaje "WIQL falló" o "Detalle falló".
    """
    client = azure.build_client()

    try:
        ids = client.run_wiql(azure.connection.project, query)[:MAX_WORK_ITEMS]
    except AzureHttpError as error:
        raise DashboardError(f"WIQL falló: {error.status_code}") from error

    if not ids:
        return []

    try:
        return client.get_work_items(
            azure.connection.project,
            ids,
            fields.split(","),
        )
    except AzureHttpError as error:
        raise DashboardError(f"Detalle falló: {error.status_code}") from error


def load_assignees(azure: DailyAzure) -> JsonObject:
    """
    Personas asignadas en los work items del proyecto (30 minutos).

    Args:
        azure: Conexion del panel.

    Returns:
        {"ok", "usuarios"} o {"ok": False, "error", "usuarios": []}.
    """
    if not azure.connection.is_complete:
        return {"ok": False, "error": CONNECT_FIRST, "usuarios": []}

    def load() -> JsonObject:
        query = (
            "SELECT [System.Id] FROM WorkItems WHERE "
            f"{wiql_project_filter(azure.connection.project)} "
            "ORDER BY [System.ChangedDate] DESC"
        )

        try:
            work_items = query_field_values(azure, query, "System.AssignedTo")
        except DashboardError as error:
            return {"ok": False, "error": error.detail, "usuarios": []}

        names: dict[str, str] = {}

        for work_item in work_items:
            assigned = (work_item.get("fields") or {}).get("System.AssignedTo")

            if isinstance(assigned, dict) and assigned.get("uniqueName"):
                email = str(assigned["uniqueName"])
                names[email] = str(assigned.get("displayName") or email)

        users = sorted(
            ({"nombre": name, "email": email} for email, name in names.items()),
            key=lambda user: locale_key(user["nombre"]),
        )

        return {"ok": True, "usuarios": users}

    return cached_result(azure, "_asignados", ASSIGNEES_CACHE_SECONDS, load)


def locale_key(text: str) -> tuple[str, str, str]:
    """
    Orden como localeCompare: letra base, acentos y luego minusculas.

    Args:
        text: Texto a ordenar.

    Returns:
        La llave de orden.
    """
    return normalize_field_name(text), text.lower(), text.swapcase()


def search_users(azure: DailyAzure, query: object) -> JsonObject:
    """
    Busca personas por nombre o correo (maximo 8).

    Args:
        azure: Conexion del panel.
        query: Texto buscado.

    Returns:
        {"ok", "usuarios"}.
    """
    result = load_assignees(azure)

    if not result.get("ok"):
        return result

    text = search_text(query)
    users: list[JsonObject] = result["usuarios"]

    return {
        "ok": True,
        "usuarios": [
            user
            for user in users
            if not text
            or text in str(user["nombre"]).lower()
            or text in str(user["email"]).lower()
        ][:SEARCH_LIMIT],
    }


def load_searchable_work_items(azure: DailyAzure) -> JsonObject:
    """
    Work items no cerrados para relacionar (10 minutos).

    Args:
        azure: Conexion del panel.

    Returns:
        {"ok", "items"} o {"ok": False, "error", "items": []}.
    """
    if not azure.connection.is_complete:
        return {"ok": False, "error": CONNECT_FIRST, "items": []}

    def load() -> JsonObject:
        query = (
            "SELECT [System.Id] FROM WorkItems WHERE "
            f"{wiql_project_filter(azure.connection.project)} AND "
            "[System.State] NOT IN ('Closed','Removed') "
            "ORDER BY [System.ChangedDate] DESC"
        )

        try:
            work_items = query_field_values(
                azure,
                query,
                "System.Id,System.Title,System.WorkItemType",
            )
        except DashboardError as error:
            return {"ok": False, "error": error.detail, "items": []}

        return {
            "ok": True,
            "items": [
                {
                    "id": work_item.get("id"),
                    "titulo": fields.get("System.Title") or "",
                    "tipo": fields.get("System.WorkItemType") or "",
                }
                for work_item in work_items
                for fields in (work_item.get("fields") or {},)
            ],
        }

    return cached_result(
        azure,
        "_wi_buscables",
        SEARCHABLE_CACHE_SECONDS,
        load,
    )


def search_work_items(azure: DailyAzure, query: object) -> JsonObject:
    """
    Busca work items por ID o titulo (maximo 8).

    Args:
        azure: Conexion del panel.
        query: Texto buscado.

    Returns:
        {"ok", "items"}.
    """
    result = load_searchable_work_items(azure)

    if not result.get("ok"):
        return result

    text = search_text(query)
    items: list[JsonObject] = result["items"]

    return {
        "ok": True,
        "items": [
            item
            for item in items
            if not text
            or text in str(item["id"])
            or text in str(item["titulo"]).lower()
        ][:SEARCH_LIMIT],
    }


def html_text(value: object) -> str:
    """
    Convierte saltos de linea a <br>, como htmlSeguro().

    Args:
        value: Texto recibido.

    Returns:
        El texto con <br>.
    """
    return str(value or "").replace("\n", "<br>")


def build_risk_operations(
    fields: Mapping[str, Any],
    project: str,
    reference: Callable[[str], str | None],
) -> list[JsonObject]:
    """
    Arma el JSON Patch del riesgo.

    Args:
        fields: Campos del formulario.
        project: Team Project (Area e Iteration por omision).
        reference: Llave logica -> Reference Name.

    Returns:
        Las operaciones add.
    """
    operations: list[JsonObject] = [
        {
            "op": "add",
            "path": "/fields/System.Title",
            "value": fields["titulo"],
        },
        {
            "op": "add",
            "path": "/fields/System.AreaPath",
            "value": fields.get("areaPath") or project,
        },
        {
            "op": "add",
            "path": "/fields/System.IterationPath",
            "value": fields.get("iterationPath") or project,
        },
    ]
    added: set[str] = set()

    def add(reference_name: str | None, value: object) -> None:
        if not reference_name or value is None or value == "":
            return

        if reference_name in added:
            return

        added.add(reference_name)
        operations.append(
            {"op": "add", "path": f"/fields/{reference_name}", "value": value},
        )

    add("System.Description", html_text(fields.get("descripcion")))
    add("System.AssignedTo", fields.get("responsable"))
    add(reference("severidad"), fields.get("nivel"))
    add(reference("prioridad"), fields.get("prioridad"))

    if reference("planMitigacion") and reference("planMitigacion") == reference(
        "triggers",
    ):
        combined = "<br><br>".join(
            text
            for text in (
                f"Plan de mitigación: {fields['planMitigacion']}"
                if fields.get("planMitigacion")
                else "",
                f"Triggers: {fields['triggers']}"
                if fields.get("triggers")
                else "",
            )
            if text
        )
        add(reference("planMitigacion"), html_text(combined))
    else:
        add(
            reference("planMitigacion"), html_text(fields.get("planMitigacion"))
        )
        add(reference("triggers"), html_text(fields.get("triggers")))

    add(reference("contingencyPlan"), html_text(fields.get("contingencyPlan")))
    # Probability lleva el mismo valor que Priority, como en el original.
    add(reference("probabilidad"), fields.get("prioridad"))

    for key in (
        "categoria",
        "fuenteRiesgo",
        "partesInteresadas",
        "estrategiaGestion",
        "fechaSeguimiento",
        "personaEscala",
        "escalate",
    ):
        add(reference(key), fields.get(key))

    return operations


def create_risk_work_item(azure: DailyAzure, form: object) -> JsonObject:
    """
    Crea el work item Risk en Azure DevOps.

    Args:
        azure: Conexion del panel.
        form: Campos del formulario.

    Returns:
        {"ok", "id", "url"} o {"ok": False, "error"}.
    """
    fields: dict[str, Any] = dict(form) if isinstance(form, dict) else {}
    title = str(fields.get("titulo") or "").strip()

    if not title:
        return {"ok": False, "error": "Falta el título del riesgo."}

    connection = azure.connection

    if not connection.is_complete:
        return {"ok": False, "error": CONNECT_FIRST}

    fields["titulo"] = title
    mapped = map_risk_fields(azure)
    mapping: dict[str, JsonObject | None] = (
        mapped["mapa"] if mapped.get("ok") else {}
    )

    def reference(key: str) -> str | None:
        field = mapping.get(key)
        return str(field.get("referenceName")) if field else None

    operations = build_risk_operations(fields, connection.project, reference)
    related_id = str(fields.get("relatedWorkItemId") or "").strip()

    if DIGITS_ONLY.fullmatch(related_id):
        operations.append(
            {
                "op": "add",
                "path": "/relations/-",
                "value": {
                    "rel": "System.LinkTypes.Related",
                    "url": f"{AZURE_BASE_URL}/"
                    f"{encode_url_part(connection.organization)}"
                    f"/_apis/wit/workItems/{related_id}",
                },
            },
        )

    try:
        created = azure.build_client().create_work_item(
            connection.project,
            RISK_TYPE,
            operations,
        )
    except AzureHttpError as error:
        if error.status_code in WRITE_DENIED_STATUSES:
            return {"ok": False, "error": WRITE_DENIED_MESSAGE}

        return {
            "ok": False,
            "error": f"Azure DevOps respondió {error.status_code}: "
            f"{error.body[:CREATE_ERROR_CHARS]}",
        }
    except DashboardError as error:
        return {"ok": False, "error": error.detail}

    clear_work_item_cache(azure)

    return {
        "ok": True,
        "id": created.get("id"),
        "url": work_item_url(connection, created.get("id")),
    }


def clear_work_item_cache(azure: DailyAzure) -> None:
    """
    Borra la cache de las tarjetas del proyecto activo.

    Args:
        azure: Conexion del panel.
    """
    prefix = azure.connection.cache_prefix

    for suffix in ("", "_tobe_cr_base", "_tipo_Risk", "_tipo_Opportunity"):
        azure.cache.delete(f"{prefix}{suffix}")

    clear_raid_cache(azure.cache)


def add_work_item_comment(
    azure: DailyAzure,
    work_item_id: object,
    comment: object,
    today: datetime,
) -> JsonObject:
    """
    Publica "dd/mm/aaaa - comentario" en la discusion del work item.

    Args:
        azure: Conexion del panel.
        work_item_id: ID del work item.
        comment: Comentario.
        today: Fecha local actual.

    Returns:
        {"ok", "textoPublicado"} o {"ok": False, "error"}.
    """
    comment_text = str(comment).strip() if comment else ""

    if not comment_text:
        return {"ok": False, "error": "Escribe un comentario antes de enviar."}

    connection = azure.connection

    if not connection.is_complete:
        return {"ok": False, "error": CONNECT_FIRST}

    text = f"{today.strftime('%d/%m/%Y')} - {comment_text}"

    try:
        azure.build_client().add_comment(
            connection.project,
            str(work_item_id),
            text,
        )
    except AzureHttpError as error:
        if error.status_code in WRITE_DENIED_STATUSES:
            return {"ok": False, "error": WRITE_DENIED_MESSAGE}

        return {
            "ok": False,
            "error": f"Azure DevOps respondió {error.status_code}: "
            f"{error.body[:ERROR_BODY_CHARS]}",
        }
    except DashboardError as error:
        return {"ok": False, "error": error.detail}

    return {"ok": True, "textoPublicado": text}
