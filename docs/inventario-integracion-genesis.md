# Inventario de páginas y API para Genesis

Lectura estática de las rutas del dashboard al 02/11/2026. No se ejecutan
vistas, conexiones ni escrituras para obtener esta lista. Fuente de verdad:
`apps/portal/urls.py`, `apps/portal/api/urls.py` y clases de sus módulos.
Los métodos listados excluyen HEAD/OPTIONS implícitos y no sustituyen una
prueba de contrato o una revisión del alcance de permisos.

## Rutas de página

Base actual `/`. En Genesis las rutas necesitan un prefijo propio para no
colisionar con su Dashboard/Proyectos. Incluye alias y rutas de exportación:
no equivale a un conteo de pantallas independientes.

| Ruta | Vista |
|---|---|
| `/guia-de-interfaz/` | `pages.guia` |
| `/ejecutiva/oportunidades/` | `pages.margins` |
| `/diccionario-datos/` | `pages.dictionary` |
| `/ejecutiva/actualizacion/` | `views.actualizacion_ejecutiva` |
| `/ejecutiva/acuerdos/` | `views.acuerdos_ejecutivos` |
| `/ejecutiva/cuentas/` | `pages.all_accounts` |
| `/ejecutiva/costos/detalle/` | `pages.costs` |
| `/cuenta/financiera/` | `views.cuenta_financiera` |
| `/ejecutiva/costos/` | `views.costos_revenue` |
| `/ejecutiva/ingresos/` | `views.ingresos` |
| `/operativa/eva3/cerrados/burn/` | `views.eva3_cerrados_burn` |
| `/operativa/eva3/cerrados/` | `pages.eva3_cerrados` |
| `/` | `pages.executive` |
| `/proyectos/<str:project_id>/` | `pages.project_detail` |
| `/capacidad-instalada/` | `pages.capacity_daily` |
| `/operativa/` | `pages.operativa` |
| `/comercial/` | `pages.commercial` |
| `/operativa/eva-1/` | `pages.eva1` |
| `/operativa/eva-1/summary/` | `pages.summary_inventory` |
| `/operativa/inversion/` | `pages.investment` |
| `/operativa/facturabilidad/` | `pages.billability` |
| `/operativa/facturabilidad/especialidad/` | `pages.billability_specialty` |
| `/operativa/facturabilidad/recurso/` | `pages.billability_resource` |
| `/operativa/facturabilidad/area/` | `pages.billability_area` |
| `/operativa/kpis-delivery-managers/` | `pages.kpis_dm` |
| `/operativa/eva-2/` | `pages.eva2` |
| `/operativa/eva-4/` | `pages.eva4` |
| `/operativa/eva-3/` | `pages.eva3` |
| `/operativa/capacidad-instalada/` | `pages.capacity` |
| `/operativa/capacidad-instalada/exportar/` | `views.capacidad_instalada_csv` |
| `/cuenta/<slug:slug>/` | `pages.account` |
| `/cuenta/<slug:slug>/horas/` | `pages.account_hours` |
| `/proyecto/<str:project_id>/` | `pages.project` |
| `/operativa/delivery-manager/<slug:slug>/` | `pages.delivery_manager` |

## API publicada

Base actual `/api/v1/`. No incluye `/api/rpc/`, que solo montan las pruebas.
La ubicación final en Genesis debe acordarse; no cambiar consumidores sin
adaptar el servicio cliente y revisar exportaciones, sesión y CSRF.

| Ruta | Métodos | Clase y módulo |
|---|---|---|
| `/api/v1/screens/proyectos/<str:project_id>/ia-aer/config-guardar/` | POST | `AerAiConfigWriteView` en `apps/portal/api/project_aer_ai.py` |
| `/api/v1/screens/proyectos/<str:project_id>/ia-aer/prompt/` | GET | `AerAiReadView` en `apps/portal/api/project_aer_ai.py` |
| `/api/v1/screens/proyectos/<str:project_id>/ia-aer/analisis/` | GET | `AerAiReadView` en `apps/portal/api/project_aer_ai.py` |
| `/api/v1/screens/proyectos/<str:project_id>/ia-aer/resumen/` | GET | `AerAiReadView` en `apps/portal/api/project_aer_ai.py` |
| `/api/v1/screens/proyectos/<str:project_id>/ia-aer/minutas/` | GET | `AerAiReadView` en `apps/portal/api/project_aer_ai.py` |
| `/api/v1/screens/proyectos/<str:project_id>/ia-aer/config/` | GET | `AerAiConfigReadView` en `apps/portal/api/project_aer_ai.py` |
| `/api/v1/screens/proyectos/<str:project_id>/ia-aer/archivos/` | GET | `AerAiReadView` en `apps/portal/api/project_aer_ai.py` |
| `/api/v1/screens/proyectos/<str:project_id>/evaluaciones-aer/<slug:operation>/` | POST | `AerResourcesWriteView` en `apps/portal/api/project_aer_resources.py` |
| `/api/v1/screens/proyectos/<str:project_id>/riesgos-aer/` | GET | `AerRisksReadView` en `apps/portal/api/project_aer_risks.py` |
| `/api/v1/screens/proyectos/<str:project_id>/riesgos-aer/<slug:operation>/` | POST | `AerRisksWriteView` en `apps/portal/api/project_aer_risks.py` |
| `/api/v1/screens/proyectos/<str:project_id>/aer/registros/` | GET | `ProjectAerRecordsView` en `apps/portal/api/project_detail.py` |
| `/api/v1/screens/proyectos/<str:project_id>/planeacion-aer/<slug:operation>/` | POST | `AerPlanningWriteView` en `apps/portal/api/project_aer_planning.py` |
| `/api/v1/screens/proyectos/<str:project_id>/acciones/` | GET | `ProjectActionsReadView` en `apps/portal/api/project_actions.py` |
| `/api/v1/screens/proyectos/<str:project_id>/acciones/partes/` | GET | `ProjectActionsReadView` en `apps/portal/api/project_actions.py` |
| `/api/v1/screens/proyectos/<str:project_id>/acciones/<slug:operation>/` | POST | `ProjectActionsWriteView` en `apps/portal/api/project_actions.py` |
| `/api/v1/account-logos/` | DELETE, GET, POST | `AccountLogoListView` en `apps/portal/api/account_logos.py` |
| `/api/v1/account-logos/<int:pk>/image/` | GET | `AccountLogoImageView` en `apps/portal/api/account_logos.py` |
| `/api/v1/screens/proyectos/<str:project_id>/ia/analizar/` | POST | `AiAnalyze` en `apps/portal/api/project_ai.py` |
| `/api/v1/screens/proyectos/<str:project_id>/ia/preguntar/` | POST | `AiAsk` en `apps/portal/api/project_ai.py` |
| `/api/v1/screens/proyectos/<str:project_id>/ia/memoria/guardar/` | POST | `AiMemorySave` en `apps/portal/api/project_ai.py` |
| `/api/v1/screens/proyectos/<str:project_id>/ia/minutas/guardar/` | POST | `AiMinuteSave` en `apps/portal/api/project_ai.py` |
| `/api/v1/screens/proyectos/<str:project_id>/ia/drive/carpetas/guardar/` | POST | `AiFolderSave` en `apps/portal/api/project_ai.py` |
| `/api/v1/screens/proyectos/<str:project_id>/ia/drive/carpetas/quitar/` | POST | `AiFolderRemove` en `apps/portal/api/project_ai.py` |
| `/api/v1/screens/proyectos/<str:project_id>/ia/drive/documento/leer/` | POST | `AiDocumentRead` en `apps/portal/api/project_ai.py` |
| `/api/v1/screens/proyectos/<str:project_id>/ia/drive/minuta/generar/` | POST | `AiDriveMinute` en `apps/portal/api/project_ai.py` |
| `/api/v1/screens/proyectos/<str:project_id>/ia/accion/guardar/` | POST | `AiActionSave` en `apps/portal/api/project_ai.py` |
| `/api/v1/screens/proyectos/<str:project_id>/cliente/<slug:operacion>/` | POST | `ProjectClientWriteView` en `apps/portal/api/project_client.py` |
| `/api/v1/screens/proyectos/<str:project_id>/cliente/` | GET | `ProjectClientReadView` en `apps/portal/api/project_ai.py` |
| `/api/v1/screens/proyectos/<str:project_id>/ia/analisis/` | GET | `ProjectAiAnalysisReadView` en `apps/portal/api/project_ai.py` |
| `/api/v1/screens/proyectos/<str:project_id>/ia/memoria/` | GET | `ProjectAiMemoryReadView` en `apps/portal/api/project_ai.py` |
| `/api/v1/screens/proyectos/<str:project_id>/ia/minutas/` | GET | `ProjectAiMinutesReadView` en `apps/portal/api/project_ai.py` |
| `/api/v1/screens/proyectos/<str:project_id>/ia/drive/carpetas/` | GET | `ProjectAiFoldersReadView` en `apps/portal/api/project_ai.py` |
| `/api/v1/screens/proyectos/<str:project_id>/ia/drive/archivos/` | GET | `ProjectAiFilesReadView` en `apps/portal/api/project_ai.py` |
| `/api/v1/screens/proyectos/<str:project_id>/azure/` | GET | `ProjectAzureView` en `apps/portal/api/project_detail.py` |
| `/api/v1/screens/work-items/<int:work_item_id>/avance/` | POST | `WorkItemProgressView` en `apps/portal/api/project_detail.py` |
| `/api/v1/screens/work-items/<int:work_item_id>/comentarios/` | POST | `WorkItemCommentView` en `apps/portal/api/project_detail.py` |
| `/api/v1/screens/proyectos/<str:project_id>/planeacion/` | GET | `ProjectPlanningView` en `apps/portal/api/project_detail.py` |
| `/api/v1/screens/proyectos/<str:project_id>/planeacion/azure/` | GET | `ProjectPlanningAzureView` en `apps/portal/api/project_detail.py` |
| `/api/v1/screens/proyectos/<str:project_id>/planeacion/<str:plan_type>/guardar/` | POST | `ProjectPlanningWriteView` en `apps/portal/api/project_detail.py` |
| `/api/v1/screens/proyectos/<str:project_id>/planeacion/<str:plan_type>/eliminar/` | POST | `ProjectPlanningDeleteView` en `apps/portal/api/project_detail.py` |
| `/api/v1/screens/proyectos/hitos/tipos/` | GET | `ProjectMilestoneTypesView` en `apps/portal/api/project_detail.py` |
| `/api/v1/screens/proyectos/comunicados/` | GET | `ProjectCommunicationsView` en `apps/portal/api/project_detail.py` |
| `/api/v1/screens/proyectos/comunicados/guardar/` | POST | `ProjectCommunicationSaveView` en `apps/portal/api/project_detail.py` |
| `/api/v1/screens/proyectos/raid/prompt/` | GET, POST | `RaidPromptView` en `apps/portal/api/project_detail.py` |
| `/api/v1/screens/proyectos/raid/sugerir/` | POST | `RaidSuggestView` en `apps/portal/api/project_detail.py` |
| `/api/v1/screens/proyectos/<str:project_id>/raid/campos/` | GET | `RaidFieldTypesView` en `apps/portal/api/project_detail.py` |
| `/api/v1/screens/proyectos/<str:project_id>/raid/alta-opciones/` | GET | `RaidCreationOptionsView` en `apps/portal/api/project_detail.py` |
| `/api/v1/screens/proyectos/<str:project_id>/raid/crear/` | POST | `RaidCreateView` en `apps/portal/api/project_detail.py` |
| `/api/v1/screens/proyectos/<str:project_id>/raid-registro/` | GET | `ProjectRaidRegistryView` en `apps/portal/api/project_detail.py` |
| `/api/v1/screens/proyectos/<str:project_id>/hitos/guardar/` | POST | `ProjectMilestoneSaveView` en `apps/portal/api/project_detail.py` |
| `/api/v1/screens/proyectos/<str:project_id>/hitos/editar/` | POST | `ProjectMilestoneEditView` en `apps/portal/api/project_detail.py` |
| `/api/v1/screens/proyectos/<str:project_id>/hitos/eliminar/` | POST | `ProjectMilestoneDeleteView` en `apps/portal/api/project_detail.py` |
| `/api/v1/screens/proyectos/<str:project_id>/recursos/guardar/` | POST | `ProjectResourceSaveView` en `apps/portal/api/project_detail.py` |
| `/api/v1/screens/proyectos/<str:project_id>/registros/` | GET | `ProjectRecordsView` en `apps/portal/api/project_detail.py` |
| `/api/v1/screens/proyectos/<str:project_id>/raid/` | GET | `ProjectRaidView` en `apps/portal/api/project_detail.py` |
| `/api/v1/screens/proyectos/<str:project_id>/tasks/` | GET | `ProjectTasksView` en `apps/portal/api/project_detail.py` |
| `/api/v1/screens/proyectos/<str:project_id>/clockify-rango/` | GET | `ProjectClockifyRangeView` en `apps/portal/api/project_detail.py` |
| `/api/v1/screens/proyectos/<str:project_id>/riesgos-manuales/` | POST | `ProjectManualRiskSaveView` en `apps/portal/api/project_detail.py` |
| `/api/v1/screens/proyectos/<str:project_id>/etapas/` | GET | `ProjectStagesView` en `apps/portal/api/project_detail.py` |
| `/api/v1/screens/proyectos/<str:project_id>/recursos/` | GET | `ProjectResourcesView` en `apps/portal/api/project_detail.py` |
| `/api/v1/screens/proyectos/filtros/` | GET | `ProjectFiltersView` en `apps/portal/api/project_detail.py` |
| `/api/v1/screens/proyectos/<str:project_id>/ejecutivo/` | GET | `ProjectExecutiveView` en `apps/portal/api/project_detail.py` |
| `/api/v1/screens/proyectos/<str:project_id>/aer/` | GET | `ProjectAerView` en `apps/portal/api/project_detail.py` |
| `/api/v1/screens/eva-3/cerrados/` | GET | `Eva3ClosedView` en `apps/portal/api/eva.py` |
| `/api/v1/screens/eva-3/consumos/` | POST | `Eva3ConsumptionView` en `apps/portal/api/eva.py` |
| `/api/v1/screens/eva-3/cerrados/consumo/` | POST | `Eva3ClosedBurnView` en `apps/portal/api/eva.py` |
| `/api/v1/screens/facturabilidad/area/areas/` | GET | `AreaListView` en `apps/portal/api/billability_area.py` |
| `/api/v1/screens/facturabilidad/area/mes/` | GET | `AreaMonthView` en `apps/portal/api/billability_area.py` |
| `/api/v1/screens/facturabilidad/area/lote/` | GET | `AreaBatchView` en `apps/portal/api/billability_area.py` |
| `/api/v1/screens/facturabilidad/area/cache/` | GET, POST | `AreaCacheView` en `apps/portal/api/billability_area.py` |
| `/api/v1/screens/facturabilidad/area/ids/` | POST | `AreaIdsView` en `apps/portal/api/billability_area.py` |
| `/api/v1/screens/capacidad/diaria/` | GET | `CapacityDailyView` en `apps/portal/api/capacity_daily.py` |
| `/api/v1/screens/cuenta/horas/` | GET | `AccountHoursView` en `apps/portal/api/account_hours.py` |
| `/api/v1/me/` | GET | `MeView` en `apps/portal/api/views.py` |
| `/api/v1/agreements/` | GET, POST | `AgreementListView` en `apps/portal/api/agreements.py` |
| `/api/v1/agreements/<int:pk>/` | PATCH | `AgreementDetailView` en `apps/portal/api/agreements.py` |
| `/api/v1/reference/glossary/` | GET | `GlossaryView` en `apps/portal/api/views.py` |
| `/api/v1/ping/` | GET | `PingView` en `apps/portal/api/views.py` |
| `/api/v1/screens/cuenta/` | GET | `AccountScreenView` en `apps/portal/api/account.py` |
| `/api/v1/screens/cuenta/consumos/` | GET | `AccountConsumptionView` en `apps/portal/api/account.py` |
| `/api/v1/screens/cuenta/finanzas/` | GET | `AccountFinanceView` en `apps/portal/api/account.py` |
| `/api/v1/screens/delivery-managers/<slug:slug>/` | GET | `ManagerScreenView` en `apps/portal/api/screens.py` |
| `/api/v1/screens/executive/` | GET | `ExecutiveScreenView` en `apps/portal/api/screens.py` |
| `/api/v1/screens/executive/actualizar/` | GET, POST | `ExecutiveRefreshView` en `apps/portal/api/screens.py` |
| `/api/v1/screens/kpis-dm/` | GET | `KpiManagersView` en `apps/portal/api/screens.py` |
| `/api/v1/screens/eva-2/` | GET | `EvaScreenView` en `apps/portal/api/operations.py` |
| `/api/v1/screens/eva-3/` | GET | `Eva3ScreenView` en `apps/portal/api/operations.py` |
| `/api/v1/screens/inversion/` | GET | `InvestmentScreenView` en `apps/portal/api/operations.py` |
| `/api/v1/screens/capacidad/` | GET | `CapacityScreenView` en `apps/portal/api/operations.py` |
| `/api/v1/screens/facturabilidad/` | GET | `FacturabilityScreenView` en `apps/portal/api/operations.py` |
| `/api/v1/screens/facturabilidad/especialidad/` | GET | `FacturabilitySpecialtyView` en `apps/portal/api/operations.py` |
| `/api/v1/screens/facturabilidad/recurso/` | GET | `FacturabilityResourceView` en `apps/portal/api/operations.py` |
| `/api/v1/screens/eva4/` | GET | `Eva4ScreenView` en `apps/portal/api/screens.py` |
| `/api/v1/screens/margenes/` | GET | `MarginsScreenView` en `apps/portal/api/screens.py` |
| `/api/v1/screens/margenes/actualizar/` | GET, POST | `MarginsRefreshView` en `apps/portal/api/screens.py` |
| `/api/v1/costs/project/` | GET | `ProjectCostView` en `apps/portal/api/screens.py` |
| `/api/v1/costs/summary/` | GET | `CostSummaryView` en `apps/portal/api/screens.py` |
| `/api/v1/screens/operativa/` | GET | `OperativaView` en `apps/portal/api/screens.py` |
| `/api/v1/screens/operativa/datos/` | GET | `OperativaBlockView` en `apps/portal/api/screens.py` |
| `/api/v1/screens/operativa/facturabilidad/` | GET | `OperativaBillingView` en `apps/portal/api/screens.py` |

## Bloques funcionales y orden propuesto

| Bloque | Entradas principales | Dependencias |
|---|---|---|
| Piloto EVA1 | `/operativa/eva-1/`, `screens/eva1/`, Summary renderizado por pages.summary_inventory | Inventario local, cortes, iteraciones, Clockify, histórico Azure |
| KPI DM | `/operativa/kpis-delivery-managers/`, `screens/kpis-dm/` | Tablas KPI propias; no reconstruir al consultar |
| Operativa y capacidad | `/operativa/`, capacidad, facturabilidad, inversión | Catálogos, roster, horas, cortes y tags |
| EVA3/EVA4 | Vistas de servicio y contratos | MPB/ROC, horas y reglas propias, no reutilizar fórmula de otro EVA por nombre |
| Business Overview y financiera | Raíz, márgenes, ingresos, costos y cuentas | Sheets DataRevenue/bandas/tarifas, horas; refrescos separados de lectura |
| Comercial | `/comercial/` | Contexto/servicios comerciales; revisar datos aún renderizados en servidor |
| Detalle proyecto | `/proyectos/<id>/`, `screens/proyectos/...` | Familias AER/IXS, pestañas, lecturas/escrituras, IA/Drive/Azure |
| Cuenta y horas | `/cuenta/<slug>/`, `/cuenta/<slug>/horas/` | Scope de cuenta/proyecto, CSV, navegación de regreso |

No todos los datos de páginas pasan ya por una única API: Summary conserva
renderizado en Django y hay contextos conservados en views.py. Antes de portar
una pantalla, fijar campos/tipos/nulos, parámetros y errores de su contrato;
no trasladar HTML de servidor a React ni duplicar cálculos en componentes.

Inventariadas 34 entradas path de página y 100 entradas path de API.

## Lista de aceptación por pantalla

- IDs y cifras con la misma muestra fija/corte que la aplicación independiente.
- Filtros, URL, paginación, exportación y regreso a su origen.
- Usuario sin sesión, sin permiso, con alcance limitado y con permiso total.
- Carga, resultado parcial, dato desconocido, error, reintento y respuestas tardías.
- Escrituras con CSRF; sin efectos externos al probar contratos.
- Diseño propio aprobado conservado; responsivo en claro/oscuro y modo sistema,
  usando el ThemeProvider y la navegación de Genesis. Sin selector duplicado
  ni cambios en filtros/cifras al alternar el tema. Criterios en G04-T del plan.
- Tiempos de lectura/actualización y trazabilidad de las fuentes.
- Pruebas de negocio conservadas y gates de Genesis sin debilitar reglas.
