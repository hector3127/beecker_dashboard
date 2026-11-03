# AGENTS.md — Dashboard Management

Guía para cualquier agente (Codex, Claude Code…) o desarrollador. Antes de
tocar nada lee este archivo y
[`docs/plan-integracion-genesis.md`](docs/plan-integracion-genesis.md), que
tiene el estado, las tareas pendientes y el registro de traspaso.

## Estado

- Todas las pantallas usan `frontend/` (plantillas, CSS y JS separados) y
  Django como servidor. La migración desde Apps Script terminó; su historial
  vive en Git, no en `docs/`.
- El diseño actual es la línea base aprobada por el usuario. No hay fotos JSON
  del diseño: se protege con pruebas de humo (sin desborde, CSP, sin errores).
- Siguiente trabajo: integración como módulo de Genesis
  (`C:/Genesis/genesis`, rama `Integracion_Dashboard_Management`). No se ha
  autorizado desplegar UAT ni producción.

## Reglas que no se negocian

1. **No cambiar cálculos ni reglas de negocio.** Si algo parece mal, repórtalo.
2. **No activar `ACCESS_ENFORCED`** sin accesos configurados.
3. **Horas por mes** (`cuenta/<slug>/horas/`) se conserva: filtros de fechas y
   proyectos, CSV, permisos y regreso a la cuenta.
4. Commits pequeños **directo en `main`** (un solo desarrollador, sin ramas).
   **No hacer push** salvo petición expresa del usuario.
5. Nunca subir `.env`, `key.json`, `db.sqlite3`, `logos.json` ni credenciales.
6. No tocar cambios locales ajenos: `tools/migracion/*`, `shots_tmp/`,
   `tests/e2e/test_zz_*.py`. Agregar archivos por nombre, nunca `git add .`.
7. Lecturas del frontend con `apiGet` o el catálogo compartido de logos; no
   añadir `fetch` directo para leer datos (excepción documentada: escritura
   multipart de logos). No revertir `0de6c7d`, `3410e89`, `47d0364` ni el
   comportamiento de Capacidad diaria de `834bbfa`.
8. CSP obligatoria (`CSP_ENFORCE=True`, nonce por petición). Sin `style=""` ni
   scripts en línea.
9. `ruff format` solo sobre archivos propios, nunca sobre el repositorio entero.

## Decisiones de negocio vigentes

Detalle en `docs/`; si un documento contradice esta lista, manda esta lista.

- **EVA1** usa el inventario Summary de Azure/Clockify local por bloques S#/CR#
  (`docs/eva-inventario-activo.md`). ETC = Budget − Burn; Desv. Hrs =
  min(ETC, 0); avance = Burn / Budget × 100.
- Suspendido solo con evidencia Azure explícita (RSP activo o RCP con
  ProjectSituation Suspended). Nunca inferirlo de huecos del calendario.
- Horas facturables sin tarea/tag de alcance: una sola vez al bloque con el
  Start más antiguo entre los que cubren el día; empate queda pendiente.
- **Tarjetas EVA**: T = desviación ≤ 0 / TP; C = avance > 100 % / TP
  (sobrecosto), sobre la tabla filtrada.
- **KPI DM**: lee `DmKpiPeriod/Observation/Metric`, no recalcula al consultar.
  C es **cumplimiento** (avance ≤ 100 % / TP). Enero–septiembre 2026
  importados del reporte aprobado; octubre cerrado con la captura del 29/10.
  No reconstruir esos meses con Azure actual (`docs/kpis-dm-persistidos.md`).
- `EVA_MONTHLY_CLOSES_ENABLED=0` y `KPI_DM_AUTO_UPDATE_ENABLED=0` hasta
  acordarlo en Genesis; las tareas Windows siguen deshabilitadas.
- Bandas financieras: si falta la del mes, la última válida con tarifa positiva
  de meses anteriores del mismo año.
- El Histórico de Sheets devuelve `#REF!` (T141): se conserva la copia válida
  con su fecha original y el monitoreo sigue avisando. No ocultarlo.
- PostgreSQL y la importación de evaluaciones esperan a Genesis y a la
  plantilla oficial.

## Estructura

- `frontend/templates/layouts/` (`base.html` con el importmap `#app/...`,
  `app.html` con barra superior y `freshness`), `partials/`, `pages/`.
- `frontend/static/styles/`: `tokens.css`, `base.css`, `layout.css`,
  `components.css`, `a11y.css` y `pages/*.css` (una hoja por pantalla).
  Colores por variables de `tokens.css`; en `pages/` pueden ser literales.
- `frontend/static/scripts/`: `data/` (cliente de la API), `lib/`, `ui/`,
  `pages/<pantalla>/main.js` + `sections/`. Todo módulo compartido debe estar
  en el importmap de `layouts/base.html` (hay una prueba que lo exige).
- Datos por API: el JS pide con `apiGet` y pinta con `el()` de `lib/dom.js`
  (nunca `innerHTML` con datos).
- `apps/portal/pages.py`: vistas de páginas. `apps/portal/views.py`: servicios
  de contexto usados por la API y la precarga. `apps/portal/api/`: API v1
  (`{data, meta}`).
- `core/rpc/registry.py`: registro interno de funciones (`register_rpc`,
  `get_rpc_function`) que usan `warm_cache` y varios servicios. No hay
  transporte HTTP RPC. No borrar el registro mientras tenga consumidores.
- Conservar `views.ejecutiva`, `views.comercial`/`comercial_response`,
  `dm_state`/`dm_rows` y los servicios de caché.

## Cómo probar (Windows, Git Bash)

```bash
export MSYS_NO_PATHCONV=1
.venv/Scripts/python -m pytest tests --ignore=tests/e2e -q --no-cov
.venv/Scripts/python -m pytest tests/e2e -q --no-cov --ignore-glob='tests/e2e/test_zz_*.py'
.venv/Scripts/ruff check apps core config tests --exclude 'test_zz_*.py'
.venv/Scripts/mypy apps/portal/pages.py
node --test tests/frontend/*.test.*
```

- E2E con Playwright y red bloqueada; el fixture `datos` de
  `tests/e2e/conftest.py` pone datos de ejemplo.
- No correr dos pytest con base al mismo tiempo. No afirmar suite completa
  sumando corridas con alcances distintos.
- Los JSON de `tests/frontend/frozen/` validan cálculos: no regenerarlos para
  hacer pasar una diferencia; investigar primero.

## Cuidado

- `vista=` en Costos elige proyectos/márgenes. `?anterior=1` y
  `?vista=anterior` son enlaces viejos que deben mostrar la pantalla vigente.
- Lo que antes devolvía `?bloque=consumos` en la cuenta ahora lo da la API.
- Sin `ACCESS_ENFORCED` por defecto: las pruebas de permisos usan los fixtures
  `enforced` y `DictProvider`.
- No borrar `tmp/backups/`, CSV de datos, `.cache`, `graphify-out`, SQLite,
  `.env` ni `key.json` como si fueran residuos.
