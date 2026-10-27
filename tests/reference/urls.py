"""Rutas de la aplicacion mas la referencia del detalle anterior."""

from django.urls import include, path

from tests.reference.views import detail

urlpatterns = [
    path("proyectos/<str:project_id>/", detail),
    path("", include("config.urls")),
]
