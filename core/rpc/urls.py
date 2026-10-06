"""Rutas de la API RPC."""

from django.urls import path

from core.rpc.views import RpcView

"""BKD.006.005 - Rutas RPC
Publica el endpoint /api/rpc/<funcion>/.
"""

app_name = "rpc"

urlpatterns = [
    path(
        "rpc/<str:function_name>/",
        RpcView.as_view(),
        name="call",
    ),
]
