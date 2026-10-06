"""Normalizacion de textos, numeros y reglas de conceptos."""

import math
import re
from typing import Any

from apps.capacidad.constants import CONCEPT_RULES, TRAINEE_PATTERN
from core.utils.cell_types import CellValue
from core.utils.text import strip_accents, to_text

"""BKD.050.004 - Textos y reglas de Capacidad instalada
Equivale a ciNorm_(), ciNumero_() y ciRegla_().
"""

NON_ALPHANUMERIC = re.compile(r"[^a-z0-9]+")

# Formatos que acepta Number() de JavaScript para un texto decimal.
JS_DECIMAL = re.compile(r"[+-]?(\d+\.?\d*|\.\d+)([eE][+-]?\d+)?")
JS_RADIX_PREFIXES = {"0x": 16, "0o": 8, "0b": 2}

JsonObject = dict[str, Any]


def normalize_capacity_text(value: CellValue) -> str:
    """
    Normaliza un texto como ciNorm_().

    Quita acentos, pasa a minusculas y cambia todo lo que no sea letra o
    numero por un espacio.

    Args:
        value: Valor de la celda.

    Returns:
        El texto normalizado.
    """
    lowered_text = strip_accents(to_text(value)).lower()

    return NON_ALPHANUMERIC.sub(" ", lowered_text).strip()


def parse_capacity_number(value: CellValue) -> float | None:
    """
    Convierte una celda a horas como ciNumero_().

    Args:
        value: Valor de la celda.

    Returns:
        El numero si es finito y no negativo; si no, None.
    """
    if value is None or value == "" or isinstance(value, bool):
        return None

    if isinstance(value, int | float):
        number = float(value)
    else:
        number = parse_js_number(to_text(value).strip().replace(",", ".", 1))

    if math.isnan(number) or math.isinf(number) or number < 0:
        return None

    # -0 se escribe como 0 en el JSON, igual que en JavaScript.
    return number + 0.0


def parse_js_number(text: str) -> float:
    """
    Convierte un texto a numero como Number() de JavaScript.

    Args:
        text: Texto a convertir.

    Returns:
        El numero, o NaN cuando el texto no es numerico.
    """
    clean_text = text.strip()

    if not clean_text:
        return 0.0

    if JS_DECIMAL.fullmatch(clean_text):
        return float(clean_text)

    radix = JS_RADIX_PREFIXES.get(clean_text[:2].lower())

    if radix is not None:
        try:
            return float(int(clean_text[2:], radix))
        except ValueError:
            return math.nan

    if clean_text.lstrip("+-") == "Infinity":
        return -math.inf if clean_text.startswith("-") else math.inf

    return math.nan


def find_concept_rule(concept: str, resource_type: str) -> JsonObject | None:
    """
    Obtiene la regla de cargabilidad de un concepto, como ciRegla_().

    Args:
        concept: Concepto de la asignacion.
        resource_type: Tipo de recurso (Empleado, Becario, Residente).

    Returns:
        La regla con cargabilidad, facturable, capacidad y afecta; None
        si el concepto no tiene regla.
    """
    rule = CONCEPT_RULES.get(normalize_capacity_text(concept))

    if rule is None:
        return None

    is_trainee = bool(
        TRAINEE_PATTERN.search(normalize_capacity_text(resource_type)),
    )
    is_chargeable, is_billable, affects_capacity = (
        (not is_trainee) if flag is None else flag for flag in rule
    )

    return {
        "cargabilidad": "Cargable" if is_chargeable else "No Cargable",
        "facturable": "Facturable" if is_billable else "No Facturable",
        "capacidad": (
            "Afecta Capacidad" if affects_capacity else "No Afecta Capacidad"
        ),
        "afecta": affects_capacity,
    }
