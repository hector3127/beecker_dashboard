"""Rutas principales del proyecto."""

from django.contrib import admin
from django.urls import include, path

"""BKD.001.005 - Ruteo principal
Expone el panel, la API RPC y el administrador de Django.
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
        "",
        include("core.urls"),
    ),
]
