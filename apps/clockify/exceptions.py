"""Excepciones de la integracion con Clockify."""

from core.exceptions import DashboardError, TimeEntrySourceError

"""BKD.020.001 - Errores de Clockify
Errores controlados de la API de Clockify y de la extraccion de horas.
"""


class ClockifyConfigurationError(DashboardError):
    """Indica que falta la API key o el workspace de Clockify."""

    code = "ERR_CLOCKIFY_CONFIG"
    public_message = "Falta configurar Clockify."
    http_status = 409
    expose_detail = True


class ClockifyRequestError(TimeEntrySourceError):
    """Indica que Clockify rechazo una peticion o no respondio."""

    code = "ERR_CLOCKIFY_REQUEST"
    public_message = "Clockify no respondio correctamente."

    def __init__(self, detail: str = "", status_code: int = 0) -> None:
        super().__init__(detail)

        self.status_code = status_code


class ClockifyReportForbiddenError(ClockifyRequestError):
    """Indica que la API key no tiene acceso al reporte detallado."""

    code = "ERR_CLOCKIFY_FORBIDDEN"
    public_message = "Clockify no permite leer el reporte de este proyecto."


class ClockifyProjectError(TimeEntrySourceError):
    """Indica que no se pudieron obtener las horas de un proyecto."""

    code = "ERR_CLOCKIFY_PROJECT"
    public_message = "No se completo la extraccion de horas de Clockify."
