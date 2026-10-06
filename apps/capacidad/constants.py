"""Constantes de Capacidad instalada."""

import re
from typing import Final

"""BKD.050.003 - Constantes de Capacidad instalada
Hojas, encabezados y reglas tomadas de CapacidadInstaladaService.gs.
"""

SHEET_BANDS: Final[str] = "Bandas/rol"
SHEET_RESOURCES: Final[str] = "Recursos"
SHEET_MPB: Final[str] = "MPB"

# ciTabla_() busca los encabezados en las primeras 20 filas.
HEADER_SEARCH_ROWS: Final[int] = 20

MONTH_PATTERN: Final[re.Pattern[str]] = re.compile(
    r"\d{4}-(0[1-9]|1[0-2])",
)

MONTH_NAMES: Final[tuple[str, ...]] = (
    "enero",
    "febrero",
    "marzo",
    "abril",
    "mayo",
    "junio",
    "julio",
    "agosto",
    "septiembre",
    "octubre",
    "noviembre",
    "diciembre",
)

# Servicios de MPB (normalizados y sin espacios) que toman sus fechas
# de esa hoja.
MPB_SERVICES: Final[frozenset[str]] = frozenset(
    {"aer", "tym", "tm", "timeandmaterial", "timeandmaterials"},
)

# Concepto normalizado -> (cargable, facturable, afecta capacidad). Las
# reglas marcadas con None dependen de si el recurso es becario.
CONCEPT_RULES: Final[dict[str, tuple[bool | None, bool | None, bool]]] = {
    "interno": (None, False, True),
    "pre ventas": (True, None, True),
    "proyecto": (True, True, True),
    "voluntary training": (False, False, True),
    "onboarding training": (False, False, False),
    "mandatory training": (False, False, False),
    "sin asignacion": (False, False, True),
    "incapacidad": (False, False, False),
    "laboratorio beecker": (True, False, True),
    "investigacion y desarrollo": (True, True, True),
    "vacaciones": (False, False, False),
    "administrativas": (True, False, True),
    "dia feriado": (False, False, False),
    "inversion": (True, False, True),
}

TRAINEE_PATTERN: Final[re.Pattern[str]] = re.compile(r"becario|residente")

INACTIVE_STATES: Final[frozenset[str]] = frozenset({"inactivo", "baja"})

DEFAULT_RESOURCE_TYPE: Final[str] = "Empleado"
UNASSIGNED_CONCEPT: Final[str] = "Sin Asignación"
PROJECT_CONCEPT: Final[str] = "Proyecto"
NO_BAND: Final[str] = "NA"

SOURCES: Final[tuple[str, ...]] = ("Recursos", "Bandas/rol", "Azure DevOps")

SPRINT_SUFFIX: Final[re.Pattern[str]] = re.compile(
    r"_(S\d+|CR\d*)\Z",
    re.IGNORECASE,
)
MPB_ONLY_PREFIX: Final[re.Pattern[str]] = re.compile(
    r"^(AER|TYM|T&M)[._]",
    re.IGNORECASE,
)
