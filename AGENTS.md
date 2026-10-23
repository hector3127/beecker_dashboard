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
modular y recálculo DOM seguro en `ixs_work_item_actions.js`. La pestaña Azure
todavía conserva su vista/controlador anterior, pero estas dos escrituras
usan la API mediante `workItemCall`; la comparación anterior sigue con RPC.
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
respuestas tardías al recargar/cambiar de pestaña/proyecto. La presentación,
agrupaciones, filtros y acciones de la pestaña todavía usan el script anterior.
**Planeación y la fase 10 continúan parciales.** Siguiente: presentación y
acciones de Azure DevOps; después IA, Cliente/Acciones (comparten renderer con AER) y Comunicación de
IXS; en AER faltan todas las pestañas salvo Ejecutivo. También falta separar
encabezados y navegación compartida, y retirar el shim de la ruta nueva.

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
