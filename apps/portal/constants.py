"""Constantes de las vistas nuevas del portal."""

from typing import Final

from apps.dashboard.constants import (
    HEALTH_AT_RISK,
    HEALTH_CRITICAL,
    HEALTH_ON_TIME,
)

"""BKD.120.002 - Constantes del portal
Colores, etiquetas y claves de cache de las pantallas Ejecutiva,
Operativa y Comercial.
"""

PORTFOLIO_CACHE_KEY: Final[str] = "portal:portfolio:v1"
PORTFOLIO_CACHE_SECONDS: Final[int] = 300

NO_DELIVERY_MANAGER: Final[str] = "Sin Delivery Manager"

# Colores del diseno: en tiempo, en riesgo y critico.
COLOR_ON_TIME: Final[str] = "#1FA866"
COLOR_AT_RISK: Final[str] = "#F5B31C"
COLOR_CRITICAL: Final[str] = "#F0455E"
COLOR_DONUT_CRITICAL: Final[str] = "#F0489E"

HEALTH_LABELS: Final[dict[str, str]] = {
    HEALTH_ON_TIME: "En tiempo",
    HEALTH_AT_RISK: "En riesgo",
    HEALTH_CRITICAL: "Crítico",
}

DONUT_RADIUS: Final[int] = 64
DONUT_SIZE: Final[int] = 176

# Maximo de proyectos que muestra "Requieren decision".
DECISION_LIMIT: Final[int] = 5

# Dias de retraso que se consideran un problema de plazo.
DECISION_DELAY_DAYS: Final[int] = 1

# Estado de un proyecto en las tablas: codigo de clase CSS y color.
STATUS_ON_TIME: Final[str] = "g"
STATUS_AT_RISK: Final[str] = "a"
STATUS_CRITICAL: Final[str] = "r"
STATUS_PAUSED: Final[str] = "x"

SHARE_COLORS: Final[dict[str, str]] = {
    STATUS_ON_TIME: "#1B9A55",
    STATUS_AT_RISK: "#E88F0C",
    STATUS_CRITICAL: "#D6304B",
}

NO_RISK_LABEL: Final[str] = "—"
