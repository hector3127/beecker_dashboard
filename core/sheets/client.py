"""Construccion del cliente autenticado de la API de Google Sheets."""

import logging
from pathlib import Path
from typing import Any, Final

from google.auth.exceptions import GoogleAuthError
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

from core.exceptions import SheetAuthenticationError

"""BKD.004.004 - Cliente de Google Sheets
Autentica con la cuenta de servicio y construye el cliente de la API.
Sustituye el acceso implicito de SpreadsheetApp en Apps Script.
"""

logger = logging.getLogger(__name__)

# Sheets para leer y escribir; Drive (solo lectura) para las minutas.
GOOGLE_SCOPES: Final[list[str]] = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.readonly",
]


def load_service_account_credentials(credentials_file: str) -> Credentials:
    """
    Lee las credenciales de la cuenta de servicio.

    Args:
        credentials_file: Ruta al JSON de la cuenta de servicio.

    Returns:
        Las credenciales con el alcance de Google Sheets y Drive.

    Raises:
        SheetAuthenticationError: Cuando falta el archivo o las
            credenciales son invalidas.
    """
    credentials_path = Path(credentials_file)

    if not credentials_path.exists():
        raise SheetAuthenticationError(
            f"No se encontro el archivo de credenciales {credentials_path}.",
        )

    try:
        # La libreria de Google no tiene tipos para este constructor.
        return Credentials.from_service_account_file(  # type: ignore[no-any-return,no-untyped-call]
            str(credentials_path),
            scopes=GOOGLE_SCOPES,
        )
    except (GoogleAuthError, ValueError) as error:
        logger.exception("Las credenciales de Google no son validas.")

        raise SheetAuthenticationError(
            "El archivo de credenciales no es una cuenta de servicio valida.",
        ) from error


def build_drive_service(credentials: Credentials) -> Any:
    """
    Construye un cliente de Google Drive con su propia conexion HTTP.

    Args:
        credentials: Credenciales de la cuenta de servicio.

    Returns:
        El recurso de la API de Drive v3.
    """
    return build(
        "drive",
        "v3",
        credentials=credentials,
        cache_discovery=False,
    )


def build_sheets_service(credentials: Credentials) -> Any:
    """
    Construye un cliente de Google Sheets con su propia conexion HTTP.

    La conexion (httplib2) no admite varios hilos a la vez, por eso cada
    peticion debe usar un cliente propio.

    Args:
        credentials: Credenciales de la cuenta de servicio.

    Returns:
        El recurso de la API listo para leer y escribir.
    """
    return build(
        "sheets",
        "v4",
        credentials=credentials,
        cache_discovery=False,
    )
