"""Configuracion de la app aer."""

from django.apps import AppConfig

"""BKD.080.001 - App aer
Registra la app del dashboard AER / T&M y sus funciones RPC.
"""


class AerConfig(AppConfig):
    """Dashboard de proyectos AER / T&M (AERTYMProyectoService.gs)."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.aer"

    def ready(self) -> None:
        """Registra las funciones RPC de la app al iniciar Django."""
        import apps.aer.ai_rpc  # noqa: F401
        import apps.aer.rpc  # noqa: F401
