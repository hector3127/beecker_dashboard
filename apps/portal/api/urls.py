"""Rutas de la API v1."""

from django.urls import path

from apps.portal.api.agreements import AgreementDetailView, AgreementListView
from apps.portal.api.screens import (
    Eva4ScreenView,
    OperativaBillingView,
    OperativaBlockView,
    OperativaView,
)
from apps.portal.api.views import MeView, PingView

"""BKD.120.013 - Rutas de la API v1
Se publican bajo FRONTEND_API_BASE (por defecto /api/v1/).
"""

app_name = "api_v1"

urlpatterns = [
    path("me/", MeView.as_view(), name="me"),
    path("agreements/", AgreementListView.as_view(), name="agreements"),
    path(
        "agreements/<int:pk>/",
        AgreementDetailView.as_view(),
        name="agreement",
    ),
    path("ping/", PingView.as_view(), name="ping"),
    path("screens/eva4/", Eva4ScreenView.as_view(), name="eva4"),
    path("screens/operativa/", OperativaView.as_view(), name="operativa"),
    path(
        "screens/operativa/datos/",
        OperativaBlockView.as_view(),
        name="operativa_datos",
    ),
    path(
        "screens/operativa/facturabilidad/",
        OperativaBillingView.as_view(),
        name="operativa_billing",
    ),
]
