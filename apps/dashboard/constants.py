"""Constantes de negocio del dashboard ejecutivo."""

from typing import Final

"""BKD.010.001 - Constantes del dashboard
Umbrales, etiquetas y colores tomados de ProyectosService.gs,
RecursosDetalleService.gs y Config.gs.
"""

ALL_PROJECTS_LABEL: Final[str] = "Todos los proyectos"
ALL_CLIENTS_LABEL: Final[str] = "Todos los clientes"

# Categorias de estado que usa el dashboard.
CATEGORY_ACTIVE: Final[str] = "Activo"
CATEGORY_PAUSED: Final[str] = "En Pausa"
CATEGORY_PLANNING: Final[str] = "Planificación"
CATEGORY_CLOSED: Final[str] = "Cerrado"

# Estado de la hoja Proyectos -> categoria del dashboard.
STATUS_CATEGORY_BY_STATUS: Final[dict[str, str]] = {
    "discovery": CATEGORY_PLANNING,
    "development": CATEGORY_ACTIVE,
    "deployment": CATEGORY_ACTIVE,
    "suspendido": CATEGORY_PAUSED,
    "cancelado": CATEGORY_CLOSED,
}

# Niveles de riesgo e impacto.
RISK_HIGH: Final[str] = "Alto"
RISK_MEDIUM: Final[str] = "Medio"
RISK_LOW: Final[str] = "Bajo"
RISK_STATUS_OPEN: Final[str] = "Abierto"

IMPACT_ORDER: Final[dict[str, int]] = {
    RISK_HIGH: 3,
    RISK_MEDIUM: 2,
    RISK_LOW: 1,
}

# Salud por proyecto.
HEALTH_ON_TIME: Final[str] = "A tiempo"
HEALTH_AT_RISK: Final[str] = "En Riesgo"
HEALTH_CRITICAL: Final[str] = "Crítica"

# Salud general del portafolio.
PORTFOLIO_HEALTH_GOOD: Final[str] = "Buena"
PORTFOLIO_HEALTH_FAIR: Final[str] = "Regular"
PORTFOLIO_HEALTH_CRITICAL: Final[str] = "Crítica"
PORTFOLIO_CRITICAL_RATIO: Final[float] = 0.4
PORTFOLIO_FAIR_RATIO: Final[float] = 0.2

TREND_UP: Final[str] = "up"
TREND_DOWN: Final[str] = "down"

# Dias de retraso a partir de los cuales el proyecto es critico.
CRITICAL_DELAY_DAYS: Final[int] = 10

# Umbrales de "foco rojo" (RecursosDetalleService.gs).
LONG_ENTRY_THRESHOLD_HOURS: Final[float] = 4
EXCESSIVE_DAY_THRESHOLD_HOURS: Final[float] = 10

WEEK_DAYS: Final[int] = 7

# Ventana para elegir el snapshot "vs semana anterior".
SNAPSHOT_MIN_AGE_DAYS: Final[float] = 5
SNAPSHOT_MAX_AGE_DAYS: Final[float] = 10
SNAPSHOT_TARGET_AGE_DAYS: Final[float] = 7

KPI_HISTORY_HEADERS: Final[tuple[str, ...]] = (
    "Fecha",
    "ProyectosActivos",
    "AvancePromedio",
    "HorasSemana",
    "RiesgosAltos",
    "FocoRojoSemana",
    "MargenPromedio",
)

SPRINT_STATUS_IN_PROGRESS: Final[str] = "En curso"

TOP_PROGRESS_LIMIT: Final[int] = 6
TOP_RISKS_LIMIT: Final[int] = 15

MAX_PROGRESS_PERCENT: Final[int] = 100

# Paleta corporativa de Config.gs.
COLOR_GREEN: Final[str] = "#2E7D32"
COLOR_YELLOW: Final[str] = "#F2A900"
COLOR_BLUE: Final[str] = "#5B8DEF"
COLOR_GRAY: Final[str] = "#6B6B6F"

ALERT_ERROR: Final[str] = "error"
ALERT_WARNING: Final[str] = "warning"
