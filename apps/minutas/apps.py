"""Configuracion de la app minutas."""

from django.apps import AppConfig

"""BKD.060.001 - App minutas
Registra la app y sus funciones RPC.
"""


class MinutasConfig(AppConfig):
    """Minutas de Google Meet procesadas por reglas."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.minutas"

    def ready(self) -> None:
        """Registra las funciones RPC de la app al iniciar Django."""
        import apps.minutas.rpc  # noqa: F401
