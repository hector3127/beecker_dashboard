"""Configuracion de la app gse."""

from django.apps import AppConfig

"""BKD.100.001 - App gse
Registra la app y sus funciones RPC.
"""


class GseConfig(AppConfig):
    """Horas de Clockify por area (ROL de Bandas/rol)."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.gse"

    def ready(self) -> None:
        """Registra las funciones RPC de la app al iniciar Django."""
        import apps.gse.rpc  # noqa: F401
