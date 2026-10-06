"""Etiqueta de severidad de los riesgos de Azure DevOps."""

import re

from apps.azure_devops.constants import (
    SEVERITY_HIGH,
    SEVERITY_LOW,
    SEVERITY_MEDIUM,
)
from apps.azure_devops.services.project_resolver import normalize_azure_name

"""BKD.030.005 - Severidad de riesgos
Equivale a _altoNivelEtiquetaSeveridadRiesgo(): 1 o 2 (Critical/High) es
Alto, 4 (Low) es Bajo y lo demas es Medio.
"""

HIGH_WORDS = ("CRITICAL", "CRITICA", "CRITICO", "HIGH", "ALTA", "ALTO")
LOW_WORDS = ("LOW", "BAJA", "BAJO")

HIGH_NUMBER_PATTERN = re.compile(r"^[12](?:\D|$)")
LOW_NUMBER_PATTERN = re.compile(r"^4(?:\D|$)")

SEVERITY_ORDER = {
    SEVERITY_HIGH: 3,
    SEVERITY_MEDIUM: 2,
    SEVERITY_LOW: 1,
}


def label_risk_severity(raw_severity: object) -> str:
    """
    Convierte el campo Severity de Azure a Alto, Medio o Bajo.

    Args:
        raw_severity: Valor crudo, por ejemplo "2 - High".

    Returns:
        La etiqueta que muestra el dashboard; Medio si viene vacio.
    """
    normalized = normalize_azure_name(str(raw_severity or ""))

    if not normalized:
        return SEVERITY_MEDIUM

    if any(word in normalized for word in HIGH_WORDS) or (
        HIGH_NUMBER_PATTERN.match(normalized)
    ):
        return SEVERITY_HIGH

    if any(word in normalized for word in LOW_WORDS) or (
        LOW_NUMBER_PATTERN.match(normalized)
    ):
        return SEVERITY_LOW

    return SEVERITY_MEDIUM


def severity_order(label: str) -> int:
    """
    Da el orden de una etiqueta: Alto 3, Medio 2, Bajo 1.

    Args:
        label: Etiqueta de severidad.

    Returns:
        El valor de orden, o 0 si no se reconoce.
    """
    return SEVERITY_ORDER.get(label, 0)
