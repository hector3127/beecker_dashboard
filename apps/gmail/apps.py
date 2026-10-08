"""Configuracion de la app gmail."""

from django.apps import AppConfig

"""BKD.110.001 - App gmail
Registra la app que responde en los hilos de Gmail de cada proyecto.
"""


class GmailConfig(AppConfig):
    """Comunicados de extension enviados desde el Gmail del usuario."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.gmail"
