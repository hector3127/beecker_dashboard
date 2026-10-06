"""Configuracion para produccion."""

from config.settings.base import *  # noqa: F401, F403

"""BKD.001.004 - Configuracion de produccion
Activa cookies seguras y archivos estaticos comprimidos.
"""

SESSION_COOKIE_SECURE = True

CSRF_COOKIE_SECURE = True

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": ("whitenoise.storage.CompressedManifestStaticFilesStorage"),
    },
}
