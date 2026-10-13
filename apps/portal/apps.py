"""Configuracion de la app portal."""

from django.apps import AppConfig

"""BKD.120.001 - App portal
Registra las vistas nuevas del portal: Ejecutiva, Operativa y Comercial.
"""


class PortalConfig(AppConfig):
    """Vistas nuevas del portal (diseno aprobado por Gera)."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.portal"
