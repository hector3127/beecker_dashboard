"""Punto de entrada WSGI usado por gunicorn."""

import os

from django.core.wsgi import get_wsgi_application

"""BKD.001.007 - Arranque WSGI
Expone la aplicacion para gunicorn.
"""

os.environ.setdefault(
    "DJANGO_SETTINGS_MODULE",
    "config.settings.production",
)

application = get_wsgi_application()
