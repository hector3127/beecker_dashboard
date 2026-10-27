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

## Estado vigente (27/10/2026)

**Fase 10 completada; fase 11 abierta.** Este apartado sustituye los estados
históricos del plan y del traspaso. No reabrir pantallas migradas ni restaurar
presentaciones retiradas. Leer primero el bloque vigente de ambos documentos.

### Git y piloto de congelación

- Base publicada: `a370589`; main ya incluye la actualización documental
  `1c37925` y el piloto integrado en `2e580ec`, con nuevos cambios locales de
  congelación. Comprobar Git al comenzar; no hacer push sin petición expresa.
- Rama local existente `congelar-referencias`: `4103ed6`, un commit sobre main.
  Primer caso: `tests/frontend/aer_executive.test.mjs` compara contra
  `tests/frontend/frozen/aer_executive.json`; el generador está en
  `tests/frontend/frozen/gen/aer_executive.gen.mjs`. **Integrado en main**
  mediante cherry-pick `2e580ec`; la rama local se conserva intacta y no
  figura publicada. No volver a aplicar ese commit ni repetir el piloto.
- El bloque siguiente congela aer_ai_actions_model, aer_planning_filters y
  generic_header: 26 pruebas en los cuatro archivos y 472 Node completas
  aprobadas. Cuatro alteraciones deliberadas en copias temporales fueron
  detectadas. Generadores reproducibles normalizando CRLF/LF, sin cambiar
  valores JSON. Ver `docs/congelacion-referencias.md`.
- Último bloque sobre `7d59edf`: client_model, project_entry_model,
  ixs_work_items y project_session_model ya no leen el original. Sus 22
  dirigidas y 472 Node completas pasan; cuatro mutaciones en copias se
  detectan. Cuatro JSON originales reproducibles normalizando CRLF/LF.
  Ocho archivos congelados en total; no se modifica código de aplicación.

### Aplicación y seguridad

- Todas las páginas activas usan `frontend/`. Se retiraron los directorios
  `apps/portal/templates/portal/` y `apps/portal/static/portal/`.
- La referencia del detalle anterior vive en `tests/reference/`, solo para
  pruebas; `?vista=anterior` no selecciona una página anterior en producción.
  `_modern`, `anterior_disponible` y `ANTERIOR_HASTA` ya no existen.
- `/api/rpc/` ya no se publica en `config.urls`. El shim se movió a
  `tests/reference/static/core/js/gas_shim.js`; solo lo sirven las pruebas.
- **CSP obligatoria por defecto**: `CSP_ENFORCE=True`, nonce por petición y
  dos hashes exactos de estilos de captura, sin unsafe-inline/unsafe-eval.
  Para solo reportar se necesitan **CSP_ENFORCE=0 y CSP_REPORT_ONLY=1** juntos.
  No cambiar esta política como parte de congelar ni activar ACCESS_ENFORCED.
- `tests/conftest.py` activa `reference_site` automáticamente. La suite normal
  puede montar RPC y detalle anterior; verificar también rutas reales
  `config.urls`, sin directorios de referencia y con CSP activa.
- Conservar `views.ejecutiva`, `views.comercial`/`comercial_response`,
  `dm_state`/`dm_rows` y servicios de caché: los usan la API o la precarga.
  **No borrar core/rpc en bloque:** `warm_cache` usa `get_rpc_function` y
  varios módulos usan `register_rpc`. Separar transporte/política de pruebas
  del registro interno antes de decidir su retiro.

### Auditoría independiente sobre main a370589

27/10: **1759 servidor, 472 Node y 61 Chrome con rutas reales/CSP aprobadas**;
además, una prueba de preview de logos aprobada por separado en su preparación
Report-Only. Los 61 casos incluyen las cinco familias de proyecto/pestañas,
Cuenta, Costos, Comercial, PNG y logos. No es una corrida completa de e2e.
Ruff (excluyendo temporales ajenos), mypy de pages.py, `manage.py check` y
`collectstatic --dry-run` aprobados. La primera ejecución del adaptador de
auditoría falló por interpretar un directorio estático con prefijo como Path;
se corrigió solo el adaptador temporal y se repitió satisfactoriamente.

Comandos, límites y hallazgos: `docs/auditoria-fase11-2026-10-27.md`.
No usar los antiguos recuentos «11 HTML/29 estáticos» como estado actual.

### Limpieza y archivos locales

`a370589` retiró 56 maquetas de `design/` y archivó notas sueltas en
`docs/archivo/`, sin modificar la aplicación. Claude reportó limpieza local
de temporales/cachés; esa eliminación no se puede verificar mediante Git.
No borrar `tmp/backups/`, CSV de datos, `.cache`, `graphify-out`, SQLite,
`.env` ni `key.json` como si fueran residuos de la migración.

No tocar ni comitear cambios ajenos en `tools/migracion/inline2css.py`,
`migrate_css.py`, `migrate_page.py`, `shots_tmp/` o `tests/e2e/test_zz_*.py`.
Agregar archivos por nombre. `docs/` contiene decisiones y evidencia; no
eliminar documentos por antigüedad. Retirar solo duplicados sustituidos y
comprobar sus enlaces. El prompt de continuación antiguo se retiró: estas
instrucciones y `docs/estado-traspaso.md` son la entrada vigente.

### Siguiente bloque, en orden

1. Piloto ya integrado: no rehacerlo ni cambiar de rama con cambios ajenos.
   Continuar por modelos Node sencillos y después intermedios/complejos;
   el desarrollo normal sigue directo en main.
2. Congelar progresivamente las comparaciones Node y de navegador con
   resultados obtenidos del **original**, nunca del modelo que se comprueba.
   En main, 33 archivos Node aún leen el script anterior (41 al comenzar). El piloto de
   navegador sigue pendiente. Preservar entradas, casos límite y cobertura;
   comprobar que las pruebas detectan una alteración deliberada y restaurarla.
3. Solo después retirar referencias/generadores y transporte de pruebas que
   ya no tengan consumidores. Mantener el registro/servicios internos usados.
4. Mantener pruebas permanentes con rutas de producción y CSP; ejecutar
   regresión final y documentar evidencia antes de cerrar fase 11.
5. Genesis y activación de accesos requieren configuración de despliegue;
   no son una razón para alterar cálculos o habilitar ACCESS_ENFORCED.


## Estructura

- `frontend/templates/layouts/` (`base.html` con el importmap `#app/...`, `app.html` con la barra superior y el bloque `freshness`), `partials/`, `pages/`.
- `frontend/static/styles/`: `tokens.css`, `base.css`, `layout.css`, `components.css`, `a11y.css` y `pages/*.css` (una hoja por pantalla; `ds.css`, `legacy-base.css`, `portal-controls.css`, `portal-loading.css`, `agreements.css`, `period-picker.css` son compartidas con el diseño anterior).
- `frontend/static/scripts/`: `data/` (cliente de la API), `lib/`, `ui/` (componentes reutilizables), `pages/<pantalla>/main.js` + `sections/`.
- Todo módulo compartido (fuera de `pages/`) **debe estar en el importmap** de `layouts/base.html` (hay una prueba que lo exige).
- `apps/portal/pages.py`: vistas de las páginas nuevas. `apps/portal/views.py`: servicios de contexto y entradas conservadas para API/precarga. `apps/portal/api/`: API v1 (`{data, meta}`).
- Colores en `styles/*.css` solo por variables de `tokens.css` (los de `pages/` pueden ser literales). Sin `style=""` ni scripts ejecutables en línea; el importmap del layout lleva nonce y CSP ya bloquea por defecto.

## Receta por pantalla

1. **Plantilla.** Hay dos caminos:
   - *Datos por API* (si existe `screens/...`): el JS pide los datos con `apiGet` y pinta con `el()` de `lib/dom.js` (nunca `innerHTML` con datos).
   - *Contexto Python conservado*: `_current` fija `request.portal_template` para vistas que usan `render_page`. Comercial usa `comercial_response` con su plantilla vigente explícita. No restaurar `_modern` ni cambiar servicios/cálculos para simplificar esta capa.
2. **Herramientas** en `tools/migracion/` (ejecútalas desde la raíz; ajusta rutas `shots_tmp/` → `tools/migracion/` si hace falta):
   - `migrate_page.py <legacy.html> <nombre> <body_class> [hoja.css…]` arma la plantilla, la hoja (sin reglas de la barra superior) y guarda los scripts en línea para portarlos a mano.
   - `inline2css.py` pasa `style=""` a clases `.x.x` (misma fuerza que el estilo en línea). Los estilos con `{{ }}` hay que resolverlos a mano (por ejemplo con `data-width` y JS).
   - `scope_css.py` prefija reglas con una clase si la hoja anterior tiene reglas globales.
3. **Ruta.** Las rutas de `apps/portal/pages.py` ya sirven frontend; no restaurar bifurcaciones de comparación en producción. La referencia antigua se monta solo desde pruebas.
4. **Comparaciones.** El detalle anterior se conserva solo en tests/reference; las otras pantallas tienen referencias guardadas. Congelar con los mismos datos y comprobar cajas, estilos, cifras e interacciones. No regenerar esperados desde la implementación nueva para hacer pasar una diferencia. Los scripts locales test_zz/diff.py son auxiliares y no se comitean. Fugas visuales históricas:
   - `box-sizing`: la pantalla anterior no usaba `border-box` (`base.css` ya lo excluye bajo `body.ds`).
   - `th`/`td`/`.card`/`.note` de `components.css` agregan estilos que la anterior no tenía.
   - `.page` de `layout.css` suma relleno: neutralízalo con `body.<clase> main.page { max-width: none; padding: 0; }` y `body #main-content { margin-left: 0 !important }` (ya está en `legacy-base.css`).
   - Pantallas con captura (Business Overview, Operativa, Comercial) montan `mountPageCapture` en `.fresh`.
5. **Pruebas.** Conservar estructura, filtros, regreso, error/reintento y alcance limitado. Las comparaciones del detalle anterior usan `tests/reference` hasta congelarlas; no parchear funciones retiradas. Validar también rutas reales y CSP, sin reference_site.
6. **Plan y commit.** Actualiza el plan con evidencia y haz un commit por pantalla.

## Cómo probar (Windows, Git Bash)

```bash
export MSYS_NO_PATHCONV=1
.venv/Scripts/python -m pytest tests/portal tests/core tests/access tests/e2e -q --no-cov
.venv/Scripts/ruff check apps core config tests --exclude 'test_zz_*.py'
.venv/Scripts/ruff format --check apps tests
.venv/Scripts/mypy apps/portal/pages.py
node --test tests/frontend/*.test.*
```

- Las pruebas e2e usan Playwright con la red bloqueada; el fixture `datos` de `tests/e2e/conftest.py` pone datos de ejemplo.
- No correr dos procesos pytest con base de pruebas simultáneamente. Aplicar formato solo a archivos propios; no reformatear temporales ajenos. No afirmar una suite completa por sumar corridas con alcances distintos.
- Al escribir archivos largos con comandos de shell, evita heredocs con comillas simples; usa el editor de archivos.

## Cuidado

- `vista=` en Costos elige proyectos/márgenes. `?anterior=1` es un enlace obsoleto que debe seguir mostrando la pantalla vigente, no restaurar la plantilla retirada.
- Cualquier `?bloque=consumos` o JSON que antes devolvía la vista de la cuenta ahora lo da la API; no lo restaures.
- No hay `ACCESS_ENFORCED` por defecto: las pruebas con permisos usan los fixtures `enforced` y `DictProvider`.
