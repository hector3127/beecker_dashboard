"""Constantes de Minutas IA."""

from typing import Final

"""BKD.060.003 - Constantes de Minutas
Valores tomados de MinutasService.gs y MinutasViewService.gs.
"""

GOOGLE_DOC_MIME: Final[str] = "application/vnd.google-apps.document"
FOLDER_MIME: Final[str] = "application/vnd.google-apps.folder"
TEXT_MIME: Final[str] = "text/plain"

MINUTE_ID_PREFIX: Final[str] = "MIN-"
MINUTE_ID_DOC_CHARS: Final[int] = 8
MIN_TEXT_LENGTH: Final[int] = 50
MINUTE_SOURCE: Final[str] = "Google Meet / Gemini"
DEFAULT_SENTIMENT: Final[str] = "Neutral"
RULE_RISK_ORIGIN: Final[str] = "Regla-Minuta"
MINUTE_RISK_ORIGINS: Final[frozenset[str]] = frozenset(
    {"Regla-Minuta", "IA-Minuta"},
)
ALL_PROJECTS: Final[str] = "Todos los proyectos"
AGREEMENT_SEPARATOR: Final[str] = " | "
SCAN_PROCESS: Final[str] = "escanearMinutasNuevas"
PROCESS_PROCESS: Final[str] = "procesarMinuta"
