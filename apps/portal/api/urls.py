"""Rutas de la API v1."""

from django.urls import path

from apps.portal.api.screens import Eva4ScreenView
from apps.portal.api.views import MeView, PingView

"""BKD.120.013 - Rutas de la API v1
Se publican bajo FRONTEND_API_BASE (por defecto /api/v1/).
"""

app_name = "api_v1"

urlpatterns = [
    path("me/", MeView.as_view(), name="me"),
    path("ping/", PingView.as_view(), name="ping"),
    path("screens/eva4/", Eva4ScreenView.as_view(), name="eva4"),
]
