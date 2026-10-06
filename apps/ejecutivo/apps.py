"""Configuracion de la app ejecutivo."""

from django.apps import AppConfig

"""BKD.040.005 - App ejecutivo
Registra la app y sus funciones RPC.
"""


class EjecutivoConfig(AppConfig):
    """Resumen ejecutivo de alto nivel."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.ejecutivo"

    def ready(self) -> None:
        """Registra las funciones RPC de la app al iniciar Django."""
        import apps.ejecutivo.account_rpc  # noqa: F401
        import apps.ejecutivo.rpc  # noqa: F401
        import apps.ejecutivo.write_rpc  # noqa: F401
