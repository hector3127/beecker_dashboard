"""Rutas de la API v1."""

from django.urls import path

from apps.portal.api.account import (
    AccountConsumptionView,
    AccountFinanceView,
    AccountScreenView,
)
from apps.portal.api.agreements import AgreementDetailView, AgreementListView
from apps.portal.api.screens import (
    Eva4ScreenView,
    ExecutiveRefreshView,
    ExecutiveScreenView,
    ManagerScreenView,
    MarginsRefreshView,
    MarginsScreenView,
    OperativaBillingView,
    OperativaBlockView,
    OperativaView,
    ProjectCostView,
)
from apps.portal.api.views import GlossaryView, MeView, PingView

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
    path("reference/glossary/", GlossaryView.as_view(), name="glossary"),
    path("ping/", PingView.as_view(), name="ping"),
    path("screens/cuenta/", AccountScreenView.as_view(), name="cuenta"),
    path(
        "screens/cuenta/consumos/",
        AccountConsumptionView.as_view(),
        name="cuenta_consumos",
    ),
    path(
        "screens/cuenta/finanzas/",
        AccountFinanceView.as_view(),
        name="cuenta_finanzas",
    ),
    path(
        "screens/delivery-managers/<slug:slug>/",
        ManagerScreenView.as_view(),
        name="delivery_manager",
    ),
    path("screens/executive/", ExecutiveScreenView.as_view(), name="executive"),
    path(
        "screens/executive/actualizar/",
        ExecutiveRefreshView.as_view(),
        name="executive_actualizar",
    ),
    path("screens/eva4/", Eva4ScreenView.as_view(), name="eva4"),
    path("screens/margenes/", MarginsScreenView.as_view(), name="margenes"),
    path(
        "screens/margenes/actualizar/",
        MarginsRefreshView.as_view(),
        name="margenes_actualizar",
    ),
    path("costs/project/", ProjectCostView.as_view(), name="project_cost"),
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
