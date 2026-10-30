"""Rutas de pruebas: la aplicacion mas el transporte RPC que no se publica."""

from django.urls import include, path

urlpatterns = [
    path("api/", include("core.rpc.urls")),
    path("", include("config.urls")),
]
