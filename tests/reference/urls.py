"""Rutas de la aplicacion mas la referencia anterior (detalle y RPC)."""

from django.urls import include, path

from tests.reference.views import detail

urlpatterns = [
    path("api/", include("core.rpc.urls")),
    path("proyectos/<str:project_id>/", detail),
    path("", include("config.urls")),
]
