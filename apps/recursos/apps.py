"""Configuracion de la app recursos."""

from django.apps import AppConfig

"""BKD.090.001 - App recursos
Registra la app de la vista de Recursos y sus funciones RPC.
"""


class RecursosConfig(AppConfig):
    """Vista de Recursos (RecursosDetalleService.gs)."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.recursos"

    def ready(self) -> None:
        """Registra las funciones RPC de la app al iniciar Django."""
        import apps.recursos.rpc  # noqa: F401
