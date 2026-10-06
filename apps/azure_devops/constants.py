"""Constantes de la integracion con Azure DevOps."""

from typing import Final

"""BKD.030.001 - Constantes de Azure DevOps
URLs, limites y reglas de riesgos de ResumenAltoNivelService.gs.
"""

AZURE_DEVOPS_BASE_URL: Final[str] = "https://dev.azure.com"
API_VERSION: Final[str] = "7.1"
REQUEST_TIMEOUT_SECONDS: Final[int] = 60
SUCCESS_STATUS_LIMIT: Final[int] = 300

PROJECTS_PAGE_SIZE: Final[int] = 500
MAX_WORK_ITEMS: Final[int] = 1000
WORK_ITEMS_BATCH_SIZE: Final[int] = 180

WORK_ITEM_FIELDS: Final[tuple[str, ...]] = (
    "System.Id",
    "System.State",
    "System.IterationPath",
    "System.WorkItemType",
    "System.Title",
    "System.ChangedDate",
    "System.AssignedTo",
    "Microsoft.VSTS.Common.Severity",
)

ITERATIONS_DEPTH: Final[int] = 15
ITERATIONS_CACHE_SECONDS: Final[int] = 900

# Los Team Projects casi no cambian: una hora.
PROJECTS_CACHE_SECONDS: Final[int] = 3600
# El original guardaba 5 minutos; con 15 el comando warm_cache alcanza a
# mantener la cache llena entre ejecuciones.
WORK_ITEMS_CACHE_SECONDS: Final[int] = 900

# Consultas a Azure DevOps al mismo tiempo durante la precarga.
MAX_PARALLEL_REQUESTS: Final[int] = 4

RISK_WORK_ITEM_TYPE: Final[str] = "RISK"
OPEN_RISK_STATES: Final[frozenset[str]] = frozenset({"ACTIVE", "PROPOSED"})
SEVERITY_FIELD: Final[str] = "Microsoft.VSTS.Common.Severity"

SEVERITY_HIGH: Final[str] = "Alto"
SEVERITY_MEDIUM: Final[str] = "Medio"
SEVERITY_LOW: Final[str] = "Bajo"
