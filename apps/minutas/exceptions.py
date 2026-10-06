"""Excepciones de Minutas IA."""

from core.exceptions import DashboardError

"""BKD.060.002 - Errores de Minutas
Errores controlados al leer la carpeta de Drive.
"""


class DriveRequestError(DashboardError):
    """Indica que Google Drive rechazo la consulta."""

    code = "ERR_DRIVE"
    public_message = "No se pudo leer la carpeta de minutas en Drive."
    http_status = 502
    expose_detail = True
