"""Excepciones de la integracion con Azure DevOps."""

from core.exceptions import DashboardError

"""BKD.030.002 - Errores de Azure DevOps
Errores controlados de configuracion y de la API de Azure DevOps.
"""


class AzureDevOpsConfigurationError(DashboardError):
    """Indica que falta la organizacion o el PAT de Azure DevOps."""

    code = "ERR_AZURE_CONFIG"
    public_message = "Falta configurar Azure DevOps."
    http_status = 409
    expose_detail = True


class AzureDevOpsRequestError(DashboardError):
    """Indica que Azure DevOps rechazo una peticion o no respondio."""

    code = "ERR_AZURE_REQUEST"
    public_message = "Azure DevOps no respondio correctamente."
    http_status = 502
    expose_detail = True
