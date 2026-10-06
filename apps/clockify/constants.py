"""Constantes de la integracion con Clockify."""

from typing import Final

"""BKD.020.002 - Constantes de Clockify
URLs, limites y tiempos de cache tomados de ClockifyService.gs y
RecursosDetalleService.gs.
"""

CLOCKIFY_BASE_URL: Final[str] = "https://api.clockify.me/api/v1"
CLOCKIFY_REPORTS_URL: Final[str] = "https://reports.api.clockify.me/v1"

REQUEST_TIMEOUT_SECONDS: Final[int] = 60
PROJECTS_PAGE_SIZE: Final[int] = 200
PROJECTS_MAX_PAGES: Final[int] = 100
REPORT_PAGE_SIZE: Final[int] = 200
REPORT_BLOCK_DAYS: Final[int] = 31
REPORT_MAX_REQUESTS: Final[int] = 200
REPORT_MAX_ATTEMPTS: Final[int] = 3
REPORT_RETRY_WAIT_SECONDS: Final[float] = 2.5
REPORT_PAUSE_SECONDS: Final[float] = 0.25

# Reportes de Clockify que se descargan al mismo tiempo. Un valor mayor
# provoca respuestas 429 (demasiadas peticiones).
MAX_PARALLEL_REPORTS: Final[int] = 3

RETRY_STATUS_TOO_MANY_REQUESTS: Final[int] = 429
SERVER_ERROR_STATUS: Final[int] = 500
SUCCESS_STATUS_LIMIT: Final[int] = 300
FORBIDDEN_STATUS: Final[int] = 403
UNAUTHORIZED_STATUS: Final[int] = 401

REPORT_TIMEZONE: Final[str] = "America/Mexico_City"

# Tiempos de cache en segundos.
PROJECTS_CACHE_SECONDS: Final[int] = 3600
TASKS_CACHE_SECONDS: Final[int] = 3600
TASKS_PAGE_SIZE: Final[int] = 200
TASKS_MAX_PAGES: Final[int] = 100
SINGLE_RETRY_WAIT_SECONDS: Final[float] = 1.5
PROJECT_REPORT_CACHE_SECONDS: Final[int] = 21600
EMPTY_REPORT_CACHE_SECONDS: Final[int] = 1800
ALL_ENTRIES_CACHE_SECONDS: Final[int] = 900
BACKUP_CACHE_SECONDS: Final[int] = 21600

# Prefijos de proyectos que toman su rango de la hoja MPB.
MPB_PROJECT_PREFIXES: Final[tuple[str, ...]] = ("TYM.", "AER.")
MPB_SERVICES: Final[frozenset[str]] = frozenset({"AER", "TYM", "T&M"})

SHEET_MPB: Final[str] = "MPB"
SHEET_PROJECT_LINKS: Final[str] = "Clockify_Vinculos"

HEADER_SEARCH_ROWS: Final[int] = 12
HISTORY_COLUMN_COUNT: Final[int] = 9
MPB_COLUMN_COUNT: Final[int] = 9
