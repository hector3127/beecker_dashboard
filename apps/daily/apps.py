"""Configuracion de la app daily."""

from django.apps import AppConfig

"""BKD.070.001 - App daily
Registra la app y sus funciones RPC.
"""


class DailyConfig(AppConfig):
    """Panel Daily: Azure DevOps, pendientes y ajustes."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.daily"

    def ready(self) -> None:
        """Registra las funciones RPC de la app al iniciar Django."""
        import apps.daily.ai_rpc  # noqa: F401
        import apps.daily.ixs_rpc  # noqa: F401
        import apps.daily.rpc  # noqa: F401
