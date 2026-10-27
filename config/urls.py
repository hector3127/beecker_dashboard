"""Rutas principales del proyecto."""

from django.contrib import admin
from django.urls import include, path

from core.frontend import csp_report

"""BKD.001.005 - Ruteo principal
Expone las vistas nuevas del portal en la raiz, los enlaces de compatibilidad
en /legacy/ y el administrador de Django. La API RPC ya no se publica:
solo la monta tests/reference/urls.py para las comparaciones de pruebas.
"""

urlpatterns = [
    path(
        "admin/",
        admin.site.urls,
    ),
    path(
        "api/v1/",
        include("apps.portal.api.urls"),
    ),
    path(
        "csp-report/",
        csp_report,
        name="csp_report",
    ),
    path(
        "gmail/",
        include("apps.gmail.urls"),
    ),
    path(
        "legacy/",
        include("core.urls"),
    ),
    path(
        "",
        include("apps.portal.urls"),
    ),
]
