"""Configuracion de la app azure_devops."""

from django.apps import AppConfig

"""BKD.030.007 - App azure_devops
Registra la app y sus funciones RPC.
"""


class AzureDevopsConfig(AppConfig):
    """Integracion con Azure DevOps (ResumenAltoNivelService.gs)."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.azure_devops"

    def ready(self) -> None:
        """Registra las funciones RPC de la app al iniciar Django."""
        import apps.azure_devops.rpc  # noqa: F401
