"""Creacion del repositorio de Sheets a partir de settings."""

from functools import lru_cache

from django.conf import settings
from google.oauth2.service_account import Credentials

from core.exceptions import ConfigurationError
from core.sheets.client import (
    build_sheets_service,
    load_service_account_credentials,
)
from core.sheets.read_cache import SheetReadCache
from core.sheets.repository import GoogleSheetRepository

"""BKD.004.007 - Fabrica del repositorio
Lee la configuracion de Django y entrega un repositorio por peticion,
cada uno con su propio cliente HTTP.
"""


@lru_cache(maxsize=1)
def get_credentials(credentials_file: str) -> Credentials:
    """
    Lee una sola vez por proceso las credenciales de la cuenta de servicio.

    Solo se comparten las credenciales. El cliente HTTP no se comparte:
    runserver atiende cada peticion en un hilo distinto y una conexion
    compartida entre hilos se corrompe (ssl WRONG_VERSION_NUMBER).

    Args:
        credentials_file: Ruta al JSON de la cuenta de servicio.

    Returns:
        Las credenciales de Google.
    """
    return load_service_account_credentials(credentials_file)


def build_sheet_repository() -> GoogleSheetRepository:
    """
    Crea un repositorio nuevo con su propia cache de lecturas.

    Returns:
        El repositorio listo para usarse en una peticion.

    Raises:
        ConfigurationError: Cuando falta GOOGLE_SPREADSHEET_ID.
    """
    spreadsheet_id = settings.GOOGLE_SPREADSHEET_ID

    if not spreadsheet_id:
        raise ConfigurationError(
            "Define GOOGLE_SPREADSHEET_ID en el archivo .env.",
        )

    return GoogleSheetRepository(
        build_sheets_service(get_credentials(settings.GOOGLE_CREDENTIALS_FILE)),
        spreadsheet_id,
        SheetReadCache(spreadsheet_id, settings.SHEETS_READ_CACHE_SECONDS),
    )
