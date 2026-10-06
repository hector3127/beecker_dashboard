"""Configuracion de la app capacidad."""

from django.apps import AppConfig

"""BKD.050.001 - App capacidad
Registra la app y sus funciones RPC.
"""


class CapacidadConfig(AppConfig):
    """Capacidad instalada por recurso, proyecto y mes."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.capacidad"

    def ready(self) -> None:
        """Registra las funciones RPC de la app al iniciar Django."""
        import apps.capacidad.rpc  # noqa: F401
