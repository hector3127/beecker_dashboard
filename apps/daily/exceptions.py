"""Excepciones del panel Daily."""

from core.exceptions import DashboardError

"""BKD.070.003 - Errores del Daily
Respuestas de Azure DevOps con su codigo HTTP, para armar los mismos
mensajes que el original.
"""


class AzureHttpError(DashboardError):
    """Azure DevOps respondio con un codigo de error."""

    code = "ERR_AZURE_HTTP"
    public_message = "Azure DevOps respondio con un error."
    http_status = 502
    expose_detail = True

    def __init__(self, status_code: int, body: str) -> None:
        super().__init__(f"Azure DevOps respondió {status_code}.")

        self.status_code = status_code
        self.body = body


class AzureConnectionError(DashboardError):
    """No hubo conexion con Azure DevOps."""

    code = "ERR_AZURE_CONNECTION"
    public_message = "No hubo conexion con Azure DevOps."
    http_status = 502
    expose_detail = True


class DailyRequestError(DashboardError):
    """Datos invalidos o registro inexistente en el panel Daily."""

    code = "ERR_DAILY"
    public_message = "No se pudo completar la accion del panel Daily."
    http_status = 400
    expose_detail = True
