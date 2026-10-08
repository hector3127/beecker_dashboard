"""Constantes de la integracion con Gmail."""

from typing import Final

"""BKD.110.002 - Constantes de Gmail
Direcciones de Google, permisos solicitados y limites de los adjuntos.
"""

AUTH_URL: Final[str] = "https://accounts.google.com/o/oauth2/v2/auth"

CODE_EXCHANGE_URL: Final[str] = "https://oauth2.googleapis.com/token"

USERINFO_URL: Final[str] = "https://openidconnect.googleapis.com/v1/userinfo"

GMAIL_API_URL: Final[str] = "https://gmail.googleapis.com/gmail/v1/users/me"

GMAIL_WEB_URL: Final[str] = "https://mail.google.com/mail/u/0/"

# Leer hilos para sacar los destinatarios y crear borradores o enviar.
OAUTH_SCOPES: Final[tuple[str, ...]] = (
    "openid",
    "email",
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.compose",
)

HTTP_TIMEOUT_SECONDS: Final[int] = 30

# Texto que llevan los asuntos de los hilos de cada proyecto.
THREAD_SUBJECT_TERM: Final[str] = "Inicio de"

MAX_THREADS: Final[int] = 40

MAX_MATCHING_THREADS: Final[int] = 10

THREAD_WORKERS: Final[int] = 8

SESSION_CREDENTIALS_KEY: Final[str] = "gmail_credentials"

SESSION_STATE_KEY: Final[str] = "gmail_oauth_state"

# Margen para no usar un acceso a punto de vencer.
EXPIRY_MARGIN_SECONDS: Final[int] = 60

DELIVERY_DRAFT: Final[str] = "draft"

DELIVERY_SEND: Final[str] = "send"

STAGES: Final[tuple[str, ...]] = ("Discovery", "Development", "Deployment")

ALLOWED_EXTENSIONS: Final[tuple[str, ...]] = (
    ".pdf",
    ".png",
    ".jpg",
    ".jpeg",
    ".xlsx",
    ".docx",
)

MAX_FILE_BYTES: Final[int] = 10 * 1024 * 1024

# Gmail rechaza mensajes de mas de 25 MB; el margen cubre la codificacion.
MAX_TOTAL_BYTES: Final[int] = 18 * 1024 * 1024

MAX_FILES: Final[int] = 10

MAX_REASON_LENGTH: Final[int] = 500
