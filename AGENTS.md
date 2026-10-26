# AGENTS.md — Migración del frontend de Beecker

Guía para continuar la migración con cualquier agente (Codex, Claude Code…). Lee esto y `docs/plan-migracion-frontend.md` antes de tocar nada.

## Objetivo

Pasar cada pantalla del portal a `frontend/` con HTML, CSS y JS separados. Django sigue como servidor.

Reglas que no se negocian:

1. **Diseño idéntico** al de la pantalla anterior (misma estructura visual, cifras, filtros, exportaciones, permisos y navegación de regreso).
2. **No cambiar cálculos ni reglas de negocio.** Si algo parece mal, repórtalo; no lo "arregles" para que coincidan reportes.
3. **No activar `ACCESS_ENFORCED` en producción** sin accesos configurados.
4. **Horas por mes** (`cuenta/<slug>/horas/`) se conserva tal cual: filtros de fechas y proyectos, CSV, permisos y regreso a la cuenta.
5. Commits pequeños y cuidados **directo en `main`** (único desarrollador, sin ramas). **No hagas push** salvo que el usuario lo pida expresamente.
6. Nunca subas `.env`, `key.json` ni credenciales. No toques cambios sin commitear que no sean tuyos.
7. Solo marca una pantalla como terminada cuando su ruta activa usa la plantilla de `frontend/`, conserva su funcionamiento y tiene prueba y comparación visual con la anterior.
8. Actualiza `docs/plan-migracion-frontend.md` con evidencia real en cada bloque.
9. Lecturas de frontend con `apiGet` o el catálogo compartido de logos; no
   añadir fetch directo para leer datos. Conservar la excepción documentada
   de escritura multipart de logos. No revertir 0de6c7d, 3410e89, 47d0364
   ni el comportamiento de Capacidad diaria de 834bbfa.

## Estado vigente: fase 10 completada (26/10/2026)

Bloque actual de fase 11: EVA 2 y Capacidad mensual sirven solo frontend;
retiradas sus dos plantillas anteriores, sin modificar contexto ni CSV. Seis
snapshots de diseño vigente se registraron sobre 7420d17 ANTES de borrarlas,
y se revalidan con CSP de prueba. Seis casos nuevos de acceso comprueban que
vista=anterior no evita login/permisos. 1715 servidor, 504 Node y 34 Chrome pasan.
Ver `docs/retiro-capacidad-eva2.md` para navegador, referencias y límites.
Quedan 23 HTML/35 estáticos de portal; no tocar Capacidad diaria ni sus reglas.
Fase 11 sigue abierta; sin push de este bloque.

Último bloque fase 11: limpieza agrupada sobre **1e17d99**, 21 archivos y
1.42 MB retirados. Inversión, Proyecto simple y Todas las cuentas ya no sirven
plantilla anterior. Cuatro huérfanos del portal y el árbol del panel original
se retiraron: /legacy/ solo redirige y conserva sus destinos/login. No recrear
core/index, legacy_skin ni templates/legacy. Siete snapshots de diseño vigente
se guardaron antes de borrar y pasan con CSP de prueba. Evidencia: 1711 servidor,
504 Node, 28 Chrome; sin skips. Ver `docs/limpieza-por-lotes.md`. Siguen activos
otros respaldos y sus pruebas: no borrar gas_shim, motor portal ni RPC aún.
Quedan 25 HTML/35 estáticos de portal. Sin push; fase 11 abierta.

Último bloque fase 11: KPIs DM sin vista/plantilla/entrada anterior ni JS de
gráfica de portal. Sus pruebas Node importan el módulo actual, manteniendo
casos. API/contexto/cálculos intactos; pruebas de cortes adaptadas sin omisiones.
1693 servidor (incluyen 78 dirigidas), 505 Node, 40 Chrome y revalidación KPI de 10 pasan
(con solapamiento). Capturas idénticas antes/después en tres tamaños con CSP
de pruebas. Quedan 30 HTML y 36 estáticos anteriores; continuar limpieza y CSP
sin activar accesos ni bloqueo global. Base 3c5b2fa publicada al inicio del
bloque; nuevos cambios posteriores sin push. Ver traspaso y preparación fase 11.

Integración posterior de Christian reorganizada sobre **3410e89**: 17 entradas
documentadas y con modelos/vistas/controladores separados; 12 hojas exclusivas
fusionadas en seis destinos, conservando acuerdos compartidos. 1691 servidor,
505 Node y 57 navegador finales aprobadas. Referencia controlada: 54 casos
contra ese commit, 53 capturas comparadas (42 idénticas; resto hora/pintado).
Ver `docs/integracion-christian.md` para pantallas, diferencias y revalidaciones.
La corrida amplia previa tuvo un fallo de sincronización de prueba; su espera
se corrigió y se comprobó en la corrida final, sin omitirlo. Fase 11 sigue
abierta; continuar otras referencias y CSP, no reabrir los logos unificados.

El detalle activo ya arranca sin script/shim anteriores. Los contratos públicos
delegan a módulos en `project_commands.js`, y CSS base está copiado sin cambios
a frontend. La ruta requiere ID; Cuenta es una ruta distinta, y el centinela
oculto recupera el ID sembrado. Las referencias originales solo se cargan en
pruebas explícitas de comparación. No retirar los archivos de referencia.
Validación: 478 Node aprobadas; suite general de 3862 casos ejecutada y
revalidación de 55 casos aprobada tras corregir ocho pruebas y reemplazar una
parametrización vacía por tres casos de acceso reales. Resultado consolidado:
3864 casos Python verificados, sin omisiones pendientes. El plan registra las
ejecuciones separadas; no se afirma una segunda corrida general de una hora.
Ruff/formato, Django y mypy aprobados. Código en fa4bf11; cierre documentado.

El usuario autorizó preparar la **fase 11**. La integración posterior del
rediseño está validada: migración local de logos aplicada, regresión de rangos
MPB restaurada al contrato previo y ajuste CSP de vista previa probado sin
bloqueo global. Evidencia: 388 servidor, 498 Node, 74 Chrome; revalidación
logos/CSP 15 casos (con solapamiento). Ver `docs/preparacion-fase-11.md`.
Fase 11 iniciada: retirada la vista/plantilla anterior de EVA-04 y su rama de
comparación. Los enlaces antiguos sirven la pantalla modular sin perder mes.
1682 pruebas de servidor (portal/core/accesos), 498 Node y 38 Chrome aprobadas; imágenes
antes/después idénticas a 1450/900/390 px, incluso con CSP real en las pruebas
de paginación/CSV. `enforced_csp` permite validar otras pantallas sin activar
bloqueo global. Segundo bloque: diccionario sin vista/plantilla anterior,
enlaces obsoletos conservados y capturas vigentes idénticas en tres tamaños.
PNG real en la guía pasa con CSP mediante dos huellas exactas de estilos
estáticos (`CAPTURE_STYLE_HASHES`), sin unsafe-inline. 1686 servidor,
54 Chrome y 498 Node
pasan. Extender CSP a gráficas/ventanas/capturas representativas y continuar
otras referencias. No borrar bases compartidas ni servicios JSON en bloque.
Fase 11 no cerrada.
ACCESS_ENFORCED/Genesis sigue siendo decisión de despliegue. Las frases
«fase 10 parcial» de los bloques históricos siguientes no son el estado actual.

## Bloque previo: inicio especial (26/10/2026)

El inicio especial sin proyecto ya usa `project_entry.startCompatibility`:
filtros API, selección inicial de cuenta/proyecto y carga tras éxito/error.
El puente moderno no llama `initDashboard(true)`; la comparación lo conserva.
475 Node y 30 navegador aprobadas (13 nuevas de compatibilidad). Todavía
faltan carga/presentación especiales antes de retirar script/shim. Ver traspaso.

## Bloque previo: estado de reportes (26/10/2026)

Los cuatro estados de reportes de compatibilidad (cachés AER/IXS, secuencia de
consumos y arranque) pertenecen a `project_state.js`; sus nombres anteriores
son accesores. `project_compatibility.js` lee cuenta/cachés directamente.
474 Node y 27 navegador aprobadas. Fase 10 parcial: faltan proveedores de
inicio/carga y presentación especiales; todavía requiere script/shim.
No repetir este bloque. Ver traspaso y plan para evidencia.

## Estado (24/10/2026)

Migradas (ruta → plantilla de `frontend/templates/pages/`, con la anterior en `?vista=anterior`):

| Pantalla | Ruta | Plantilla |
|---|---|---|
| Operativa | `/operativa/` | `operativa.html` |
| EVA-04 | `/operativa/eva-4/` | `eva4.html` |
| Cuenta | `/cuenta/<slug>/` | `account.html` |
| Margen vendido vs. real | `/ejecutiva/oportunidades/` | `margins.html` |
| Delivery Manager | `/operativa/delivery-manager/<slug>/` | `delivery_manager.html` |
| Diccionario | `/diccionario-datos/` | `dictionary.html` |
| KPIs de DMs | `/operativa/kpis-delivery-managers/` | `kpis_dm.html` |
| Business Overview | `/` | `executive.html` |
| Comercial | `/comercial/` | `commercial.html` |
| Todas las cuentas | `/ejecutiva/cuentas/` | `all_accounts.html` |
| Costos | `/ejecutiva/costos/detalle/?vista=proyectos` | `costs.html` (anterior: `?anterior=1`) |
| Inversión | `/operativa/inversion/` | `investment.html` |
| Capacidad: asignaciones mensuales | `/operativa/capacidad-instalada/` | `capacity.html` |
| Capacidad: detalle diario | `/capacidad-instalada/` | `capacity_daily.html` |
| Facturabilidad | `/operativa/facturabilidad/` | `billability.html` |
| Facturabilidad por especialidad | `/operativa/facturabilidad/especialidad/` | `billability_specialty.html` |
| Facturabilidad por recurso | `/operativa/facturabilidad/recurso/` | `billability_resource.html` |
| Facturabilidad por área | `/operativa/facturabilidad/area/` | `billability_area.html` |
| EVA 1 (con histórico) | `/operativa/eva-1/` | `eva1.html` |
| EVA 2 | `/operativa/eva-2/` | `eva2.html` |
| EVA 3 (con histórico) | `/operativa/eva-3/` | `eva3.html` |
| Proyecto simple | `/proyecto/<id>/` | `project.html` |

**Histórico de los bloques implementados (no pendientes actuales):**

Consulta `docs/estado-traspaso.md` para el punto exacto: Inversión y ambas
pantallas de Capacidad ya se completaron. El detalle diario usa API v1 y
modulos de modelo, vista y controlador, sin `gas_shim.js` en la ruta nueva.
Las cuatro pantallas de Facturabilidad están completadas. Por área usa
API v1 y módulos separados para los cinco apartados; no usa el shim RPC.
EVA 1–3 también están completadas, incluidos los históricos existentes de
EVA 1 y EVA 3. EVA 2 conserva su presentación sin añadirle otro histórico.
Proyecto simple también usa plantilla modular, CSS externo y un módulo para
presentar las barras. Conserva el contexto Python y el alcance por cuenta.
El detalle grande tiene una **entrada transitoria** en `pages/project_detail.html`
y módulos `project_detail/main.js` y `data.js`. La carga inicial y Actualizar
usan API v1 para filtros y dashboards ejecutivo/AER. Ejecutivo AER/T&M ya usa
`sections/aer_executive.js` (DOM seguro y eventos externos) y su modelo de
presentación contrastado contra el anterior. Los estilos AER compartidos están
en `project_detail_aer.css`; el enlace con ID `aer-dashboard-styles` evita
inyectarlos desde el JS anterior. La comparación anterior los sigue inyectando.
Ejecutivo IXB/SaaS/RaaS también usa modelo, vista y controlador en
`sections/ixs_executive*.js`, iconos SVG originales y estilos externos
`project_detail_ixs*.css`. Las lecturas diferidas de RAID, tasks, histórico y
estados de recursos usan API v1, con los mismos servicios y alcance total.
Se comparan todos sus elementos contra la anterior a 1450/900/390 px.
Esfuerzo IXB/SaaS/RaaS también es modular (`sections/ixs_effort*.js`): incluye
actividades, registros, ventanas, fechas, excedidas por persona y CSV. Reutiliza
las lecturas de tasks/recursos y añade `registros/`, con el servicio anterior.
Recursos IXB/SaaS/RaaS también usa modelo, vista y controlador en
`sections/ixs_resources*.js`: tabla, alertas y editor de asignaciones. Reutiliza
las lecturas de recursos/registros; el guardado usa API v1 con CSRF,
`edit_operations` y alcance total, igual que la política RPC anterior.
Planeación IXB/SaaS/RaaS ya consulta vacaciones/compromisos y su panel Azure
por API v1, y guarda/elimina registros por POST con CSRF y alcance total.
Los editores de hitos/actividades y vacaciones también tienen modelo, vista
y controlador en `sections/ixs_planning_editor*.js`, con DOM seguro, eventos
externos y CSS de formulario en `project_detail_ixs_planning.css`. Sus altas,
ediciones y eliminaciones usan API, sin ejecutar los formularios anteriores.
La presentación y las cargas de Planeación son modulares en
`sections/ixs_planning*.js`: indicadores, alertas, calendario, registros de
vacaciones y tabla Azure con filtros locales. El Gantt reutiliza la vista
del Ejecutivo, con marcadores editables; el histórico diferido actualiza la
vista modular. Sus modelos conservan las reglas anteriores, contrastadas
contra las funciones originales. Las escrituras/comentarios de Work Items
usan API v1 con edición, alcance total y CSRF; Planeación tiene controlador
modular y recálculo DOM seguro en `ixs_work_item_actions.js`. Azure DevOps
también usa estos controles y acciones modulares; su edición de fecha no
repinta las alertas de Planeación. La comparación anterior sigue con RPC.
La columna de comentarios de Planeación se conserva oculta por su CSS
original; Azure DevOps sí la muestra. No cambiar esto durante la migración.
Ya son modulares (API v1 + modelo/vista/controlador, con comparación contra la
anterior): el editor de hitos del histórico (`sections/milestones*.js`), la
ventana de comunicados Extensión/Suspensión/Reanudación/Cierre
(`sections/communique*.js`, backend en `apps/gmail`), Gestión RAID completa
(`sections/raid*.js`, lectura y alta) y el aviso de datos faltantes
(`data_notice.js`); proyectos fuera de Proyectos se arman desde MPB/Histórico.
Azure DevOps IXB ya tiene transporte y control de carga en
`sections/ixs_azure{,_model,_loading}.js`, sobre `screens/proyectos/<id>/azure/`
(`forzar=1` para Actualizar Azure). Mantiene el servicio anterior y descarta
respuestas tardías al recargar/cambiar de pestaña/proyecto. Sus agrupaciones por
persona/iteración y etapa, búsqueda y ventanas de detalle ya son modulares en
`sections/ixs_azure_groups{,_model,_view}.js`, comparadas con la anterior a
1450/900/390 px. Indicadores, distribución/salud, atención prioritaria, carga
y próximas fechas también usan modelo/vista en `ixs_azure_summary*.js`, con
DOM seguro y Ver más/menos modular. La pestaña completa usa `ixs_azure_tab*.js`:
estructura, tabla editable, filtros, avances/fechas/demos y comentarios. Reutiliza
la tabla de Planeación con su presentación propia, modelo `ixs_azure_table_model.js`
y acciones protegidas frente a respuestas tardías. No llama a los renderizadores
ni formularios anteriores en esta pestaña; el archivo grande sigue para el resto.
IA IXB tiene fuentes, historial y Drive por API v1 en `project_ai.py` y
`sections/ixs_ai_sources.js`, con tres CSS externos y comparación visual.
Contexto, snapshot, comparación entre cortes y capacidad ya están separados
en `sections/ixs_ai_model.js`, conservando las fórmulas anteriores.
La vista completa usa DOM seguro y eventos externos en `ixs_ai_view.js`,
`ixs_ai_panels_view.js` e `ixs_ai_controller.js`: indicadores, recomendaciones,
evidencias, preguntas, reportes, minutas y Drive. Sus acciones usan API v1 con
permisos originales y CSRF; la creación RAID reutiliza el módulo ya migrado.
La ruta nueva no ejecuta los renderizadores ni formularios anteriores de IA.
Se conservan wrappers de entrada/estado y comparación. Ver evidencia en el traspaso.

Cliente está migrado para AER/T&M e IXB/SaaS/RaaS en `client{,_model,_view}.js`,
con sus filtros, exportación y editores por API v1. El Centro de Comunicación
IXB/SaaS/RaaS usa `bee_com{,_model,_view}.js` y API v1. Confirmado en código y
en 94 pruebas de navegador durante la revisión posterior a Claude.
La carga compartida Cliente/Acciones IXB conserva caché en `ixs_client_actions.js`.

Acciones está migrada en ambas familias: `actions_model.js` separa los datos
derivados; `actions.js` hace las lecturas/guardados/borrados/edición directa y
pendientes Beecker/Cliente por API v1 (`project_actions.py`). `actions_view.js`
presenta las dos tablas, búsqueda y formularios con DOM seguro y eventos
externos. La ruta activa no ejecuta sus renderizadores/formularios anteriores;
conserva los puentes de entrada/estado y el fallback para comparar.

**La fase 10 continúa parcial.** Falta completar la integración compartida y
retirar las dependencias activas del archivo anterior; ver inventario en el plan.
Planeación AER ya guarda actividades/hitos, estados/cierres, vacaciones,
importaciones y borrados individuales/por lote por API v1 en
`project_aer_planning.py` y `sections/aer_planning.js`. Conserva las firmas y
los servicios anteriores. Sus formularios de actividades/hitos, vacaciones e
importación ya usan DOM seguro/eventos externos (`aer_planning_forms.js`).
Recursos, ocupación, capacidad y parser de importación usan el modelo puro
`aer_planning_model.js`, contrastado con el anterior. Indicadores, fechas y
agrupaciones del Gantt también están en ese modelo. La vista principal usa
`aer_planning_view.js`, `aer_planning_timeline.js` y `aer_planning_tables.js`
con DOM seguro y eventos externos, sin ejecutar `_aerVistaPlaneacion`.
Planeación AER está migrada: `aer_planning_controls.js`,
`aer_planning_filters_model.js` y `aer_planning_filter_view.js` ya manejan
búsqueda/filtros, selección y rango con DOM seguro/eventos externos. Los puentes
solo conservan el enlace al estado y ciclo de vida compartidos; la ruta activa
no ejecuta los auxiliares anteriores de estos controles. Ver pruebas en el plan.
Esfuerzo AER está migrado en `aer_effort{,_model,_view}.js`: indicadores,
gráficas, consumo por recurso, rango de registros y ventana «Ver más» con DOM
seguro/eventos externos. Consulta `aer/registros/` por API v1, con el mismo
servicio de Clockify; no cambia cifras ni el alcance del filtro (solo registros).
Las respuestas antiguas no reemplazan otra consulta/proyecto. Conserva enlace al
estado y ciclo de vida compartidos; sin ejecutar su renderer/ventana anteriores.
Riesgos AER está migrado en `aer_risks{,_model,_view}.js`: indicadores,
matriz, distribución, atención, seguimiento y editor con DOM seguro/eventos
externos. Lectura, guardado, borrado y limpieza de duplicados usan API v1 en
`project_aer_risks.py`, con los servicios y permisos anteriores. Reutiliza el
editor modular de Acciones. Conserva la agrupación por título anterior (incluye
el caso de responsables/fechas distintos documentado en el traspaso).
Recursos AER está migrado en `aer_resources{,_model,_view}.js`: evaluaciones,
selección, indicadores, gráfica/historial, distribución y formularios con DOM
seguro/eventos externos. Guardado/borrado usan API `project_aer_resources.py`,
con firmas y servicios anteriores; la lectura llega en el dashboard AER existente.
Conserva últimas evaluaciones globales del proyecto en la gráfica y selección
por persona solo en su resumen. No ejecuta su renderer/formulario anteriores.
IA AER tiene lecturas y acciones separadas: `project_aer_ai.py` expone seis
lecturas (incluido el prompt) y ocho POST por API v1, con servicios/permisos
anteriores; configuración requiere manage_integrations, generación/guardado
edit_operations, siempre alcance total y CSRF en escrituras.
`aer_ai_sources.js` conserva caché/estados y descarta respuestas de otro estado
o proyecto; refrescar el mismo proyecto no deja cargas bloqueadas.
`aer_ai_model.js` conserva contexto y hechos/alertas (límite de 28 compromisos
en el contexto y esfuerzo de 6 puntos). Su CSS principal está externo en
`project_detail_aer_ai.css`, con comparación visual en tres tamaños.
La presentación de IA AER ya usa `aer_ai_presentation.js`, `aer_ai_view.js`,
`aer_ai_documents_view.js`, `aer_ai_forms_view.js` y DOM seguro en `aer_ai_dom.js`.
`aer_ai_presentation_model.js` conserva formato mínimo, extractos y datos
derivados. Pantalla, lecturas, seis formularios y borrador editable comparados
en tres tamaños. Historial, selección (máximo 5) y preguntas sugeridas usan
eventos externos; no ejecuta renderer, tablas ni formularios anteriores.
`aer_ai_actions.js` y `aer_ai_minutes_actions.js` controlan análisis, preguntas,
correo, resumen, borradores con/sin Drive, guardado, configuración, prompt y
copiado. `aer_ai_actions_model.js` conserva clasificación de preguntas y límite
de selección. No ejecuta acciones RPC anteriores en la ruta nueva. Respuestas
de otro proyecto/estado/formulario no sobrescriben su presentación nueva.
**IA AER completa; fase 10 parcial.** Los encabezados, pestañas y refresco
AER/IXS ya usan `project_shell{,_model,_view}.js`: DOM seguro, eventos externos,
iconos/estilos originales y comparación en tres tamaños. AER conserva la
pestaña capturada al actualizar; IXS vuelve a Ejecutivo e invalida Cliente/Acciones,
como antes. La navegación AER mantiene el alias minutas→IA y las cargas originales.
Las respuestas superadas o de otra familia/carga no reemplazan la pantalla.
El montaje AER/IXS ya usa `project_tabs.js` y `project_tabs_view.js`: selecciona
los módulos existentes, conserva contextos diferidos, lifecycle, estados de
Planeación/Azure y precarga de recursos. Cliente/Acciones mantiene el presentador
compartido y la caché IXS. Los respaldos de pestaña desconocida se comparan con
la anterior. `projectTabsContext` sigue como adaptador de callbacks anteriores.
La inicialización AER/IXS, apertura IA IXS y enlace Cliente/Acciones usan
`project_session{,_model,_view}.js`: conservan estados del mismo proyecto,
reinicios al cambiar de ID, caché, orden de cargas y actualización diferida del
histórico por API. Los errores y aviso de backend mantienen su presentación.
`project_state.js` ya posee los doce valores centrales: dashboards/pestañas,
IA, Clockify, metadata, secuencia, hitos/ID y caché Cliente/Acciones.
Se registra antes del script anterior. Los nombres previos son accesores
temporales; el caché conserva la misma referencia. La comparación sigue con
sus valores originales. `projectSessionContext` aún suministra callbacks.
También posee los siete estados de paneles activos identificados: rango/filtros
de Planeación, registros Clockify y selección de Recursos AER, Planeación IXS,
Planeación Azure y Azure. `project_panels.js` construye contextos de Planeación,
Esfuerzo y Recursos AER con el mismo snapshot/lifecycle, sin cambiar callbacks.
Las tres funciones de contexto anteriores delegan; los avisos/guardado comunes
y los otros contextos se inyectan todavía desde entradas de compatibilidad.
La lógica de avisos/guardado ya usa `project_feedback.js`: toast, botón en
guardado/restauración tras error, selección de botón principal y cierre normal/
ancho. Conserva mensajes y tiempos. El texto entra como texto y la restauración
reutiliza los nodos originales; las funciones previas solo delegan.
La entrada de proyectos usa `project_entry{,_model,_view}.js`: montaje desde
template, filtros/selección, clasificación por servicio, carga API, secuencia
de respuestas y reintento. `showError` delega a una vista segura que conserva
el reemplazo de toda la pantalla. Se comparan cargas/errores en tres tamaños.
`project_contexts.js` ya construye los cuatro contratos de entrada, sesión,
shell y montaje desde el almacén: metadata/secuencia, getters/setters, guardias,
caché, sincronización Azure y editor de Planeación. Los cuatro nombres anteriores
solo suministran callbacks de compatibilidad. `project_feature_contexts.js`
construye los contratos de Acciones compartidas, Riesgos y fuentes/presentación/
acciones IA AER. Conserva familia, caché de pendientes y guardias distintas de
fuentes/formularios; IA IXS reutiliza su guardia de estado/proyecto en cuatro
entradas. Los callbacks de UI/servicios todavía se inyectan desde compatibilidad.
`project_ixs_adapters.js` ya compone los datos IA (contexto/snapshot/cambios/
capacidad) importando los modelos existentes, carga fuentes/historial/Drive y
construye acciones IA con el mismo paso a RAID. El soporte de Planeación usa
estado modular y abre hitos directamente con `beeProjectMilestones`, conservando
índice/fecha/observación y callback de recarga. Las entradas previas solo delegan;
todavía falta cerrar el arranque y los callbacks restantes.
`project_ixs_runtime.js` ya coordina montaje/dispatch, selección/refresco, IA y
Cliente/Acciones IXS directamente entre controladores. `project_ixs_adapters`
también pinta IA con su vista modular y sus mismas guardias. Las entradas IXS
previas delegan; los eventos creados por esta coordinación no vuelven a esos
renderizadores. `project_aer_runtime.js` también coordina AER directamente:
montaje, pestañas, refresco, contextos de paneles/formularios, IA y Comunicados.
Conserva pestaña al refrescar, alias minutas→IA y orden de sus cinco cargas.
Cliente/Acciones IXS recibe los contextos AER desde este coordinador, sin
`projectTabsContext`. Las entradas AER anteriores solo delegan en esa ruta.
`project_ixs_tools.js` conecta editores de Planeación y Comunicados con sus
controladores, mismo estado/lifecycle, UID y fechas sugeridas. El runtime IXS
usa estos enlaces directamente; estilos AER/IXS/IA ya están enlazados en la
plantilla nueva y no usa los inyectores anteriores. `ixsRuntimeBindings` aún
proporciona vista anterior y recarga. El creador modular RAID se comparte entre
su pestaña e IA: `project_ixs_tools.js` abre/formatea manualmente la recomendación
con `beeIxsRaidCreator`, sin las entradas anteriores. Conserva texto, tipo,
guardia por ID y recarga del registro tras crear; no publica automáticamente.
`project_entry_runtime.js` compone el contexto de entrada/recarga con renderers
AER/IXS/genérico directos y el almacén; conserva callbacks para sin proyecto/
cuenta y cambio de cliente. La recarga de hitos en Planeación IXS
usa ese controlador directamente, sin `loadDashboard`/`projectEntryContext`.
Los contextos AER compartidos también llegan directamente desde su runtime.
Se retira `ixsRuntimeBindings` y la conexión previa IXS. El enlace `previous`
ya usa el controlador modular `project_previous.js` y el genérico migrado.
Faltan auditar los contratos de compatibilidad sin proyecto y el arranque
independiente. No retirar todavía script/shim.
El primer bloque genérico separa fechas, fases fusionadas, suspensiones,
asignación de marcadores, resumen y detección de cierre en
`generic_timeline_model.js`. El renderer de compatibilidad consume ese modelo
cuando existe; conserva el cálculo original como fallback. La comparación
incremental modelo/fallback usa la misma plantilla nueva; los bloques siguientes
comparan la presentación y estructura contra `?vista=anterior`.
Su línea de tiempo ya usa `generic_timeline_view.js` y CSS externo
`project_detail_generic_timeline.css`: barras, estados, marcadores, eje y leyenda
con DOM seguro. El componente reemplaza un marcador estático del renderer
transitorio; no ejecuta la construcción HTML anterior de la línea de tiempo.
La estructura posterior conserva también los tamaños originales de botones.
La tabla de carga por recurso y el resumen de hitos también usan DOM seguro
en `generic_panels_view.js`, modelo de presentación `generic_panels_model.js`
y CSS externo `project_detail_generic_panels.css`. Conservan filas/totales,
redondeo, estados, fechas, observaciones y orden. Mantienen los IDs de tarjeta
y rango Clockify. La ruta nueva no construye su HTML anterior; el renderer
transitorio queda como respaldo de comparación.
Encabezado y seis KPIs genéricos usan `generic_header_model.js`,
`generic_header_view.js` y CSS externo `project_detail_generic_header.css`.
Conservan defaults, umbral de ritmo, etiquetas de cierre, presupuesto, fecha
PRD/estimada e ID financiero. La gráfica circular pequeña se crea con SVG DOM;
no se ejecuta su helper HTML anterior en esa ruta. Los flags de estado/cierre
ya llegan del modelo genérico modular, con las mismas reglas anteriores.
Las gráficas de distribución por área y horas por recurso/rol usan
`generic_charts_model.js`, `generic_charts_view.js`, `generic_charts.js` y CSS
externo. SVG/textos seguros, paleta, redondeo, orden, escala de lista completa
y cinco filas iniciales conservados. «Ver todos/menos» usa eventos externos
locales sin lecturas adicionales. Los helpers anteriores quedan para otras
rutas/comparación, pero no se ejecutan para estas gráficas en la ruta nueva.
El rango Discovery→Deployment de Clockify usa `project_clockify_range.js`
y API v1 `screens/proyectos/<id>/clockify-rango/`, con el mismo resolver,
permiso y alcance total. Conserva carga, texto, fechas locales y vacío ante
fallos; ignora respuestas superadas o de un nodo reemplazado. El helper
anterior solo delega en la ruta nueva y conserva RPC para la comparación.
RAID/tasks genéricos ya usan `generic_sources{,_model,_view}.js`, CSS externo
y sus APIs v1 existentes (mismos servicios/permisos). Conservan totales del
servidor, filas/duplicados, orden, inversión, rango, tareas sin horas y errores.
Los dos helpers anteriores solo delegan en la ruta nueva; el respaldo RPC
permanece para comparar. Texto con DOM seguro; respuestas superadas o nodos
reemplazados no sobrescriben los paneles/totales vigentes.
El alta manual de riesgos usa `generic_risk{,_model,_view}.js`, CSS externo y
POST API v1 `riesgos-manuales/`. Conserva `write_rpc.add_risk` (hojas Riesgos/
Histórico y caché, sin crear otro registro Azure), validación, campos y mensajes;
`edit_operations`, alcance total y CSRF. La recarga usa el runtime modular.
Los tres helpers anteriores solo delegan; una respuesta de una ventana cerrada
o de otro proyecto no cierra/reemplaza la nueva. No reabrir este formulario.
La estructura de tarjetas y controles usa `generic_layout_view.js` y CSS
externo `project_detail_generic_layout.css`: montaje DOM seguro, IDs/grillas,
cargas y resumen RAID originales. Agregar Hito/Riesgo usa eventos externos
y sus controladores migrados; guardar hito recarga por el runtime modular.
`generic_executive_model.js` conserva detección de cierre, flags de riesgo/color,
servicio/fecha PRD y resumen temporal. `generic_executive.js` coordina estado,
montaje y fuentes directamente. Conserva las dos asignaciones originales al
proyecto completado; error/datos faltantes usan DOM seguro con el mismo texto.
`project_entry_runtime.js` llama al genérico modular en servicios no AER/IXS;
no ejecuta el renderer ni auxiliares anteriores de este Ejecutivo. El nombre
anterior delega si están sus módulos; el cuerpo original sigue para comparar.
`project_previous.js` también maneja IXS→genérico→IXS, con el mismo control,
guardia por ID, pestaña resumen y montaje sin recarga. Sus dos nombres
anteriores solo delegan en la ruta nueva; no reabrir este enlace.
Auditoría: `proyectos/<str:project_id>/` siempre recibe ID y lo siembra en
`project_context`; `projectParams` le da prioridad frente al query. Cuenta usa
su ruta/plantilla modular separada. Se conserva la compatibilidad de casos
especiales (`previousStart`, `previousLoad`, `clientChanged`) mediante
`projectCompatibilityBindings`. La coordinación está en `project_compatibility.js`:
conserva selección, refresco, segunda comprobación de cuenta y lectura actual
de cachés antes de pintar reportes/riesgos. El script anterior solo suministra
proveedores explícitos; aún deben sustituirse para retirar su carga. El arranque
ya lo hace main: carga definiciones con `data-project-bootstrap=manual`, conecta
el puente y llama `beeProjectEntry.mount`, sin renderView/projectEntryContext/
initDashboard. La comparación anterior conserva autoinicio. El cargador
`project_script_loader.js` reutiliza scripts evaluados y reintenta descargas
fallidas, evitando redeclarar globals al recuperar un fallo de inicialización.
Fase 10 parcial: auditar dependencias/contratos activos y sustituir los que aún
obligan a cargar el archivo/shim; no llamarlo arranque totalmente independiente.
No retirar script/shim ni reabrir vistas/formularios ya migrados.
Mantener los puentes y comparación;
no retirar aún script/shim. El manejador común showError puede reemplazar el
dashboard ante errores; comportamiento preservado en el módulo nuevo.
Planeación IXB usa módulos de vista/carga/editores. Sus auxiliares de estados
de recursos, edición de hitos y fechas sugeridas también usan `ixs_support.js`
y `ixs_support_model.js`. Conservan caché por proyecto, normalización de nombres,
guardia de identidad, índice del hito y reglas de fechas anteriores.
`ixsSupportContext` suministra recarga al adaptador modular; los tres nombres
anteriores solo delegan en la ruta nueva. Quedan contextos/adaptadores y
compatibilidad genérica antes de retirar el shim. No reabrir Cliente ni el
Centro de Comunicación como pendientes.

1. Detalle del proyecto: fase 10 completada el 26/10, con arranque independiente y pestañas modulares, sin script/shim/RPC en la ruta nueva. No reabrir las pestañas como pendientes. Los originales se conservan para comparar hasta la fase 11.
2. Limpieza final: borrar plantillas, CSS y JS anteriores (`apps/portal/templates/portal/`, `apps/portal/static/portal/`), las pruebas que usan `?vista=anterior` y las pruebas de node del JS anterior; luego CSP obligatoria (hoy no hay política por defecto).
3. Genesis / `ACCESS_ENFORCED`: decisión de despliegue, no de código.

## Estructura

- `frontend/templates/layouts/` (`base.html` con el importmap `#app/...`, `app.html` con la barra superior y el bloque `freshness`), `partials/`, `pages/`.
- `frontend/static/styles/`: `tokens.css`, `base.css`, `layout.css`, `components.css`, `a11y.css` y `pages/*.css` (una hoja por pantalla; `ds.css`, `legacy-base.css`, `portal-controls.css`, `portal-loading.css`, `agreements.css`, `period-picker.css` son compartidas con el diseño anterior).
- `frontend/static/scripts/`: `data/` (cliente de la API), `lib/`, `ui/` (componentes reutilizables), `pages/<pantalla>/main.js` + `sections/`.
- Todo módulo compartido (fuera de `pages/`) **debe estar en el importmap** de `layouts/base.html` (hay una prueba que lo exige).
- `apps/portal/pages.py`: vistas de las páginas nuevas. `apps/portal/views.py`: vistas anteriores, que siguen calculando el contexto. `apps/portal/api/`: API v1 (`{data, meta}`).
- Colores en `styles/*.css` solo por variables de `tokens.css` (los de `pages/` pueden ser literales). Sin `style=""` ni scripts en línea en las plantillas nuevas (preparación de CSP).

## Receta por pantalla

1. **Plantilla.** Hay dos caminos:
   - *Datos por API* (si existe `screens/...`): el JS pide los datos con `apiGet` y pinta con `el()` de `lib/dom.js` (nunca `innerHTML` con datos).
   - *Plantilla modular con la vista de siempre* (Comercial, Todas las cuentas, Costos): `pages._modern(request, views.<vista>, "pages/<x>.html")` fija `request.portal_template`; la vista anterior usa `render_page(...)` en lugar de `render(...)`. Así las cifras no cambian.
2. **Herramientas** en `tools/migracion/` (ejecútalas desde la raíz; ajusta rutas `shots_tmp/` → `tools/migracion/` si hace falta):
   - `migrate_page.py <legacy.html> <nombre> <body_class> [hoja.css…]` arma la plantilla, la hoja (sin reglas de la barra superior) y guarda los scripts en línea para portarlos a mano.
   - `inline2css.py` pasa `style=""` a clases `.x.x` (misma fuerza que el estilo en línea). Los estilos con `{{ }}` hay que resolverlos a mano (por ejemplo con `data-width` y JS).
   - `scope_css.py` prefija reglas con una clase si la hoja anterior tiene reglas globales.
3. **Ruta.** En `apps/portal/pages.py` agrega la vista con `?vista=anterior` (usa `anterior_disponible()`; vence el 3/11/2026) y cambia `apps/portal/urls.py`.
4. **Comparar contra la anterior** con los mismos datos de prueba (`tools/migracion/test_zz_seq.py` y `test_zz_pages.py`; cópialos a `tests/e2e/` mientras los uses y no los comitees). Compara estilos calculados y cajas con `diff.py`, y capturas. Fugas típicas a corregir en la hoja de la pantalla:
   - `box-sizing`: la pantalla anterior no usaba `border-box` (`base.css` ya lo excluye bajo `body.ds`).
   - `th`/`td`/`.card`/`.note` de `components.css` agregan estilos que la anterior no tenía.
   - `.page` de `layout.css` suma relleno: neutralízalo con `body.<clase> main.page { max-width: none; padding: 0; }` y `body #main-content { margin-left: 0 !important }` (ya está en `legacy-base.css`).
   - Pantallas con captura (Business Overview, Operativa, Comercial) montan `mountPageCapture` en `.fresh`.
5. **Pruebas.** Una prueba e2e por pantalla en `tests/e2e/test_<x>.py` (estructura, filtros, navegación de regreso, error con reintento, alcance limitado). Las pruebas que leían el HTML anterior piden `?vista=anterior` y parchean `apps.portal.pages.anterior_disponible`.
6. **Plan y commit.** Actualiza el plan con evidencia y haz un commit por pantalla.

## Cómo probar (Windows, Git Bash)

```bash
export MSYS_NO_PATHCONV=1
.venv/Scripts/python -m pytest tests/portal tests/core tests/access tests/e2e -q --no-cov
.venv/Scripts/ruff check apps tests && .venv/Scripts/ruff format apps tests
.venv/Scripts/mypy apps/portal/pages.py
node --test tests/frontend/*.test.*
```

- Las pruebas e2e usan Playwright con la red bloqueada; el fixture `datos` de `tests/e2e/conftest.py` pone datos de ejemplo.
- Los tres fallos Node anteriores se corrigieron en sus pruebas: parser de scripts de Costos y expectativas comerciales desactualizadas (`executive_report`, `financial`). Backend y frontend actual ya publican importes/notas del corte. No volver a forzarlos a Pendiente ni cambiar cálculos; la suite vuelve a pasar completa.
- Al escribir archivos largos con comandos de shell, evita heredocs con comillas simples; usa el editor de archivos.

## Cuidado

- `vista=` ya significa otra cosa en Costos (`proyectos`): allí la pantalla anterior se pide con `?anterior=1`.
- Cualquier `?bloque=consumos` o JSON que antes devolvía la vista de la cuenta ahora lo da la API; no lo restaures.
- No hay `ACCESS_ENFORCED` por defecto: las pruebas con permisos usan los fixtures `enforced` y `DictProvider`.
