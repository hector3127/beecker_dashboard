"""Constantes del panel Daily."""

from typing import Final

"""BKD.070.002 - Constantes del Daily
Valores tomados de DailyPanelService.gs.
"""

AZURE_BASE_URL: Final[str] = "https://dev.azure.com"
API_VERSION: Final[str] = "7.1"
COMMENTS_API_VERSION: Final[str] = "7.1-preview.3"
REQUEST_TIMEOUT_SECONDS: Final[int] = 60

# AZ_CACHE_SEGUNDOS del original.
WORK_ITEMS_CACHE_SECONDS: Final[int] = 300
MAX_WORK_ITEMS: Final[int] = 200
ERROR_BODY_CHARS: Final[int] = 300

CLOSED_STATES_WIQL: Final[str] = "('Closed','Resolved','Removed','Done')"
RISK_TYPE: Final[str] = "Risk"
OPPORTUNITY_TYPE: Final[str] = "Opportunity"
UNASSIGNED: Final[str] = "Sin asignar"
DEFAULT_STALE_DAYS: Final[int] = 7
ALL_PROJECTS: Final[str] = "Todos los proyectos"

PENDING_ITEM_FIELDS: Final[tuple[str, ...]] = (
    "System.Id",
    "System.Title",
    "System.WorkItemType",
    "System.State",
    "System.AssignedTo",
    "System.CreatedDate",
    "System.ChangedDate",
    "Microsoft.VSTS.Scheduling.DueDate",
    "System.Tags",
)
TYPED_ITEM_FIELDS: Final[tuple[str, ...]] = (
    "System.Id",
    "System.Title",
    "System.State",
    "System.AssignedTo",
    "System.ChangedDate",
    "Microsoft.VSTS.Common.Severity",
    "Microsoft.VSTS.Common.Risk",
    "Microsoft.VSTS.Common.Priority",
)

SHEET_DAILY_PENDING: Final[str] = "Pendientes_Daily"
DAILY_PENDING_HEADERS: Final[tuple[str, ...]] = (
    "ID",
    "Descripcion",
    "Proyecto",
    "Responsable",
    "Prioridad",
    "Estado",
    "Fecha_Creacion",
    "Fecha_Limite",
)
SHEET_UAT_ADJUSTMENTS: Final[str] = "Ajustes_UAT"
SHEET_WARRANTY_ADJUSTMENTS: Final[str] = "Ajustes_Garantia"
ADJUSTMENT_HEADERS: Final[tuple[str, ...]] = (
    "ID",
    "Ajuste",
    "Proyecto",
    "Dev_Pct",
    "QA_Listo",
    "Fecha_Creacion",
)
SHEET_WORK_ITEM_PROGRESS: Final[str] = "WorkItems_Avance"
WORK_ITEM_PROGRESS_HEADERS: Final[tuple[str, ...]] = (
    "ID_WorkItem",
    "Proyecto",
    "Dev_Pct",
    "QA_Listo",
    "TTProd_Listo",
    "Fecha_Limite_Dev",
    "Demo",
)
# Campo del frontend -> columna (base 1) de WorkItems_Avance.
PROGRESS_COLUMN_BY_FIELD: Final[dict[str, int]] = {
    "devConstruido": 3,
    "qa": 4,
    "ttProd": 5,
    "fechaLimiteDev": 6,
    "demo": 7,
}
