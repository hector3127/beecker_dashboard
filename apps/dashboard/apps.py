"""Configuracion de la app dashboard."""

from django.apps import AppConfig

"""BKD.010.022 - App dashboard
Registra la app y sus funciones RPC.
"""


class DashboardConfig(AppConfig):
    """Dashboard ejecutivo (ProyectosService.gs y Codigo.gs)."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.dashboard"

    def ready(self) -> None:
        """Registra las funciones RPC de la app al iniciar Django."""
        import apps.dashboard.rpc  # noqa: F401
