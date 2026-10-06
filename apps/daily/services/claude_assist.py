"""Configuracion de Claude y sugerencias de RAID (Risk, Issue, Opportunity)."""

import json
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, Protocol

from core.exceptions import DashboardError
from core.integrations.claude_client import ClaudeClient, text_blocks
from core.utils.js_values import js_or, js_or_text, js_slice, js_str

"""BKD.070.020 - Asistente de Claude
Equivale a guardarApiKeyClaude(), obtenerConfigClaude(),
guardarPromptPersonalizadoClaude(), generarSugerenciaRiesgoConClaude(),
ixsRaidGuardarPrompt(), ixsRaidObtenerPrompt() e ixsRaidSugerirClaude().
La API key vive en ANTHROPIC_API_KEY del .env; los prompts personalizados
se guardan en la cache del servidor sin expiracion.
"""

JsonObject = dict[str, Any]

PROMPTS_DIR = Path(__file__).resolve().parent.parent / "prompts"
STANDARD_PROMPTS = {
    "Issue": (PROMPTS_DIR / "issue.md").read_text("utf-8"),
    "Opportunity": (PROMPTS_DIR / "opportunity.md").read_text("utf-8"),
}
RISK_PROMPT_KEY = "daily:claude:prompt_personalizado"
RAID_PROMPT_KEYS = {
    "Issue": "daily:claude:prompt_issue",
    "Opportunity": "daily:claude:prompt_opportunity",
}
ENV_ONLY_MESSAGE = (
    "La API key de Claude se configura en el archivo .env (ANTHROPIC_API_KEY)."
)
MAX_RISK_PROMPT = 2200
MAX_RAID_PROMPT_BYTES = 8500
MIN_RAID_DESCRIPTION = 12
MAX_RAID_INPUT = 3500
FOLLOW_UP_DAYS = 7
LEVELS = ("Alto", "Medio", "Bajo")
PRIORITIES = ("1", "2", "3", "4")
RAID_SCHEMAS = {
    "Issue": '{"titulo":"","descripcion":"","planMitigacion":""}',
    "Opportunity": (
        '{"titulo":"","descripcion":"","planAprovechamiento":"",'
        '"senalAlerta":"","planAccion":""}'
    ),
}
RAID_MAX_TOKENS = {"Issue": 1900, "Opportunity": 1350}

RISK_PROMPT = (
    "Eres un asistente de gestión de riesgos de proyectos de software "
    "(metodología Scrum, formato de Azure DevOps). A partir de esta "
    "descripción libre de un riesgo, genera un JSON con EXACTAMENTE estas "
    "claves (todas en español, nunca dejes ninguna vacía si es razonable "
    'inferirla; si no aplica, usa cadena vacía ""):\n'
    '- "titulo": máximo 8 palabras, claro y accionable\n'
    '- "descripcion": la descripción original redactada de forma clara y '
    "profesional, máximo 3 líneas\n"
    '- "nivel": solo uno de "Alto", "Medio", "Bajo"\n'
    '- "prioridad": número del 1 (más urgente) al 4 (menos urgente) — este '
    'mismo valor se usará también como "Probability"\n'
    '- "planMitigacion": acciones concretas para reducir la probabilidad o '
    "el impacto de este riesgo\n"
    '- "triggers": señales o eventos que indicarían que el riesgo se está '
    "materializando\n"
    '- "contingencyPlan": qué hacer SI el riesgo ya ocurrió (plan B)\n'
    '- "categoria": categoría corta del riesgo (ej. "Técnico", "Alcance", '
    '"Recursos", "Terceros", "Cronograma")\n'
    '- "fuenteRiesgo": de dónde viene el riesgo (ej. "Cliente", "Equipo '
    'interno", "Proveedor externo")\n'
    '- "partesInteresadas": quién se ve afectado si el riesgo ocurre\n'
    '- "estrategiaGestion": una de "Evitar", "Mitigar", "Transferir", '
    '"Aceptar"\n'
    'IMPORTANTE DE FORMATO: en "planMitigacion", "triggers" y '
    '"contingencyPlan", si mencionas varios puntos, sepáralos con un salto '
    "de línea real (\\n) entre cada uno, en formato de lista numerada, ej: "
    '"1. Primer punto.\\n2. Segundo punto.\\n3. Tercer punto." — nunca los '
    "pongas todos seguidos en un solo párrafo.\n"
)
RISK_PROMPT_EXTRA = (
    "\nInstrucciones adicionales del usuario (respétalas siempre que no "
    "contradigan el formato JSON pedido):\n"
)
RISK_PROMPT_END = (
    "Responde ÚNICAMENTE el JSON, sin texto adicional ni markdown.\n\n"
    "Descripción del riesgo: "
)
RAID_OUTPUT_INSTRUCTIONS = (
    "\n\n---\nINSTRUCCIONES DE SALIDA PARA EL FORMULARIO DE AZURE: "
    "Respeta la estructura, tono y contenido de los apartados anteriores, "
    "pero responde EXCLUSIVAMENTE con un objeto JSON válido (sin markdown "
    "externo ni explicación). Claves exactas: {schema}. Cada clave "
    "representa el apartado de nombre equivalente. Usa saltos de línea y "
    "viñetas dentro de las cadenas para las listas. No añadas campos ni "
    "inventes información; cuando falte un dato deja el apartado sin "
    "afirmaciones específicas. Para Issue, planMitigacion debe tener 5 o 6 "
    "acciones concretas, cada una en su propia linea iniciando con una "
    "viñeta. No generes primer seguimiento: el Issue aun no se ha creado y "
    "no puede tener seguimiento previo. Para Opportunity, descripcion "
    "explica el beneficio; planAprovechamiento, senalAlerta y planAccion son "
    "apartados independientes con listas breves. El título no debe copiar "
    "literalmente la entrada.\n\nInformación REAL de entrada (no uses como "
    "hechos el ejemplo del prompt):\n"
)


class PromptStore(Protocol):
    """Cache donde se guardan los prompts (la de Django cumple)."""

    def get(self, key: str) -> Any:
        """Valor guardado o None."""
        ...

    def set(self, key: str, value: Any, timeout: int | None) -> None:
        """Guarda el valor (timeout None: sin expiracion)."""
        ...

    def delete(self, key: str) -> Any:
        """Borra el valor."""
        ...


@dataclass(frozen=True, slots=True)
class ClaudeSettings:
    """API key, modelo, prompts guardados y cliente de Claude."""

    api_key: str
    model: str
    store: PromptStore
    build_client: Callable[[], ClaudeClient]
    now: datetime


class SuggestionError(DashboardError):
    """Error controlado de una sugerencia."""

    code = "ERR_CLAUDE_SUGGESTION"
    expose_detail = True


def save_api_key(api_key: object) -> JsonObject:
    """
    guardarApiKeyClaude(): la key solo se configura en el .env.

    Args:
        api_key: Key escrita en el panel (no se guarda).

    Returns:
        El error de key vacia del original, o el aviso de .env.
    """
    if not js_or_text(api_key).strip():
        return {"ok": False, "error": "Falta la API key."}

    return {"ok": False, "error": ENV_ONLY_MESSAGE}


def save_custom_prompt(settings: ClaudeSettings, text: object) -> JsonObject:
    """guardarPromptPersonalizadoClaude(): instrucciones extra del Risk."""
    settings.store.set(RISK_PROMPT_KEY, js_or_text(text).strip(), None)

    return {"ok": True}


def read_config(settings: ClaudeSettings) -> JsonObject:
    """
    obtenerConfigClaude(): si hay key, sus ultimos 4 caracteres y el prompt.

    Returns:
        {"ok", "configurado", "sufijo", "promptPersonalizado"}.
    """
    key = settings.api_key

    return {
        "ok": True,
        "configurado": bool(key),
        "sufijo": key[-4:] if key else "",
        "promptPersonalizado": settings.store.get(RISK_PROMPT_KEY) or "",
    }


def ask_claude(
    settings: ClaudeSettings,
    prompt: str,
    max_tokens: int,
) -> tuple[int, str]:
    """Envia el prompt y regresa el codigo HTTP y el cuerpo."""
    response = settings.build_client().create_message(
        {
            "model": settings.model,
            "max_tokens": max_tokens,
            "messages": [{"role": "user", "content": prompt}],
        },
    )

    return response.status_code, response.body


def suggest_risk(settings: ClaudeSettings, description: object) -> JsonObject:
    """
    Sugiere los campos de un Risk (generarSugerenciaRiesgoConClaude).

    Nunca crea nada en Azure: el usuario edita la sugerencia antes.

    Args:
        settings: Configuracion de Claude.
        description: Descripcion libre del riesgo.

    Returns:
        Los campos sugeridos o {"ok": False, "error"}.
    """
    try:
        return build_risk_suggestion(settings, js_or_text(description).strip())
    except (DashboardError, ValueError) as error:
        detail = (
            error.detail if isinstance(error, DashboardError) else str(error)
        )
        return {
            "ok": False,
            "error": f"No se pudo generar la sugerencia: {detail}",
        }


def build_risk_suggestion(
    settings: ClaudeSettings, description: str
) -> JsonObject:
    """Cuerpo de suggest_risk; los errores se convierten afuera."""
    if not description:
        raise SuggestionError("Escribe una descripción del riesgo primero.")

    if not settings.api_key:
        return {
            "ok": False,
            "error": "Configura tu API key de Claude primero.",
            "sinApiKey": True,
        }

    custom = settings.store.get(RISK_PROMPT_KEY) or ""
    prompt = (
        RISK_PROMPT
        + (f"{RISK_PROMPT_EXTRA}{custom}\n" if custom else "")
        + RISK_PROMPT_END
        + description
    )
    status, body = ask_claude(settings, prompt, 1500)

    if status == 401:
        return {"ok": False, "error": "API key de Claude inválida."}

    if status >= 300:
        return {
            "ok": False,
            "error": f"Claude respondió {status}: {js_slice(body, 0, 300)}",
        }

    data = json.loads(body)
    blocks = text_blocks(data if isinstance(data, dict) else {})
    text = blocks[0] if blocks else ""

    if not text:
        return {
            "ok": False,
            "error": "Claude no devolvió texto. Respuesta cruda del servidor: "
            + js_slice(body, 0, 400),
        }

    start, end = text.find("{"), text.rfind("}")

    if start == -1 or end == -1 or end < start:
        return {
            "ok": False,
            "error": "Claude no devolvió un JSON reconocible. Respuesta "
            f'recibida: "{js_slice(text, 0, 150)}..."',
        }

    try:
        suggestion = json.loads(text[start : end + 1])
    except ValueError:
        return {
            "ok": False,
            "error": "La respuesta de Claude llegó incompleta (probablemente "
            "se cortó por el límite de tokens). Intenta de nuevo.",
        }

    if not isinstance(suggestion, dict):
        suggestion = {}

    level = suggestion.get("nivel")
    priority = js_str(suggestion.get("prioridad"))
    follow_up = (settings.now + timedelta(days=FOLLOW_UP_DAYS)).astimezone(UTC)

    return {
        "ok": True,
        "titulo": js_or(suggestion.get("titulo"), ""),
        "descripcion": js_or(suggestion.get("descripcion"), description),
        "nivel": level if level in LEVELS else "Medio",
        "prioridad": priority if priority in PRIORITIES else "2",
        "planMitigacion": js_or(suggestion.get("planMitigacion"), ""),
        "triggers": js_or(suggestion.get("triggers"), ""),
        "contingencyPlan": js_or(suggestion.get("contingencyPlan"), ""),
        "categoria": js_or(suggestion.get("categoria"), ""),
        "fuenteRiesgo": js_or(suggestion.get("fuenteRiesgo"), ""),
        "partesInteresadas": js_or(suggestion.get("partesInteresadas"), ""),
        "estrategiaGestion": js_or(
            suggestion.get("estrategiaGestion"), "Mitigar"
        ),
        "escalate": "No",
        "fechaSeguimiento": follow_up.strftime("%Y-%m-%d"),
    }


def save_raid_prompt(
    settings: ClaudeSettings,
    raid_type: object,
    text: object,
) -> JsonObject:
    """
    Guarda el prompt de un tipo RAID (ixsRaidGuardarPrompt).

    Risk usa el prompt personalizado de siempre (hasta 2,200 caracteres);
    Issue y Opportunity guardan el prompt completo, y vacio o igual al
    estandar vuelve al estandar.

    Returns:
        {"ok"} para Risk; {"ok", "prompt", "predeterminado"} para los demas.
    """
    if raid_type == "Risk":
        return save_custom_prompt(
            settings,
            js_slice(js_or_text(text), 0, MAX_RISK_PROMPT),
        )

    key = (
        RAID_PROMPT_KEYS.get(raid_type) if isinstance(raid_type, str) else None
    )

    if not key:
        return {"ok": False, "error": "Tipo no permitido"}

    standard = STANDARD_PROMPTS[str(raid_type)]
    new_prompt = js_or_text(text).strip()

    if not new_prompt or new_prompt == standard:
        settings.store.delete(key)
    elif len(new_prompt.encode("utf-8")) > MAX_RAID_PROMPT_BYTES:
        return {
            "ok": False,
            "error": "El prompt supera el límite de 8.5 KB permitido para la "
            "personalización.",
        }
    else:
        settings.store.set(key, new_prompt, None)

    saved = settings.store.get(key)

    return {
        "ok": True,
        "prompt": saved or standard,
        "predeterminado": not saved,
    }


def read_raid_prompt(settings: ClaudeSettings, raid_type: object) -> JsonObject:
    """
    Prompt vigente de un tipo RAID (ixsRaidObtenerPrompt).

    Returns:
        {"ok", "configurado", "prompt", ...}.
    """
    if raid_type == "Risk":
        config = read_config(settings)
        return {
            "ok": True,
            "configurado": config["configurado"],
            "prompt": config["promptPersonalizado"],
            "error": "",
        }

    key = (
        RAID_PROMPT_KEYS.get(raid_type) if isinstance(raid_type, str) else None
    )

    if not key:
        return {"ok": False, "error": "Tipo no permitido"}

    custom = settings.store.get(key) or ""

    return {
        "ok": True,
        "configurado": bool(settings.api_key),
        "prompt": custom or STANDARD_PROMPTS[str(raid_type)],
        "predeterminado": not custom,
    }


def suggest_raid(
    settings: ClaudeSettings,
    raid_type: object,
    description_value: object,
) -> JsonObject:
    """
    Sugerencia para el formulario RAID (ixsRaidSugerirClaude).

    Args:
        settings: Configuracion de Claude.
        raid_type: Risk, Issue u Opportunity.
        description_value: Texto de entrada (minimo 12 caracteres).

    Returns:
        Risk: la sugerencia de suggest_risk. Issue/Opportunity:
        {"ok", "sugerencia", "modelo"}.
    """
    description = js_or_text(description_value).strip()

    if len(description) < MIN_RAID_DESCRIPTION:
        return {
            "ok": False,
            "error": "Escribe una descripción de al menos 12 caracteres.",
        }

    if raid_type == "Risk":
        return suggest_risk(settings, description)

    if raid_type not in ("Issue", "Opportunity"):
        return {"ok": False, "error": "Tipo no permitido"}

    raid_type_text = str(raid_type)
    config = read_raid_prompt(settings, raid_type_text)

    if not settings.api_key:
        return {
            "ok": False,
            "error": "Configura la API key de Claude en Configuración.",
            "sinApiKey": True,
        }

    prompt = (
        config["prompt"]
        + RAID_OUTPUT_INSTRUCTIONS.format(schema=RAID_SCHEMAS[raid_type_text])
        + js_slice(description, 0, MAX_RAID_INPUT)
    )

    try:
        status, body = ask_claude(
            settings,
            prompt,
            RAID_MAX_TOKENS[raid_type_text],
        )

        if status >= 300:
            return {
                "ok": False,
                "error": f"Claude HTTP {status}: {js_slice(body, 0, 240)}",
            }

        data = json.loads(body)
        text = "\n".join(text_blocks(data if isinstance(data, dict) else {}))
        start, end = text.find("{"), text.rfind("}")

        if start < 0 or end <= start:
            return {
                "ok": False,
                "error": f"Claude no devolvió JSON para {raid_type_text}.",
            }

        suggestion = json.loads(text[start : end + 1])
    except DashboardError as error:
        return {"ok": False, "error": error.detail}
    except ValueError as error:
        return {"ok": False, "error": str(error)}

    return {"ok": True, "sugerencia": suggestion, "modelo": settings.model}
