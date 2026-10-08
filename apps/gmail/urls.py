"""Rutas de Gmail."""

from django.urls import path

from apps.gmail import views

"""BKD.110.013 - Rutas de Gmail
Inicio de sesion con Google y respuesta en los hilos de proyecto.
"""

app_name = "gmail"

urlpatterns = [
    path("oauth/start/", views.oauth_start, name="oauth_start"),
    path("oauth/callback/", views.oauth_callback, name="oauth_callback"),
    path("status/", views.status, name="status"),
    path("disconnect/", views.disconnect, name="disconnect"),
    path("threads/", views.threads, name="threads"),
    path("reply/", views.reply, name="reply"),
]
