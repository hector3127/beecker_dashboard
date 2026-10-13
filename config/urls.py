"""Rutas principales del proyecto."""

from django.contrib import admin
from django.urls import include, path

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
        "api/",
        include("core.rpc.urls"),
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
