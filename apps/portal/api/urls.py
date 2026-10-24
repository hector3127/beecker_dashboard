"""Rutas de la API v1."""

from django.urls import path

from apps.portal.api.account import (
    AccountConsumptionView,
    AccountFinanceView,
    AccountScreenView,
)
from apps.portal.api.account_hours import AccountHoursView
from apps.portal.api.agreements import AgreementDetailView, AgreementListView
from apps.portal.api.billability_area import (
    AreaBatchView,
    AreaCacheView,
    AreaIdsView,
    AreaListView,
    AreaMonthView,
)
from apps.portal.api.capacity_daily import (
    CapacityDailyProjectView,
    CapacityDailyView,
)
from apps.portal.api.eva import (
    Eva3ClosedBurnView,
    Eva3ClosedView,
    Eva3ConsumptionView,
    EvaClosedView,
)
from apps.portal.api.operations import (
    CapacityScreenView,
    Eva3ScreenView,
    EvaScreenView,
    FacturabilityResourceView,
    FacturabilityScreenView,
    FacturabilitySpecialtyView,
    InvestmentScreenView,
)
from apps.portal.api.project_actions import (
    ProjectActionsReadView,
    ProjectActionsWriteView,
)
from apps.portal.api.project_aer_planning import AerPlanningWriteView
from apps.portal.api.project_ai import (
    AiActionSave,
    AiAnalyze,
    AiAsk,
    AiDocumentRead,
    AiDriveMinute,
    AiFolderRemove,
    AiFolderSave,
    AiMemorySave,
    AiMinuteSave,
    ProjectAiAnalysisReadView,
    ProjectAiFilesReadView,
    ProjectAiFoldersReadView,
    ProjectAiMemoryReadView,
    ProjectAiMinutesReadView,
    ProjectClientReadView,
)
from apps.portal.api.project_client import ProjectClientWriteView
from apps.portal.api.project_detail import (
    ProjectAerView,
    ProjectAzureView,
    ProjectCommunicationSaveView,
    ProjectCommunicationsView,
    ProjectExecutiveView,
    ProjectFiltersView,
    ProjectMilestoneDeleteView,
    ProjectMilestoneEditView,
    ProjectMilestoneSaveView,
    ProjectMilestoneTypesView,
    ProjectPlanningAzureView,
    ProjectPlanningDeleteView,
    ProjectPlanningView,
    ProjectPlanningWriteView,
    ProjectRaidRegistryView,
    ProjectRaidView,
    ProjectRecordsView,
    ProjectResourceSaveView,
    ProjectResourcesView,
    ProjectStagesView,
    ProjectTasksView,
    RaidCreateView,
    RaidCreationOptionsView,
    RaidFieldTypesView,
    RaidPromptView,
    RaidSuggestView,
    WorkItemCommentView,
    WorkItemProgressView,
)
from apps.portal.api.screens import (
    CostSummaryView,
    Eva4ScreenView,
    ExecutiveRefreshView,
    ExecutiveScreenView,
    KpiManagersView,
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
    path(
        "screens/proyectos/<str:project_id>/planeacion-aer/<slug:operation>/",
        AerPlanningWriteView.as_view(),
    ),
    path(
        "screens/proyectos/<str:project_id>/acciones/",
        ProjectActionsReadView.as_view(),
        {"operation": "leer"},
    ),
    path(
        "screens/proyectos/<str:project_id>/acciones/partes/",
        ProjectActionsReadView.as_view(),
        {"operation": "partes-leer"},
    ),
    path(
        "screens/proyectos/<str:project_id>/acciones/<slug:operation>/",
        ProjectActionsWriteView.as_view(),
    ),
    path(
        "screens/proyectos/<str:project_id>/ia/analizar/", AiAnalyze.as_view()
    ),
    path("screens/proyectos/<str:project_id>/ia/preguntar/", AiAsk.as_view()),
    path(
        "screens/proyectos/<str:project_id>/ia/memoria/guardar/",
        AiMemorySave.as_view(),
    ),
    path(
        "screens/proyectos/<str:project_id>/ia/minutas/guardar/",
        AiMinuteSave.as_view(),
    ),
    path(
        "screens/proyectos/<str:project_id>/ia/drive/carpetas/guardar/",
        AiFolderSave.as_view(),
    ),
    path(
        "screens/proyectos/<str:project_id>/ia/drive/carpetas/quitar/",
        AiFolderRemove.as_view(),
    ),
    path(
        "screens/proyectos/<str:project_id>/ia/drive/documento/leer/",
        AiDocumentRead.as_view(),
    ),
    path(
        "screens/proyectos/<str:project_id>/ia/drive/minuta/generar/",
        AiDriveMinute.as_view(),
    ),
    path(
        "screens/proyectos/<str:project_id>/ia/accion/guardar/",
        AiActionSave.as_view(),
    ),
    path(
        "screens/proyectos/<str:project_id>/cliente/<slug:operacion>/",
        ProjectClientWriteView.as_view(),
    ),
    path(
        "screens/proyectos/<str:project_id>/cliente/",
        ProjectClientReadView.as_view(),
    ),
    path(
        "screens/proyectos/<str:project_id>/ia/analisis/",
        ProjectAiAnalysisReadView.as_view(),
    ),
    path(
        "screens/proyectos/<str:project_id>/ia/memoria/",
        ProjectAiMemoryReadView.as_view(),
    ),
    path(
        "screens/proyectos/<str:project_id>/ia/minutas/",
        ProjectAiMinutesReadView.as_view(),
    ),
    path(
        "screens/proyectos/<str:project_id>/ia/drive/carpetas/",
        ProjectAiFoldersReadView.as_view(),
    ),
    path(
        "screens/proyectos/<str:project_id>/ia/drive/archivos/",
        ProjectAiFilesReadView.as_view(),
    ),
    path(
        "screens/proyectos/<str:project_id>/azure/",
        ProjectAzureView.as_view(),
    ),
    path(
        "screens/work-items/<int:work_item_id>/avance/",
        WorkItemProgressView.as_view(),
    ),
    path(
        "screens/work-items/<int:work_item_id>/comentarios/",
        WorkItemCommentView.as_view(),
    ),
    path(
        "screens/proyectos/<str:project_id>/planeacion/",
        ProjectPlanningView.as_view(),
    ),
    path(
        "screens/proyectos/<str:project_id>/planeacion/azure/",
        ProjectPlanningAzureView.as_view(),
    ),
    path(
        "screens/proyectos/<str:project_id>/planeacion/<str:plan_type>/guardar/",
        ProjectPlanningWriteView.as_view(),
    ),
    path(
        "screens/proyectos/<str:project_id>/planeacion/<str:plan_type>/eliminar/",
        ProjectPlanningDeleteView.as_view(),
    ),
    path("screens/proyectos/hitos/tipos/", ProjectMilestoneTypesView.as_view()),
    path("screens/proyectos/comunicados/", ProjectCommunicationsView.as_view()),
    path(
        "screens/proyectos/comunicados/guardar/",
        ProjectCommunicationSaveView.as_view(),
    ),
    path("screens/proyectos/raid/prompt/", RaidPromptView.as_view()),
    path("screens/proyectos/raid/sugerir/", RaidSuggestView.as_view()),
    path(
        "screens/proyectos/<str:project_id>/raid/campos/",
        RaidFieldTypesView.as_view(),
    ),
    path(
        "screens/proyectos/<str:project_id>/raid/alta-opciones/",
        RaidCreationOptionsView.as_view(),
    ),
    path(
        "screens/proyectos/<str:project_id>/raid/crear/",
        RaidCreateView.as_view(),
    ),
    path(
        "screens/proyectos/<str:project_id>/raid-registro/",
        ProjectRaidRegistryView.as_view(),
    ),
    path(
        "screens/proyectos/<str:project_id>/hitos/guardar/",
        ProjectMilestoneSaveView.as_view(),
    ),
    path(
        "screens/proyectos/<str:project_id>/hitos/editar/",
        ProjectMilestoneEditView.as_view(),
    ),
    path(
        "screens/proyectos/<str:project_id>/hitos/eliminar/",
        ProjectMilestoneDeleteView.as_view(),
    ),
    path(
        "screens/proyectos/<str:project_id>/recursos/guardar/",
        ProjectResourceSaveView.as_view(),
    ),
    path(
        "screens/proyectos/<str:project_id>/registros/",
        ProjectRecordsView.as_view(),
    ),
    path("screens/proyectos/<str:project_id>/raid/", ProjectRaidView.as_view()),
    path(
        "screens/proyectos/<str:project_id>/tasks/", ProjectTasksView.as_view()
    ),
    path(
        "screens/proyectos/<str:project_id>/etapas/",
        ProjectStagesView.as_view(),
    ),
    path(
        "screens/proyectos/<str:project_id>/recursos/",
        ProjectResourcesView.as_view(),
    ),
    path(
        "screens/proyectos/filtros/",
        ProjectFiltersView.as_view(),
        name="project_filters",
    ),
    path(
        "screens/proyectos/<str:project_id>/ejecutivo/",
        ProjectExecutiveView.as_view(),
        name="project_executive",
    ),
    path(
        "screens/proyectos/<str:project_id>/aer/",
        ProjectAerView.as_view(),
        name="project_aer",
    ),
    path("screens/eva-1/cerrados/", EvaClosedView.as_view()),
    path("screens/eva-3/cerrados/", Eva3ClosedView.as_view()),
    path("screens/eva-3/consumos/", Eva3ConsumptionView.as_view()),
    path("screens/eva-3/cerrados/consumo/", Eva3ClosedBurnView.as_view()),
    path("screens/facturabilidad/area/areas/", AreaListView.as_view()),
    path("screens/facturabilidad/area/mes/", AreaMonthView.as_view()),
    path("screens/facturabilidad/area/lote/", AreaBatchView.as_view()),
    path("screens/facturabilidad/area/cache/", AreaCacheView.as_view()),
    path("screens/facturabilidad/area/ids/", AreaIdsView.as_view()),
    path(
        "screens/capacidad/diaria/",
        CapacityDailyView.as_view(),
        name="capacidad_diaria",
    ),
    path(
        "screens/capacidad/diaria/proyecto/",
        CapacityDailyProjectView.as_view(),
        name="capacidad_diaria_proyecto",
    ),
    path(
        "screens/cuenta/horas/", AccountHoursView.as_view(), name="cuenta_horas"
    ),
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
    path("screens/kpis-dm/", KpiManagersView.as_view(), name="kpis_dm"),
    path("screens/eva-1/", EvaScreenView.as_view(), name="eva1"),
    path("screens/eva-2/", EvaScreenView.as_view(), name="eva2"),
    path("screens/eva-3/", Eva3ScreenView.as_view(), name="eva3"),
    path(
        "screens/inversion/", InvestmentScreenView.as_view(), name="inversion"
    ),
    path("screens/capacidad/", CapacityScreenView.as_view(), name="capacidad"),
    path(
        "screens/facturabilidad/",
        FacturabilityScreenView.as_view(),
        name="facturabilidad",
    ),
    path(
        "screens/facturabilidad/especialidad/",
        FacturabilitySpecialtyView.as_view(),
        name="facturabilidad_especialidad",
    ),
    path(
        "screens/facturabilidad/recurso/",
        FacturabilityResourceView.as_view(),
        name="facturabilidad_recurso",
    ),
    path("screens/eva4/", Eva4ScreenView.as_view(), name="eva4"),
    path("screens/margenes/", MarginsScreenView.as_view(), name="margenes"),
    path(
        "screens/margenes/actualizar/",
        MarginsRefreshView.as_view(),
        name="margenes_actualizar",
    ),
    path("costs/project/", ProjectCostView.as_view(), name="project_cost"),
    path("costs/summary/", CostSummaryView.as_view(), name="cost_summary"),
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
