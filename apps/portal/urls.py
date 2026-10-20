"""Rutas de las vistas nuevas del portal."""

from django.urls import path

from apps.portal import views

"""BKD.120.011 - Rutas del portal
Ejecutiva en la raiz, Operativa y Comercial. Capacidad instalada,
proyectos y Facturabilidad por area tienen sus propias paginas del portal.
"""

app_name = "portal"

urlpatterns = [
    path("diccionario-datos/", views.diccionario_datos, name="diccionario_datos"),
    path(
        "ejecutiva/actualizacion/", views.actualizacion_ejecutiva,
        name="actualizacion_ejecutiva",
    ),
    path("ejecutiva/comercial/", views.comercial_ejecutiva, name="comercial_ejecutiva"),
    path("ejecutiva/acuerdos/", views.acuerdos_ejecutivos, name="acuerdos_ejecutivos"),
    path("ejecutiva/cuentas/", views.todas_cuentas, name="todas_cuentas"),
    path("ejecutiva/operations/", views.operaciones_ejecutiva, name="operaciones_ejecutiva"),
    path("cuenta/financiera/", views.cuenta_financiera, name="cuenta_financiera"),
    path("ejecutiva/cuentas/rentabilidad/", views.cuentas_rentabilidad, name="cuentas_rentabilidad"),
    path(
        "ejecutiva/costos/detalle/", views.costos_detalle,
        name="costos_detalle",
    ),
    path(
        "ejecutiva/rentabilidad/", views.rentabilidad_mensual,
        name="rentabilidad_mensual",
    ),
    path("ejecutiva/costos/", views.costos_revenue, name="costos_revenue"),
    path("ejecutiva/ingresos/", views.ingresos, name="ingresos"),
    path("operativa/eva3/cerrados/burn/", views.eva3_cerrados_burn, name="eva3_cerrados_burn"),
    path("operativa/eva3/cerrados/", views.eva3_cerrados, name="eva3_cerrados"),
    path(
        "operativa/operations-resumen/",
        views.operations_resumen,
        name="operations_resumen_legacy",
    ),
    path(
        "operations/resumen/",
        views.operations_resumen,
        name="operations_resumen",
    ),
    path("", views.ejecutiva, name="ejecutiva"),
    path("proyectos/<str:project_id>/", views.proyecto_detalle, name="proyecto_detalle"),
    path("capacidad-instalada/", views.capacidad_detalle, name="capacidad_detalle"),
    path("operativa/", views.operativa, name="operativa"),
    path("operativa/datos/", views.operativa_datos, name="operativa_datos"),
    path("comercial/", views.comercial, name="comercial"),
    path("operativa/eva-1/", views.eva1, name="eva1"),
    path(
        "operativa/eva-1/cerrados/",
        views.eva1_cerrados,
        name="eva1_cerrados",
    ),
    path("operativa/inversion/", views.inversion, name="inversion"),
    path(
        "operativa/facturabilidad/",
        views.facturabilidad,
        name="facturabilidad",
    ),
    path(
        "operativa/facturabilidad/especialidad/",
        views.facturabilidad_especialidad,
        name="facturabilidad_especialidad",
    ),
    path(
        "operativa/facturabilidad/recurso/",
        views.facturabilidad_recurso,
        name="facturabilidad_recurso",
    ),
    path("operativa/facturabilidad/area/", views.facturabilidad_area, name="facturabilidad_area"),
    path(
        "operativa/kpis-delivery-managers/",
        views.kpis_delivery_managers,
        name="kpis_dm",
    ),
    path("operativa/eva-2/", views.eva2, name="eva2"),
    path("operativa/eva-4/", views.eva4, name="eva4"),
    path("operativa/eva-3/", views.eva3, name="eva3"),
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
