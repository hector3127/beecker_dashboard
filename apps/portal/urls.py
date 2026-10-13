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
    path(
        "operativa/en-ejecucion/",
        views.en_ejecucion,
        name="en_ejecucion",
    ),
    path("operativa/en-tiempo/", views.en_tiempo, name="en_tiempo"),
    path("operativa/eva-1/", views.eva1, name="eva1"),
    path(
        "operativa/kpis-delivery-managers/",
        views.kpis_delivery_managers,
        name="kpis_dm",
    ),
    path("operativa/eva-2/", views.eva2, name="eva2"),
    path(
        "operativa/capacidad-instalada/",
        views.capacidad_instalada,
        name="capacidad",
    ),
    path(
        "operativa/capacidad-instalada/exportar/",
        views.capacidad_instalada_csv,
        name="capacidad_csv",
    ),
    path("cuenta/<slug:slug>/", views.cuenta, name="cuenta"),
    path("proyecto/<str:project_id>/", views.proyecto, name="proyecto"),
    path(
        "operativa/delivery-manager/<slug:slug>/",
        views.delivery_manager,
        name="delivery_manager",
    ),
]
