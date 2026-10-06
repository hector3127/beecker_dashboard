"""Constantes del resumen ejecutivo."""

from typing import Final

"""BKD.040.001 - Constantes del resumen ejecutivo
Columnas de la hoja MPB y reglas tomadas de obtenerResumenAERTYMMPB().
"""

SHEET_MPB: Final[str] = "MPB"

# La ultima columna necesaria de MPB es BL (64 columnas).
MPB_COLUMN_COUNT: Final[int] = 64
HEADER_SEARCH_ROWS: Final[int] = 12

# Encabezado -> columna de respaldo (base 0) si el encabezado no existe.
MPB_COLUMNS: Final[dict[str, tuple[str, int]]] = {
    "client": ("CLIENTE", 1),
    "project_id": ("ID", 2),
    "name": ("NOMBRE", 4),
    "service": ("SERVICE", 5),
    "start": ("INICIO", 6),
    "end": ("FIN", 8),
    "status": ("ESTATUS", 19),
    "manager": ("Delivery Manager", 20),
    "fte": ("FTE", 22),
    "budget": ("HORAS", 32),
    "burn": ("Horas consumidas", 63),
}

# El rol DEV esta en X; el resto de roles va de Y a AE.
ROLE_COLUMNS: Final[dict[str, int]] = {
    "DEV": 23,
    "ARQ": 24,
    "IA": 25,
    "SM": 26,
    "BA": 27,
    "TT": 28,
    "CR": 29,
    "DM": 30,
}

UNASSIGNED_MANAGER: Final[str] = "Sin asignar"
SERVICE_AER: Final[str] = "AER"
SERVICE_TYM: Final[str] = "T&M"

SUMMARY_CACHE_SECONDS: Final[int] = 90
CONSUMPTION_BATCH_SIZE: Final[int] = 2
