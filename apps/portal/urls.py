"""Rutas de las vistas nuevas del portal."""

from django.urls import path

from apps.portal import views

"""BKD.120.011 - Rutas del portal
Ejecutiva en la raiz, Operativa y Comercial. El panel anterior (con
Capacidad instalada, GSE, Daily, Minutas y Recursos) sigue en /legacy/.
"""

app_name = "portal"

urlpatterns = [
    path("", views.ejecutiva, name="ejecutiva"),
    path("operativa/", views.operativa, name="operativa"),
    path("comercial/", views.comercial, name="comercial"),
    path(
        "operativa/suspendidos/",
        views.suspendidos,
        name="suspendidos",
    ),
    path("operativa/eva-1/", views.eva1, name="eva1"),
    path("operativa/eva-2/", views.eva2, name="eva2"),
    path(
        "operativa/delivery-manager/<slug:slug>/",
        views.delivery_manager,
        name="delivery_manager",
    ),
]
