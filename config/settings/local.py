"""Configuracion para desarrollo local."""

from config.settings.base import *  # noqa: F401, F403
from config.settings.base import REST_FRAMEWORK

"""BKD.001.002 - Configuracion local
Habilita DEBUG y permite usar la API sin iniciar sesion.
"""

DEBUG = True

PORTAL_LOGIN_REQUIRED = False

REST_FRAMEWORK = {
    **REST_FRAMEWORK,
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.AllowAny",
    ],
}
