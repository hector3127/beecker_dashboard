"""Hechos verificables del proyecto para anclar las respuestas de Claude."""

import re
import unicodedata
from collections.abc import Mapping, Sequence
from typing import Any

from core.utils.js_values import (
    js_json,
    js_len,
    js_number,
    js_object_keys,
    js_or,
    js_or_text,
    js_slice,
    js_str,
    js_truthy,
)

"""BKD.070.021 - Hechos de la IA IXS
Equivale a ixsIAHechos_() e ixsIAValidarAfirmaciones_(): convierte el
contexto del panel en hechos con identificador estable (PR-1, ET-3,
WI-123...) y descarta las afirmaciones del modelo que no citan un hecho
o que mencionan numeros que no aparecen en sus evidencias.
"""

JsonObject = dict[str, Any]

MAX_FACT_TEXT = 600
SHORT_TEXT = 160
MAX_CLAIM_TEXT = 700
NUMBER_TOLERANCE = 0.011
MIN_TERM_LENGTH = 5
MIN_ID_LENGTH = 3
MATCHED_ITEMS = 35
DATED_ITEMS = 20
DEFAULT_ITEMS = 55
MAX_ASSIGNEES = 30
MAX_EXTRA_RESOURCES = 30
MAX_HOUR_DAYS = 90
CLOSED_ITEM = re.compile(r"closed|done|resolved|complet|cerrad", re.IGNORECASE)
CITATION = re.compile(r"\[[A-Z0-9-]+\]")
NUMBER = re.compile(r"\d+(?:[.,]\d+)?", re.ASCII)
MISSING = object()


def fmt(value: object) -> str:
    """Texto como x == null || x === '' ? '' : String(x)."""
    return (
        ""
        if value is None or value is MISSING or value == ""
        else js_str(value)
    )


def short(value: object) -> str:
    """fmt(x) hasta 160 caracteres."""
    return js_slice(fmt(value), 0, SHORT_TEXT)


def prop(item: object, key: str) -> Any:
    """x.key (None si x no es objeto o no tiene la llave)."""
    return item.get(key) if isinstance(item, Mapping) else None


def concat(value: object) -> str:
    """Texto como en 'prefijo' + x (undefined/null se escriben)."""
    return "undefined" if value is MISSING else js_str(value)


def rows(value: object) -> list[Any]:
    """Array.isArray(x) ? x : []."""
    return value if isinstance(value, list) else []


def includes(container: object, text: str) -> bool:
    """x.indexOf(text) >= 0 para listas o textos."""
    if isinstance(container, list):
        return text in container

    return isinstance(container, str) and text in container


def search_terms(query: str) -> list[str]:
    """Palabras de 5 o mas letras o digitos de la pregunta."""
    terms: list[str] = []
    current: list[str] = []

    for character in query:
        if unicodedata.category(character).startswith("L") or (
            "0" <= character <= "9"
        ):
            current.append(character)
        else:
            terms.append("".join(current))
            current = []

    terms.append("".join(current))

    return [term for term in terms if len(term) >= MIN_TERM_LENGTH]


def build_facts(
    context: Mapping[str, Any], question: object
) -> list[JsonObject]:
    """
    Hechos del proyecto con identificador, fuente y texto (ixsIAHechos_).

    Args:
        context: Contexto que arma el panel (avance, etapas, Work Items,
            horas, recursos, planeacion, acciones, RAID, minutas...).
        question: Pregunta del usuario ("" para el analisis).

    Returns:
        Los hechos en el orden del original.
    """
    facts: list[JsonObject] = []

    def add(fact_id: object, source: str, text: object) -> None:
        clean = js_or_text(text).strip()

        if clean:
            facts.append(
                {
                    "id": js_str(fact_id),
                    "fuente": source,
                    "texto": js_slice(clean, 0, MAX_FACT_TEXT),
                },
            )

    add_summary_facts(context, add)
    sources = context.get("fuentesDisponibles")

    for index, stage in enumerate(rows(context.get("etapas"))):
        add(
            f"ET-{index + 1}",
            "planeación",
            f"{short(prop(stage, 'nombre'))}: inicio "
            f"{fmt(prop(stage, 'inicio'))}"
            f", fin {fmt(prop(stage, 'fin'))}, estado "
            f"{fmt(prop(stage, 'estado'))}.",
        )

    if includes(sources, "azure"):
        add(
            "AZ-RES",
            "Azure DevOps",
            f"Total Work Items {fmt(context.get('workItemsTotal'))}; "
            "sin seguimiento "
            f"{fmt(context.get('workItemsSinSeguimiento'))}; estados "
            f"{js_json(js_or(context.get('workItemsPorEstado'), {}))}; "
            f"iteraciones "
            f"{js_json(js_or(context.get('workItemsPorIteracion'), {}))}.",
        )
        assignees = js_or(context.get("workItemsPorAsignado"), {})
        names = js_object_keys(assignees) if isinstance(assignees, dict) else []

        for index, name in enumerate(names[:MAX_ASSIGNEES]):
            add(
                f"AZ-AS-{index + 1}",
                "Azure DevOps",
                f"{short(name)}: {fmt(assignees[name])} Work Items asignados.",
            )

    add_work_item_facts(context, question, add)

    if includes(sources, "clockify"):
        add(
            "CL-RES",
            "Clockify",
            "Horas registradas en el ID "
            f"{fmt(context.get('horasClockifyTotal'))} h; "
            f"{fmt(context.get('registrosClockifyTotal'))} registros.",
        )

    for index, day in enumerate(
        rows(context.get("horasPorFecha"))[-MAX_HOUR_DAYS:]
    ):
        add(
            f"CL-DAY-{index + 1}",
            "Clockify",
            f"{fmt(prop(day, 'fecha'))}: {fmt(prop(day, 'horas'))} horas "
            "registradas en el proyecto.",
        )

    add_resource_facts(context, add)
    add_planning_facts(context, add)

    previous = context.get("memoriaAnterior")

    if js_truthy(previous):
        analysis = js_or(prop(previous, "analisis"), {})
        add(
            "MEM-1",
            "Memoria",
            f"Corte previo del {fmt(prop(previous, 'fecha'))}: "
            f"{short(js_json(analysis))}",
        )

    return facts


def add_summary_facts(context: Mapping[str, Any], add: Any) -> None:
    """PR-1 (avance) y FIN-1 (cumplimiento financiero)."""
    progress = context.get("avance")
    parts = [
        f"Proyecto {fmt(context.get('proyecto', MISSING))} "
        f"{fmt(context.get('nombreProyecto', MISSING))}",
        f"fecha de corte {fmt(context.get('fechaCorte'))}"
        if js_or(context.get("fechaCorte"), None) is not None
        else "",
        f"avance {fmt(prop(progress, 'pct'))}%"
        if js_or(progress, None) is not None
        and prop(progress, "pct") is not None
        else "",
    ]
    add("PR-1", "dashboard", "; ".join(part for part in parts if part) + ".")
    kpis = context.get("kpis")
    compliance = prop(kpis, "pctCumplimientoFinanciero")

    if not js_truthy(kpis) or compliance is None:
        return

    budget = context.get("presupuesto")
    parts = [
        f"Cumplimiento financiero {fmt(compliance)}%",
        f"presupuesto {fmt(prop(budget, 'budget'))} horas"
        if js_or(budget, None) is not None
        and prop(budget, "budget") is not None
        else "",
        f"gasto {fmt(prop(budget, 'burn'))} horas"
        if js_truthy(budget) and prop(budget, "burn") is not None
        else "",
    ]
    add("FIN-1", "dashboard", "; ".join(part for part in parts if part) + ".")


def add_work_item_facts(
    context: Mapping[str, Any],
    question: object,
    add: Any,
) -> None:
    """WI-<id>: los mencionados en la pregunta o los abiertos/con fecha."""
    all_items = rows(context.get("workItems"))
    query = js_or_text(question).lower()
    terms = search_terms(query)

    def text_of(item: object, key: str) -> str:
        return js_or_text(prop(item, key)).lower()

    def matches(item: object) -> bool:
        if not query:
            return False

        id_text = js_or_text(prop(item, "id"))

        if len(id_text) >= MIN_ID_LENGTH and id_text in query:
            return True

        return any(
            term in text_of(item, "titulo") or term in text_of(item, "asignado")
            for term in terms
        )

    def has_date(item: object) -> bool:
        return js_truthy(prop(item, "fechaLimite"))

    matched = [item for item in all_items if matches(item)]

    if matched:
        selected = (
            matched[:MATCHED_ITEMS]
            + [item for item in all_items if has_date(item)][:DATED_ITEMS]
        )
    else:
        selected = [
            item
            for item in all_items
            if has_date(item)
            or not CLOSED_ITEM.search(js_or_text(prop(item, "estado")))
        ][:DEFAULT_ITEMS]

    seen: set[str] = set()

    for item in selected:
        raw_id = (
            item.get("id", MISSING) if isinstance(item, Mapping) else MISSING
        )
        key = concat(raw_id)

        if key in seen:
            continue

        seen.add(key)
        add(
            f"WI-{key}",
            "Azure DevOps",
            f"#{fmt(raw_id)} {short(prop(item, 'titulo'))}; estado "
            f"{fmt(prop(item, 'estado'))}; responsable "
            f"{short(prop(item, 'asignado'))}; etapa "
            f"{short(prop(item, 'iteracion'))}; fecha límite "
            f"{fmt(prop(item, 'fechaLimite'))}.",
        )


def lower_name(item: object) -> str:
    """String(x.nombre || '').toLowerCase()."""
    return js_or_text(prop(item, "nombre")).lower()


def add_resource_facts(context: Mapping[str, Any], add: Any) -> None:
    """REC-n (recursos con sus horas) y CL-n (horas sin recurso asignado)."""
    resources = rows(context.get("recursos"))
    hours = rows(context.get("horasPorRecurso"))

    for index, resource in enumerate(resources):
        name = fmt(prop(resource, "nombre"))
        logged = next(
            (item for item in hours if lower_name(item) == name.lower()),
            None,
        )
        state = "inactivo" if prop(resource, "activo") is False else "activo"
        add(
            f"REC-{index + 1}",
            "Recursos / Clockify",
            f"{short(name)}; rol {short(prop(resource, 'rol'))}; {state}; "
            f"estimadas {fmt(prop(resource, 'horasEstimadas'))} h; "
            f"registradas {fmt(prop(logged, 'horas'))} h.",
        )

    resource_names = {lower_name(resource) for resource in resources}
    extra = [item for item in hours if lower_name(item) not in resource_names]

    for index, item in enumerate(extra[:MAX_EXTRA_RESOURCES]):
        add(
            f"CL-{index + 1}",
            "Clockify",
            f"{short(prop(item, 'nombre'))}: {fmt(prop(item, 'horas'))} h "
            "registradas, sin asignación del recurso en la tabla.",
        )


def first_of(item: object, *keys: str) -> Any:
    """x.a || x.b || x.c (el ultimo aunque sea falso)."""
    value: Any = None

    for key in keys:
        value = prop(item, key)

        if js_truthy(value):
            return value

    return value


def add_planning_facts(context: Mapping[str, Any], add: Any) -> None:
    """Vacaciones, compromisos, acciones, RAID y minutas."""
    for index, item in enumerate(rows(context.get("vacaciones"))):
        add(
            f"VAC-{index + 1}",
            "Planeación",
            "Vacaciones "
            f"{short(first_of(item, 'recurso', 'nombre', 'persona'))}"
            f": {fmt(first_of(item, 'inicio', 'fechaInicio'))} a "
            f"{fmt(first_of(item, 'fin', 'fechaFin'))}; estado "
            f"{fmt(prop(item, 'estado'))}.",
        )

    for index, item in enumerate(rows(context.get("compromisos"))):
        add(
            f"COM-{index + 1}",
            "Planeación",
            "Compromiso "
            f"{short(first_of(item, 'actividad', 'nombre', 'titulo'))}: "
            f"responsable {short(prop(item, 'responsable'))}; fecha "
            f"{fmt(first_of(item, 'fechaLimite', 'fecha'))}; estado "
            f"{fmt(prop(item, 'estado'))}.",
        )

    for index, item in enumerate(rows(context.get("acciones"))):
        add(
            f"ACC-{js_str(js_or(prop(item, 'uid'), index + 1))}",
            "Acciones",
            f"Acción {short(prop(item, 'accion'))}: "
            f"{short(prop(item, 'responsable'))}; fecha límite "
            f"{fmt(prop(item, 'fechaLimite'))}; estado "
            f"{fmt(prop(item, 'estado'))}.",
        )

    for index, item in enumerate(rows(context.get("raid"))):
        add(
            f"RAID-{js_str(js_or(prop(item, 'id'), index + 1))}",
            "RAID",
            f"{short(prop(item, 'tipo'))} #{fmt(prop(item, 'id'))}: "
            f"{short(prop(item, 'titulo'))}; estado "
            f"{fmt(prop(item, 'estado'))}.",
        )

    for index, item in enumerate(rows(context.get("minutas"))):
        add(
            f"MIN-{index + 1}",
            "Minutas",
            f"{short(prop(item, 'tema'))} ({fmt(prop(item, 'fecha'))}): "
            f"{short(prop(item, 'contenido'))}",
        )


def validate_claims(
    items: object,
    facts: Sequence[Mapping[str, Any]],
    limit: int,
) -> list[JsonObject]:
    """
    Afirmaciones que citan hechos validos (ixsIAValidarAfirmaciones_).

    Se descartan las que no citan un hecho existente, las vacias o muy
    largas y las que escriben un numero que no aparece en sus evidencias.

    Args:
        items: Lista del modelo (textos u objetos con evidencias).
        facts: Hechos enviados al modelo.
        limit: Maximo de elementos a revisar.

    Returns:
        Las afirmaciones validas con evidencias y fuente.
    """
    by_id = {str(fact["id"]): fact for fact in facts}
    valid: list[JsonObject] = []

    for item in (items if isinstance(items, list) else [])[: limit or 5]:
        claim = {"texto": item} if isinstance(item, str) else item

        if not isinstance(claim, dict):
            continue

        evidence = claim.get("evidencias")
        refs = (
            [js_str(ref) for ref in evidence if js_str(ref) in by_id]
            if isinstance(evidence, list)
            else []
        )

        if not refs:
            continue

        text = " ".join(
            js_str(value)
            for value in (
                claim.get("texto"),
                claim.get("titulo"),
                claim.get("detalle"),
            )
            if js_truthy(value)
        )

        if not text or js_len(text) > MAX_CLAIM_TEXT:
            continue

        numbers = NUMBER.findall(CITATION.sub("", text))
        source = " ".join(js_str(by_id[ref]["texto"]) for ref in refs)
        available = [
            js_number(value.replace(",", ".", 1))
            for value in NUMBER.findall(source)
        ]

        if any(
            not any(
                abs(candidate - js_number(number.replace(",", ".", 1)))
                < NUMBER_TOLERANCE
                for candidate in available
            )
            for number in numbers
        ):
            continue

        sources = list(
            dict.fromkeys(str(by_id[ref]["fuente"]) for ref in refs),
        )
        valid.append(
            {**claim, "evidencias": refs, "fuente": " / ".join(sources)},
        )

    return valid
