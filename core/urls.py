"""Rutas del portal."""

from django.urls import path

from core.views import portal_home

"""BKD.006.007 - Rutas del portal
Publica la pagina principal del panel.
"""

app_name = "core"

urlpatterns = [
    path(
        "",
        portal_home,
        name="home",
    ),
]
