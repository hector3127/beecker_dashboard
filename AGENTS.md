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

**Pendiente, en este orden:**

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

**La fase 10 continúa parcial.** En IXB/SaaS/RaaS falta la estructura compartida.
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
la anterior. `projectTabsContext` sigue como adaptador a los globals/contextos.
Continuar por inicialización de proyectos y estado compartido, después auxiliares;
`renderDashboard…`, el inicializador IA IXS y carga compartida aún tienen puentes
en el archivo anterior. No reabrir vistas/formularios como pendientes.
Mantener los puentes y comparación;
no retirar aún script/shim. El manejador común showError sigue anterior y
puede reemplazar el dashboard ante errores; comportamiento preservado.
Planeación IXB usa módulos de
vista/carga/editores; todavía conserva puentes de estado y auxiliares como
`ixsEditarHitoTimeline`, `_ixsCargarEstadosRecursos` y `_ixeAuto` en el archivo
anterior. Extraerlos junto con entrada/estado/montaje compartidos antes
de retirar el shim. No reabrir Cliente ni el Centro de Comunicación como pendientes.

1. Detalle del proyecto (`proyectos/<id>/`, `proyecto_detalle.js` ≈ 1 MB y `gas_shim.js`): continuar por pestaña y sustituir gradualmente las llamadas a `/api/rpc/`. No duplicar el megabyte en `frontend/` ni dar por migradas las pestañas por tener una entrada nueva.
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
- Hay 3 fallos de node anteriores a esta migración (`executive_report`, `executive_numbers`/commercial y `cost_sprint_details`): son del JS anterior y se retiran en la limpieza.
- Al escribir archivos largos con comandos de shell, evita heredocs con comillas simples; usa el editor de archivos.

## Cuidado

- `vista=` ya significa otra cosa en Costos (`proyectos`): allí la pantalla anterior se pide con `?anterior=1`.
- Cualquier `?bloque=consumos` o JSON que antes devolvía la vista de la cuenta ahora lo da la API; no lo restaures.
- No hay `ACCESS_ENFORCED` por defecto: las pruebas con permisos usan los fixtures `enforced` y `DictProvider`.
