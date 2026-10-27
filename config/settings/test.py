"""Configuracion usada por pytest."""

import os

# La clave solo existe para pruebas; base.py la exige antes de cargar.
os.environ.setdefault("DJANGO_SECRET_KEY", "solo-para-pruebas")

from config.settings.base import *  # noqa: E402, F401, F403
from config.settings.base import REST_FRAMEWORK  # noqa: E402

"""BKD.001.003 - Configuracion de pruebas
Usa cache en memoria y no requiere credenciales reales.
"""

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
    },
}

GOOGLE_SPREADSHEET_ID = "spreadsheet-de-pruebas"

TIME_ENTRY_SOURCE = "sheet"

# Las pruebas leen datos distintos en cada caso: sin cache de hojas.
SHEETS_READ_CACHE_SECONDS = 0

PORTAL_LOGIN_REQUIRED = False

# Las pruebas de navegador comparan contra la referencia anterior, que lleva
# estilos en linea: la politica se aplica solo donde la prueba lo pide.
CSP_ENFORCE = False

REST_FRAMEWORK = {
    **REST_FRAMEWORK,
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.AllowAny",
    ],
}
