"""Configuracion de la app access."""

from django.apps import AppConfig

"""BKD.140.001 - App access
Concentra las reglas de acceso: capacidades (que puede hacer una persona)
y alcance (sobre que cuentas y proyectos). Las pantallas y la API le
preguntan a esta app; ninguna decide por su cuenta.
"""


class AccessConfig(AppConfig):
    """Capacidades y alcance de datos del portal."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.access"
