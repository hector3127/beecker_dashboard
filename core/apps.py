"""Configuracion de la app core."""

from django.apps import AppConfig

"""BKD.006.006 - App core
Registra la app de piezas compartidas.
"""


class CoreConfig(AppConfig):
    """Piezas compartidas: Sheets, RPC, utilidades y portal."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "core"
