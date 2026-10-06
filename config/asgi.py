"""Punto de entrada ASGI."""

import os

from django.core.asgi import get_asgi_application

"""BKD.001.006 - Arranque ASGI
Expone la aplicacion para servidores ASGI.
"""

os.environ.setdefault(
    "DJANGO_SETTINGS_MODULE",
    "config.settings.production",
)

application = get_asgi_application()
