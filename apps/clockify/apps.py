"""Configuracion de la app clockify."""

from django.apps import AppConfig

"""BKD.020.010 - App clockify
Registra la app y sus funciones RPC.
"""


class ClockifyConfig(AppConfig):
    """Integracion con Clockify (ClockifyService.gs)."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.clockify"

    def ready(self) -> None:
        """Registra las funciones RPC de la app al iniciar Django."""
        import apps.clockify.project_rpc  # noqa: F401
        import apps.clockify.rpc  # noqa: F401
        import apps.clockify.validation_rpc  # noqa: F401
