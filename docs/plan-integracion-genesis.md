# Plan de integración de Dashboard Management en Genesis

Actualizado: 02/11/2026. **Documento de entrada y traspaso.** Quien continúe el
trabajo empieza aquí: lee «Cómo usar este documento», revisa el registro de
traspaso al final y toma la siguiente tarea libre de la tabla de fases.

No autoriza despliegues, cambios de reglas de negocio, uso de datos de
producción ni push sin petición expresa del usuario.

## 1. Cómo usar este documento

1. Lee las secciones 2 a 5 una vez: estado, decisiones, normas de Genesis y brechas.
2. Revisa la sección 6: qué preguntas siguen abiertas y qué bloquean.
3. Toma una tarea de la sección 7 cuyo estado sea `pendiente` y cuyas
   dependencias estén `terminado`. Anota tu nombre y ponla `en curso`.
4. Al terminar, cambia el estado, deja la evidencia (comando y resultado) y
   llena una fila del registro de traspaso (sección 12).
5. Si algo de este documento contradice al código, manda el código: corrige
   el documento en el mismo commit.

Estados válidos: `pendiente`, `en curso`, `bloqueado`, `revisión`, `terminado`.
No marcar `terminado` sin la evidencia que pide la tarea.

## 2. Estado al 02/11/2026

| Tema | Estado comprobado |
|---|---|
| Dashboard | `C:/beecker_dashboard`, rama `main`. Referencia funcional estable; limpieza de plantillas/JS sin uso en `4ef6d75` y `5b3d7f5` |
| Pruebas del dashboard | Node 473, servidor 1937 (`tests/portal tests/core tests/access`), e2e 742 en la corrida completa previa al último borrado |
| Genesis | `C:/Genesis/genesis`, rama local `Integracion_Dashboard_Management` en `70299ea`; **6 commits detrás de `origin/UAT`** (`76d82b8`) |
| Trabajo previo en Genesis | El commit visual `e28ec5d` (estructura y temas sin datos) lo retiró el usuario con un reset. Solo existe en el reflog local; **no recuperarlo**. La estructura se rehace en G2/G3 |
| Base local de Genesis | `Genesis/db.sqlite3` es solo de desarrollo y está atrasado (37 migraciones de `lin` pendientes). No es referencia de esquema (confirmado por Ulises) |
| Fuente de verdad del esquema Genesis | Sus migraciones (`ai_hub/migrations/`, `lin/migrations/`) y la PostgreSQL de UAT en solo lectura |
| Preguntas al equipo Genesis | Enviadas a Ulises el 02/11. Ver sección 6 |

## 3. Decisiones de arquitectura

Las marcadas *propuesta* se registran como ADR en Genesis (G2) y pasan por revisión del equipo.

| # | Decisión | Estado |
|---|---|---|
| A1 | Dashboard Management es **un módulo dentro de Genesis**, no un sistema externo. No lee ni escribe tablas de `ai_hub` ni `lin`; usa usuarios y sesión de Genesis | Comunicada a Ulises |
| A2 | Una sola app Django nueva `dashboard_management` en `Genesis/dashboard_management/`, como Lin (ADR 0026). Tablas `dashboard_management_*` en la misma base | *propuesta* |
| A3 | Las 15 apps actuales (`apps/*`, `core/`) se consolidan en subpaquetes de esa app. Migraciones nuevas desde cero; no se copian las 18 actuales | *propuesta* |
| A4 | API bajo `/api/management/`; SPA bajo `/management/...`. Evita chocar con «Dashboard» (`/`) y «Proyectos» (`/proyectos`) de Genesis | *propuesta* |
| A5 | Pantallas reescritas en React dentro de `frontend/src/components/views/management/`. Los cálculos puros de nuestros `model.js` se portan casi tal cual; el render se rehace | *propuesta* |
| A6 | Servicio de frontend `frontend/src/services/managementService.js` sobre `apiClient.js` (sesión, CSRF, `ApiError`) | *propuesta* |
| A7 | Las sincronizaciones (Clockify, Azure DevOps, Sheets, extracción EVA, KPI DM) pasan a **tipos de job** del runner de Genesis (`ai_hub/jobs/`). Los periódicos se reencolan solos con su próxima fecha. Sin hilos en el proceso web | *propuesta* |
| A8 | La caché en archivos (`.cache`) se sustituye por tablas precalculadas propias, creadas con migraciones (el disco del App Service es efímero y hay varios workers) | *propuesta* |
| A9 | El histórico se carga con un comando de importación desde un export verificable, no con una migración ni copiando el SQLite | *propuesta* |
| A10 | Piloto: **KPI DM**. Datos pequeños y ya persistidos (10 periodos, 43 métricas), sin llamadas externas al consultar | *propuesta* |
| A11 | IA: cuando se porten las pestañas de IA, pasar por `ai_hub/llm/`. El proveedor es global (`LLM_PROVIDER`, Gemini); no cambiarlo para el módulo sin acuerdo | Diferido al final |
| A12 | Bandas de costo y tarifas (Sheets) **no** se mezclan con las bandas de carrera de Lin (A1/B2 por puesto) | Firme |

## 4. Normas de Genesis que aplican al módulo

Fuente: `AGENTS.md`, `GOLDEN_PATH.md`, `docs/sdd.md`, `docs/norma/` de Genesis. Checklist para cada PR:

- [ ] **Cero comentarios** en Python y JS propios (lo exige `ai_hub/tests/test_layout.py` y la regla `no-comments` de ESLint). Docstrings y JSDoc solo para API pública.
- [ ] **Cero supresiones**: ni `noqa`, `type: ignore`, `eslint-disable`, `pragma` ni `fmt: off`.
- [ ] `mypy --strict` sobre la app completa (agregarla a `Genesis/Makefile` y a `pyproject.toml`).
- [ ] Cobertura del backend ≥ 80 % combinado (`fail_under`); el piso del frontend no baja.
- [ ] Ruff con las reglas de Genesis (`E F I UP B SIM C4 RUF RET PIE ASYNC T20 DJ`); sin `print`.
- [ ] Logs con `logging.getLogger(__name__)`, evento como mensaje y datos en `extra`; errores al cliente con `error_id` (`exception_handler.py`).
- [ ] Llamadas externas envueltas en `medir_operacion`.
- [ ] Cada endpoint en `docs/reference/openapi.yaml` (regenerar con `scripts/generar-openapi.sh`; `make verify` lo compara).
- [ ] Cada ruta del SPA en `frontend/docs/reference/mapa-de-features.md` (`pnpm verify` lo compara).
- [ ] Migraciones compatibles con el código anterior (el pipeline migra antes de repuntar).
- [ ] Permiso explícito en cada vista (el default de DRF en Genesis es `AllowAny`).
- [ ] Tests herméticos con `--disable-socket`; lo que use locks o `skip_locked`, probado con el marcador `postgres`.
- [ ] Conventional Commits, un concern por commit, tests y documentación en el mismo commit.
- [ ] Dependencias nuevas solo con `uv add` / `pnpm add` y lockfile actualizado.
- [ ] Gates mostrados: `make gate`, `make verify`, `pnpm gate`, `pnpm verify`. Nunca afirmar verde sin correrlos.

Comandos:

```bash
cd /c/Genesis/genesis/Genesis && uv sync --locked && uv run python manage.py migrate
make -C /c/Genesis/genesis/Genesis gate
make -C /c/Genesis/genesis/Genesis verify
cd /c/Genesis/genesis/frontend && pnpm gate && pnpm verify
```

## 5. Brechas del dashboard frente a Genesis

| Tema | Dashboard hoy | Trabajo |
|---|---|---|
| Tamaño | 15 apps, ~77 mil líneas Python, 285 módulos JS | Consolidar en una app (A2/A3) |
| Comentarios y supresiones | 366 líneas `#`, 49 `noqa`/`type: ignore`, 507 líneas `//` en JS | Quitar al portar; el porqué va a nombres, tests o docs |
| Tipado | `mypy` estricto solo en `apps/portal/pages.py` | Tipar estricto lo que se porte (D4) |
| Frontend | Plantillas Django + módulos JS sin compilación, CSP con nonce | React/JSX con Tailwind y Recharts (A5). La CSP la da el Static Web App, no Django |
| Rutas | `/`, `/proyectos/`, `/operativa/`… | Prefijo `/management` (A4) |
| API | 100 endpoints `/api/v1/` con `{data, meta}` | Documentarlos en OpenAPI; mantener contrato |
| Caché | Archivos en `.cache` | Tablas precalculadas (A8) |
| Trabajo largo | Extracción EVA ~68 s; hilos en `apps/portal/services/executive_refresh.py`, `core/utils/parallel.py`, `apps/gmail/services/thread_finder.py` | Jobs del runner (A7). `GUNICORN_TIMEOUT` es 60 s |
| Usuarios y permisos | `apps/access` (capacidades y alcance) | Mapear a grupos de Django o roles de Lin (pregunta P1) |
| Credenciales | `.env`, `key.json`, PAT personal, OAuth de Gmail | Cuentas de servicio en app settings (pregunta P3) |
| Dependencias | `google-api-python-client`, `google-auth`, `Pillow` no están en Genesis | `uv add` con aprobación del equipo |
| Datos | SQLite ~4.22 GB | Export + import verificado (A9, D3, G7) |

## 6. Preguntas abiertas y bloqueos

Enviadas a Ulises (infraestructura) el 02/11. La de permisos va a quien defina el negocio.

| ID | Pregunta | Bloquea | Respuesta |
|---|---|---|---|
| P1 | Quién ve finanzas, todo el portafolio o solo sus proyectos; roles de Lin o grupos nuevos; cómo ligar usuario de Genesis con nombre de DM en Azure | G5 (permisos reales), G9 | Pendiente |
| P2 | ¿~5 GB por entorno en `psql-flx-genesis` (B1ms compartido) o subir de tier? ¿Quién carga el histórico en UAT/PROD y en qué ventana? | G10 | Pendiente |
| P3 | Quién crea cuentas de servicio de Azure DevOps, Clockify y Google, y quién las carga como app settings en UAT/PROD | G8 | Pendiente |
| P4 | Lectura sobre `rg-genesis` y rol PostgreSQL de solo lectura en `genesis_uat_db` | Validar esquema real y app settings (no bloquea el trabajo local) | Pendiente |

Ya respondido por el código o por Ulises (no volver a preguntar):

- La base local de Genesis no es referencia; mandan las migraciones y UAT.
- UAT tiene `RUN_JOBS_WORKER=true` y `JOBS_RUNNERS=2`; el runner admite reprogramar un job.
- No hay VNet ni restricción de salida en el App Service.
- Los secretos van como app settings (sin Key Vault).
- Existe Blob (`media`, `media-uat`) para archivos como logos.
- La base de Genesis es pequeña (respaldo PROD de 22.4 MB en septiembre).

## 7. Fases y tareas

Las tareas D se hacen en el dashboard y las G en Genesis (rama local, sin push hasta que el usuario lo pida).

### Fase 1 — Preparar el dashboard (no bloqueada)

| ID | Tarea | Depende | Estado | Responsable | Terminado cuando |
|---|---|---|---|---|---|
| D1 | **Congelar contratos de API**: por cada endpoint del piloto y de cada bloque, guardar respuesta JSON con datos fijos (`tests/contracts/<pantalla>/*.json`) y un test que la compare | — | pendiente | — | Test pasa; una alteración deliberada lo rompe |
| D2 | **Separar servicios puros**: que los cálculos de cada pantalla se llamen sin request, caché ni vistas (entrada → salida tipada) | — | pendiente | — | Tests de servicio sin cliente HTTP; cifras iguales a D1 |
| D3 | **Comando de exportación** `export_for_genesis`: tablas propias a JSONL por tabla, con conteos y SHA-256 en un manifiesto | — | pendiente | — | Export de la base local; manifiesto reproducible; sin secretos ni usuarios |
| D4 | **Tipado estricto y sin supresiones** en los servicios que se portan (empezar por KPI DM) | D2 | pendiente | — | `mypy --strict` y `ruff` limpios en esos módulos |
| D5 | **Sincronizaciones como funciones idempotentes** sin hilos: `sync(rango, cursor) -> resultado` reutilizable por un handler de job | D2 | pendiente | — | Tests de reintento e idempotencia; sin `threading` en la ruta |
| D6 | **Inventario de colores** por pantalla (literales de `pages/*.css`) → lista de tokens del módulo para claro y oscuro | — | terminado | Héctor (con Claude) | [diseno-modo-oscuro.md](diseno-modo-oscuro.md): 5,885 usos y 3,339 valores agrupados en 14 funciones; 30 tokens `--mg-*` con valor claro y oscuro y tabla de traducción |

### Fase 2 — Esqueleto en Genesis (no bloqueada, local)

| ID | Tarea | Depende | Estado | Responsable | Terminado cuando |
|---|---|---|---|---|---|
| G1 | Sincronizar la rama local con `origin/UAT`; `uv sync --locked`, `migrate`, `pnpm install --frozen-lockfile` | — | pendiente | — | Rama al día; Genesis arranca con base local migrada |
| G2 | App `dashboard_management`: `apps.py`, `urls.py` en `/api/management/`, `INSTALLED_APPS`, Makefile/pyproject (mypy, cobertura), ADR nuevo, fila en `structure-deviations.md`, endpoint `ping` con permiso de sesión | G1 | pendiente | — | `make gate` y `make verify` en verde |
| G3 | Módulo SPA: ruta `/management` con `PrivateRoute`, ítem en `navigation.js`, layout propio, tokens del módulo claro/oscuro enlazados a `theme.css`, mapa de features | G1, D6 | pendiente | — | `pnpm gate` y `pnpm verify` en verde; los tres temas (claro, oscuro, sistema) visibles |
| G4 | Servicio `managementService.js` sobre `apiClient.js` y manejo de carga, vacío, error con `error_id` y reintento | G3 | pendiente | — | Tests Vitest del servicio y de los estados |

### Fase 3 — Piloto KPI DM

| ID | Tarea | Depende | Estado | Responsable | Terminado cuando |
|---|---|---|---|---|---|
| G5 | Modelos `DmKpiPeriod/Observation/Metric` en la app, comando de importación desde D3 y endpoint de lectura con el mismo contrato que D1 | G2, D1, D3, D4 | pendiente | — | Conteos y cifras iguales al dashboard; cobertura ≥ 80 % del módulo |
| G6 | Pantalla KPI DM en React: año único, mes, multiselección de DMs, tablas, tendencia y glosario; claro y oscuro | G4, G5 | pendiente | — | Mismas cifras que el dashboard; filtros en URL; cuatro anchos; tema no reinicia filtros |
| G6b | Permisos reales del piloto | G6, P1 | bloqueado | — | Pruebas sin sesión, sin permiso y con permiso |

### Fase 4 — Fuentes y trabajos

| ID | Tarea | Depende | Estado | Responsable | Terminado cuando |
|---|---|---|---|---|---|
| G7 | Modelos de datos base (clientes, personas, proyectos, Clockify, Azure) e importación por lotes desde D3 | G5 | pendiente | — | Integridad referencial, conteos y horas por mes/proyecto iguales |
| G8 | Tipos de job de sync (Clockify, Azure DevOps, Sheets) con D5, reencolado periódico y candados | G7, D5, P3 | bloqueado | — | Reintento, idempotencia, lease y reinicio probados con marcador `postgres` |

### Fase 5 — Resto de pantallas

Orden recomendado; cada bloque repite: contrato D1 → servicio portado → endpoint → pantalla React → ambos temas → evidencia.

| ID | Bloque | Depende | Estado |
|---|---|---|---|
| G9 | EVA1 y Summary (inventario, cortes, iteraciones) | G7, G8 | pendiente |
| G10a | Operativa, capacidad, facturabilidad, inversión | G7 | pendiente |
| G10b | EVA2/EVA3/EVA4 | G7 | pendiente |
| G10c | Business Overview, financiera, costos, márgenes, comercial | G7, G8, P1 | pendiente |
| G10d | Cuenta y Horas por mes (CSV, regreso a cuenta) | G7 | pendiente |
| G10e | Detalle de proyecto y pestañas (AER/IXS, RAID, Azure, recursos) | G7, G8 | pendiente |
| G10f | Pestañas de IA vía `ai_hub/llm` | G10e, A11 | pendiente |

### Fase 6 — UAT

| ID | Tarea | Depende | Estado |
|---|---|---|---|
| G11 | Importación completa en UAT con respaldo y reversión; cierres KPI intactos | G9–G10, P2 | bloqueado |
| G12 | PR de `Integracion_Dashboard_Management` a UAT con gates y evidencia; revisores Talin y Ulises | G11 | pendiente |

## 8. Diseño y modo oscuro

Cómo funciona en Genesis: `ThemeProvider` (`frontend/src/context/ThemeContext.jsx`) guarda `light`, `dark` o `system` en `genesis-theme`, pone la clase `.dark` y `data-theme` en `<html>`, y `frontend/src/styles/theme.css` define las variables (`--background`, `--surface`, `--foreground`, `--border`, `--primary`, `--chart-1..5`…) para `:root` y `.dark`, expuestas a Tailwind con `@custom-variant dark`.

Reglas del módulo:

- El diseño claro actual del dashboard es la referencia: organización, jerarquía, tamaños, tarjetas, tablas, filtros y gráficas.
- Usar el `ThemeToggle` y el `ThemeProvider` de Genesis. No crear otro selector ni otra preferencia.
- Tokens propios con prefijo `--mg-*`, definidos bajo la clase raíz del módulo y redefinidos bajo `.dark`. Donde el significado coincide, apuntan a los de Genesis (`--mg-surface: var(--surface)`).
- Conservar el significado de los colores de riesgo, cumplimiento, suspensión y sobrecosto; ajustar solo el tono para contraste. No invertir colores en bloque.
- Cubrir gráficas (ejes, leyendas, tooltips), tablas con encabezado fijo, formularios, diálogos y estados de carga, vacío, error, hover y foco.
- Estilos aislados en el módulo: no tocar el tema ni los componentes de Lin u otras pantallas.
- No hace falta agregar modo oscuro al dashboard independiente: se hace al portar cada pantalla.
- Tokens, valores claro/oscuro y tabla de traducción: [diseno-modo-oscuro.md](diseno-modo-oscuro.md).

Aceptación por pantalla: claro igual al diseño aprobado; oscuro y sistema legibles (contraste AA en texto); cambiar de tema no reinicia filtros ni cambia cifras; cuatro anchos (1450, 1000, 768, 390) sin desborde horizontal.

## 9. Reglas funcionales que se conservan

- EVA1 activo usa inventario Summary Azure/Clockify local, con bloques S#/CR# independientes. Fechas desde iteraciones; Finish usa la última etapa fechada.
- Etapas activas por rango inclusivo al corte. Suspendido solo con evidencia Azure explícita (RSP activo o RCP con situación Suspended); nunca inferirlo de huecos.
- Burn: horas facturables atribuidas al bloque. ETC = Budget − Burn; Desv. Hrs = min(ETC, 0); avance = Burn / Budget × 100 con faltantes explícitos.
- Horas sin tarea/tag de alcance: una sola vez al bloque que inició primero entre los elegibles; empate pendiente; nota visible.
- T de EVA1/KPI: desviación ≤ 0 / TP. **C de KPI DM es cumplimiento** (avance ≤ 100 / TP). Las tarjetas EVA conservan su propia regla; verificar el contrato de cada C.
- KPI DM lee sus tablas, no recalcula al consultar. Enero–septiembre 2026 importados del reporte aprobado; octubre cerrado con la captura del 29/10 (TP 9, T 100 %, C 66.7 %). No reconstruir esos meses con Azure actual.
- Automatización KPI y cierres EVA siguen desactivados hasta acordarlo en Genesis.
- EVA4 excluye AER; paquete no aplicable es N/A, nunca horas inventadas.
- Bandas financieras: si falta la del mes, la última válida con tarifa positiva de meses anteriores del mismo año; sin banda válida queda pendiente.
- Capacidad: base = personas × días hábiles × jornada; concepto por ID en Azure/MPB (Proyecto), nomenclatura NYB (Interno) o nombre de Clockify.
- Conservar Horas por mes, exportaciones CSV, regreso a cuenta y alcance limitado.

Detalle: [EVA vigente](eva-inventario-activo.md), [histórico Azure](historico-azure.md), [fuentes persistentes](fuentes-persistentes.md), [KPIs persistidos](kpis-dm-persistidos.md), [reglas KPI](kpis-dm-reglas.md), [inventario de páginas y API](inventario-integracion-genesis.md).

## 10. Datos y fuentes

Medición de solo lectura del 02/11/2026 en `C:/beecker_dashboard/db.sqlite3` (~4.22 GB; 31 tablas propias):

| Grupo | Datos |
|---|---|
| Catálogos | 250 clientes, 293 personas, 1,614 proyectos |
| Clockify | 536,344 entradas; meses 2024-08 a 2026-11 |
| Azure | 451 proyectos, 227,782 WI, 781,913 revisiones |
| Sheets | 14 copias locales |
| KPI DM | 10 periodos, 10 observaciones, 43 métricas |

Fuentes externas que siguen vivas: Azure DevOps, Clockify, Google Sheets (DataRevenue, bandas/tarifas, MPB, ROC), Google Drive y Gmail para funciones IA/correo.

Reglas de importación: respaldo consistente previo; base de prueba aislada; lotes preservando IDs, fechas y JSON; comparar conteos, duplicados, integridad y horas por mes/proyecto; conservar periodos KPI cerrados; reversión definida antes de UAT; nunca importar usuarios, sesiones ni secretos. Nunca copiar SQLite, `.env`, `key.json`, caché ni respaldos al repo de Genesis.

## 11. Cómo trabajar sin pisarse

- Dashboard: commits pequeños directo en `main`; no push sin petición; no tocar `tools/migracion/*`, `shots_tmp/`, `logos.json` ni `tests/e2e/test_zz_*.py` (cambios locales ajenos).
- Genesis: trabajar en `Integracion_Dashboard_Management`; nunca push a `UAT`/`main` ni `--force`; no tocar `ai_hub` ni `lin` salvo lo mínimo para registrar la app (settings, urls, navegación, test_layout).
- Una persona por archivo de settings, rutas o migraciones a la vez. Antes de empezar: `git status`, `git log -5` y este registro.
- No correr dos pytest con base al mismo tiempo. No activar sincronizaciones reales en pruebas.

## 12. Registro de traspaso

Agregar una fila por sesión de trabajo, la más reciente arriba.

| Fecha | Quién | Tareas | Repo / commit | Evidencia | Siguiente paso / bloqueos |
|---|---|---|---|---|---|
| 02/11/2026 | Héctor (con Claude) | D6 terminado: tokens de modo oscuro | Dashboard, commit de `diseno-modo-oscuro.md` | Medición de colores por hoja (sección Diagnóstico) | Seguir con G1–G3 |
| 02/11/2026 | Héctor (con Claude) | Limpieza previa: 62 documentos históricos, transporte RPC de pruebas, fotos JSON del diseño y herramienta de carga | Dashboard `1f2759e`, `915bbfd`, `7499608` | Servidor 2928; Node 473; e2e 691 + 3 corregidas tras la corrida (33 en sus archivos) | Empezar D1/D3/D6 y G1–G3 |
| 02/11/2026 | Héctor (con Claude) | Revisión completa de Genesis, limpieza del dashboard, preguntas P1–P4, este plan | Dashboard `5b3d7f5` + commit de este plan | Node 473, servidor 1937, e2e capacidad 18 | Empezar D1/D3/D6 y G1–G3; esperar P1–P4 |
