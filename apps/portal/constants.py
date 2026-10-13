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

# EVA 1: en rojo si faltan menos de estos dias para renovar.
RENEWAL_ALERT_DAYS: Final[int] = 30
PROGRESS_ALERT_PERCENT: Final[int] = 100
EVA1_SERVICES: Final[tuple[str, ...]] = ("AER", "T&M")

# EVA 2: como se escribe cada servicio y color de cada etapa.
EVA2_SERVICE_LABELS: Final[dict[str, str]] = {
    "IXB": "IXB",
    "RAAS": "RaaS",
    "RAAS+": "RaaS+",
    "SAAS": "SaaS",
    "IXB Y RAAS": "IXB y RaaS",
    "POC": "POC",
}
EVA2_SERVICE_ORDER: Final[tuple[str, ...]] = ("IXB", "RAAS")
EVA2_STATUS_COLUMNS: Final[tuple[tuple[str, str], ...]] = (
    ("sus", "Sus"),
    ("dis", "Dis"),
    ("dev", "Dev"),
    ("dep", "Dep"),
)
EVA2_STATUS_WORDS: Final[tuple[tuple[str, str], ...]] = (
    ("suspend", "sus"),
    ("deployment", "dep"),
    ("development", "dev"),
    ("discovery", "dis"),
)
EVA2_STAGE_KEYS: Final[tuple[str, ...]] = (
    "discovery",
    "development",
    "deployment",
    "general",
)
EVA2_CACHE_KEY: Final[str] = "portal:eva2:v1"
EVA2_CACHE_SECONDS: Final[int] = 600

# Capacidad instalada
CAPACITY_CACHE_PREFIX: Final[str] = "portal:capacity:v1:"
CAPACITY_CACHE_SECONDS: Final[int] = 300
DEFAULT_WORKDAY_HOURS: Final[float] = 8.0
MAX_WORKDAY_HOURS: Final[float] = 24.0
WEEKDAYS_PER_WEEK: Final[int] = 5

# Pantalla de Proyecto
PROJECT_CACHE_PREFIX: Final[str] = "portal:project:v1:"
PROJECT_CACHE_SECONDS: Final[int] = 600
PROJECT_BAR_SCALE_PERCENT: Final[int] = 150

# Ranking de cuentas y KPIs de Delivery Managers
TOP_ACCOUNTS: Final[int] = 3
KPI_LOW_PERCENT: Final[int] = 40
KPI_HIGH_PERCENT: Final[int] = 80

# Facturabilidad
FIXED_SERVICE: Final[str] = "AER"
VARIABLE_SERVICES: Final[tuple[str, ...]] = ("TYM", "IXB", "SAAS", "RAAS")
SERVICE_LABELS: Final[dict[str, str]] = {
    "AER": "AER",
    "TYM": "TYM",
    "IXB": "IXB",
    "SAAS": "SaaS",
    "RAAS": "RaaS",
}
FACTURABILITY_CACHE_PREFIX: Final[str] = "portal:facturability:v1:"
FACTURABILITY_CACHE_SECONDS: Final[int] = 600
BILLABLE_HIGH_PERCENT: Final[int] = 80
BILLABLE_LOW_PERCENT: Final[int] = 50
