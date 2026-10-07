"""Constantes de GSE."""

import re
from typing import Final

"""BKD.100.003 - Constantes de GSE
Hojas, encabezados y reglas tomadas de GSEService.gs.
"""

SHEET_ROSTER: Final[str] = "Bandas/rol"
BASE_SHEET_PREFIX: Final[str] = "08.Base Clockify "
CONTROL_SHEET: Final[str] = "GSE_Base_Control"

# Encabezados con los que se crea la hoja de la base.
BASE_HEADER_TITLES: Final[tuple[str, ...]] = (
    "Project",
    "User",
    "Start Date",
    "Duration (decimal)",
    "Task",
    "Tags",
    "Billable",
    "ID Registro",
    "ID Clockify",
    "Workspace",
    "Conexión GSE",
    "Actualizado",
)
# Encabezados normalizados de la base compartida (12 columnas).
BASE_COLUMNS: Final[int] = 12
BASE_REQUIRED_HEADERS: Final[tuple[str, ...]] = (
    "project",
    "user",
    "start date",
    "duration decimal",
    "task",
    "tags",
    "billable",
    "id registro",
    "id clockify",
    "workspace",
    "conexion gse",
    "actualizado",
)
BATCH_REQUIRED_HEADERS: Final[tuple[str, ...]] = (
    "project",
    "user",
    "start date",
    "duration decimal",
    "task",
    "id registro",
    "id clockify",
)

CONTROL_HEADERS: Final[tuple[str, ...]] = (
    "Clave",
    "Mes",
    "IDs JSON",
    "Actualizado",
    "Registros",
)

CATALOG_SHEET_KEYS: Final[frozenset[str]] = frozenset(
    {"catalagoproyectos", "catalogoproyectos"},
)
# Columnas del catalogo: B operacion, C tipo, D ID_Proyecto, I servicio.
CATALOG_OPERATION_COLUMN: Final[int] = 1
CATALOG_TYPE_COLUMN: Final[int] = 2
CATALOG_ID_COLUMN: Final[int] = 3
CATALOG_SERVICE_COLUMN: Final[int] = 8
ROLE_COLUMN: Final[int] = 2

HEADER_SEARCH_ROWS: Final[int] = 20
BATCH_SIZE: Final[int] = 5000
MIN_YEAR: Final[int] = 2000
MAX_YEAR: Final[int] = 2100

NO_SUFFIX_VARIANT: Final[re.Pattern[str]] = re.compile(
    r"_(?:S\d+|CR\d*)\Z",
    re.IGNORECASE | re.ASCII,
)
SUFFIX_IN_TEXT: Final[re.Pattern[str]] = re.compile(
    r"_(S\d+|CR\d*)(?![a-z0-9])",
    re.IGNORECASE | re.ASCII,
)
OWN_SUFFIX: Final[re.Pattern[str]] = re.compile(
    r"_(S\d+|CR\d*)\Z",
    re.IGNORECASE | re.ASCII,
)
LEGACY_DATE: Final[re.Pattern[str]] = re.compile(
    r"^(\d{2})[/-](\d{2})[/-](\d{4})$",
    re.ASCII,
)
ISO_DATE: Final[re.Pattern[str]] = re.compile(
    r"^(\d{4}-\d{2}-\d{2})",
    re.ASCII,
)
LOCAL_DATE: Final[re.Pattern[str]] = re.compile(
    r"^(\d{1,2})[/-](\d{1,2})[/-](\d{4})",
    re.ASCII,
)
TAG_SEPARATOR: Final[re.Pattern[str]] = re.compile(r"[,;]")
BILLABLE_TEXT: Final[re.Pattern[str]] = re.compile(
    r"^(yes|true|si|sí)$",
    re.IGNORECASE,
)

UNCLASSIFIED: Final[str] = "Sin clasificación"
NOT_AVAILABLE: Final[str] = "NA"
NO_PROJECT: Final[str] = "Sin proyecto"
NO_NAME: Final[str] = "Sin nombre"
BILLABLE: Final[str] = "Facturable"
NON_BILLABLE: Final[str] = "No Facturables"
KPI_CATEGORIES: Final[tuple[str, ...]] = (
    "Facturable",
    "Optimización",
    "Agentes Autónomos",
    "Continuos Improvement",
    "Laboratorio",
)

# (etiqueta, alias) que se buscan en proyecto, task o tags.
TEXT_RULES: Final[tuple[tuple[str, tuple[str, ...]], ...]] = (
    ("Inversión Operaciones", ("inversion operaciones", "inv operativa")),
    ("Inversión Comercial", ("inversion comercial", "inv comercial")),
    ("Vacaciones", ("vacaciones",)),
    ("Sin Asignación", ("sin asignacion",)),
    ("Pre-Venta", ("pre venta", "pre ventas")),
    ("Internos", ("interno", "internos")),
)
# (etiqueta, alias) que se comparan con la operacion del catalogo.
OPERATION_RULES: Final[tuple[tuple[str, tuple[str, ...]], ...]] = (
    ("Optimización", ("optimizacion",)),
    (
        "Agentes Autónomos",
        ("agentes autonomos", "agente autonomo"),
    ),
    (
        "Continuos Improvement",
        ("continuos improvement", "continuous improvement"),
    ),
    ("Laboratorio", ("laboratorio",)),
)

BATCH_VERSION: Final[str] = "GSE-BASE-BANDAS-2026-10-06"
BATCH_ERROR_VERSION: Final[str] = "GSE-BASE-BLOQUES-2026-10-06"
RESULT_CACHE_SCOPE: Final[str] = "gse-result-v2-servicio"
RESULT_CACHE_SECONDS: Final[int] = 21_600
RESULT_MAX_CHARS: Final[int] = 5_000_000
