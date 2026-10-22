"""Rutas principales del proyecto."""

from django.contrib import admin
from django.urls import include, path

from core.frontend import csp_report

"""BKD.001.005 - Ruteo principal
Expone las vistas nuevas del portal en la raiz, el panel anterior en
/legacy/, la API RPC y el administrador de Django.
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
        "api/",
        include("core.rpc.urls"),
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
