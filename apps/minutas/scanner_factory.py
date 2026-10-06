"""Creacion del escaneo de minutas con la configuracion de Django."""

from django.conf import settings
from django.utils import timezone

from apps.dashboard.cache import clear_cached_dashboard
from apps.minutas.services.drive_folder import GoogleDriveDocumentSource
from apps.minutas.services.minute_scanner import ScanContext, scan_new_minutes
from core.sheets.client import build_drive_service
from core.sheets.factory import build_sheet_repository, get_credentials

"""BKD.060.008 - Escaneo con settings
Une la hoja de calculo, Drive y la carpeta configurada en .env.
"""


def run_minutes_scan() -> int:
    """
    Escanea la carpeta de minutas configurada en GOOGLE_MINUTES_FOLDER_ID.

    Returns:
        Cuantos documentos de hoy se procesaron.
    """
    repository = build_sheet_repository()
    context = ScanContext(
        reader=repository,
        writer=repository,
        source=GoogleDriveDocumentSource(
            build_drive_service(
                get_credentials(settings.GOOGLE_CREDENTIALS_FILE),
            ),
        ),
        now=timezone.localtime().replace(tzinfo=None),
    )
    processed = scan_new_minutes(context, settings.GOOGLE_MINUTES_FOLDER_ID)

    if processed:
        clear_cached_dashboard()

    return processed
