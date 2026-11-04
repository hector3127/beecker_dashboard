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
| Genesis | `C:/Genesis/genesis`, rama local `Integracion_Dashboard_Management` en `9b1afe7` (al día con `origin/UAT` `76d82b8` más 3 commits propios, sin push) |
| Trabajo previo en Genesis | El commit visual `e28ec5d` (estructura y temas sin datos) lo retiró el usuario con un reset. Solo existe en el reflog local; **no recuperarlo**. La estructura se rehace en G2/G3 |
| Base local de Genesis | `Genesis/db.sqlite3` es solo de desarrollo y está atrasado (37 migraciones de `lin` pendientes). No es referencia de esquema (confirmado por Ulises) |
| Fuente de verdad del esquema Genesis | Sus migraciones (`ai_hub/migrations/`, `lin/migrations/`) y la PostgreSQL de UAT en solo lectura |
| Preguntas al equipo Genesis | Enviadas a Ulises el 02/11. Ver sección 6 |

## 3. Decisiones de arquitectura

Las marcadas *propuesta* se registran como ADR en Genesis (G2) y pasan por revisión del equipo.

| # | Decisión | Estado |
|---|---|---|
| A1 | Dashboard Management es **un módulo dentro de Genesis**, no un sistema externo. No lee ni escribe tablas de `ai_hub` ni `lin`; usa usuarios y sesión de Genesis | Comunicada a Ulises |
| A2 | Una sola app Django nueva `dashboard_management` en `Genesis/dashboard_management/`, como Lin (ADR 0026). Tablas `management_*` (`db_table` de cada modelo, migración `0003`) en la misma base | *propuesta* |
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
| P5 | Dashboard Management son plantillas Django con JS sin compilar (unas 29 mil líneas de dibujo de pantallas). ¿Confirman que se porta como componentes React del SPA de Genesis, reutilizando cálculos y backend, o prefieren embeberlo de otra forma? | Decisión A5 y toda la Fase 5 | Pendiente |

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
| D1 | **Congelar contratos de API**: por cada endpoint del piloto y de cada bloque, guardar respuesta JSON con datos fijos (`tests/contracts/<pantalla>/*.json`) y un test que la compare | — | terminado | Héctor (con Claude) | Solo KPI DM por ahora: `tests/contracts/test_kpis_dm_contract.py` guarda 7 respuestas completas en `tests/contracts/kpis_dm/` (5 consultas y 2 errores); alterar una cifra del JSON hace fallar la prueba. Falta repetir el patrón en las demás pantallas al portarlas |
| D2 | **Separar servicios puros**: que los cálculos de cada pantalla se llamen sin request, caché ni vistas (entrada → salida tipada) | — | terminado | Héctor (con Claude) | Solo KPI DM: `apps/portal/services/kpi_screen.py` (`build_kpi_context`) no usa request, reloj, base ni DRF; `views.kpi_context` es un adaptador. Los 7 contratos de D1 no cambiaron, 20 pruebas nuevas sin cliente HTTP, 2955 de servidor y 28 e2e de KPIs en verde |
| D3 | **Comando de exportación** `export_for_genesis`: tablas propias a JSONL por tabla, con conteos y SHA-256 en un manifiesto | — | terminado | Héctor (con Claude) | `manage.py export_for_genesis --group kpi --out tmp/...` y `--verify`: JSONL por tabla con manifiesto (filas, columnas, llaves foráneas y SHA-256); rechaza destinos dentro del repo (salvo `tmp/`) y tablas excluidas; 28 pruebas. Corrida real sobre el grupo `kpi`: 17 extracciones, 10 periodos, 10 observaciones y 43 métricas, verificado. Los grupos `clockify`, `azure`, `catalogos`, `eva`, `hojas` y `acuerdos` existen y están probados con datos de prueba, pero no se han exportado de la base real (la de Clockify y Azure es grande) |
| D4 | **Tipado estricto y sin supresiones** en los servicios que se portan (empezar por KPI DM) | D2 | terminado | Héctor (con Claude) | Solo KPI DM: `kpi_screen.py` pasa `mypy` estricto, sin `noqa` ni `type: ignore`. Los módulos de los que depende (`kpi_eva`, `kpi_history`, `kpi_quarterly`, `kpi_dm_store`) no se revisaron en estricto |
| D5 | **Sincronizaciones como funciones idempotentes** sin hilos: `sync(rango, cursor) -> resultado` reutilizable por un handler de job | D2 | pendiente | — | Tests de reintento e idempotencia; sin `threading` en la ruta |
| D6 | **Inventario de colores** por pantalla (literales de `pages/*.css`) → lista de tokens del módulo para claro y oscuro | — | terminado | Héctor (con Claude) | [diseno-modo-oscuro.md](diseno-modo-oscuro.md): 5,885 usos y 3,339 valores agrupados en 14 funciones; 30 tokens `--mg-*` con valor claro y oscuro y tabla de traducción |

### Fase 2 — Esqueleto en Genesis (no bloqueada, local)

| ID | Tarea | Depende | Estado | Responsable | Terminado cuando |
|---|---|---|---|---|---|
| G1 | Sincronizar la rama local con `origin/UAT`; `uv sync --locked`, `migrate`, `pnpm install --frozen-lockfile` | — | terminado | Héctor (con Claude) | Rama al día con `origin/UAT`; `uv sync --locked`, `migrate` y `pnpm install --frozen-lockfile` sin errores |
| G2 | App `dashboard_management`: `apps.py`, `urls.py` en `/api/management/`, `INSTALLED_APPS`, Makefile/pyproject (mypy, cobertura), ADR nuevo, fila en `structure-deviations.md`, endpoint `ping` con permiso de sesión | G1 | terminado | Héctor (con Claude) | `c2170d0`: app, `ping/` autenticado, ADR 0030, desvío, OpenAPI; 3 + 2 pruebas nuevas, mypy estricto limpio, 91.6 % de cobertura |
| G3 | Módulo SPA: ruta `/management` con `PrivateRoute`, ítem en `navigation.js`, layout propio, tokens del módulo claro/oscuro enlazados a `theme.css`, mapa de features | G1, D6 | terminado | Héctor (con Claude) | `a471580`: ruta, menú y vista; 6 pruebas Vitest; verificado en claro, oscuro, sistema y 390 px (ver `odd/tasks/dashboard-management.md` en Genesis) |
| G4 | Servicio `managementService.js` sobre `apiClient.js` y manejo de carga, vacío, error con `error_id` y reintento | G3 | terminado | Héctor (con Claude) | `070ab65`: `managementService` (ping y lectura con parámetros), hook `useConsulta` y `EstadoDeConsulta` (cargando, vacío, error con `error_id` y reintento; descarta respuestas tardías); 27 pruebas Vitest, cobertura y build en verde |

### Fase 3 — Piloto KPI DM

| ID | Tarea | Depende | Estado | Responsable | Terminado cuando |
|---|---|---|---|---|---|
| G5 | Modelos `DmKpiPeriod/Observation/Metric` en la app, comando de importación desde D3 y endpoint de lectura con el mismo contrato que D1 | G2, D1, D3, D4 | terminado | Héctor (con Claude) | Genesis `e32c1f0` y el commit de G5: modelos y migración, lectura de capturas, cálculo, `GET /api/management/kpis-dm/` e `importar_kpis_dm` (verifica SHA-256 sin distinguir CRLF, carga atómica, llaves conservadas). Paridad: 6 respuestas del dashboard sobre el mismo escenario coinciden campo por campo (`tests/contracts/kpis_dm_db/` aquí y `dashboard_management/tests/datos/` allá). 95 pruebas del módulo y 99 % de cobertura. Permisos aún solo de sesión (P1). Con datos reales: el paquete de `tmp/genesis-export-kpi` importado en una base desechable de Genesis devolvió lo mismo que el dashboard en 3 consultas, sin diferencias |
| G6 | Pantalla KPI DM en React: año único, mes, multiselección de DMs, tablas, tendencia y glosario; claro y oscuro | G4, G5 | terminado | Héctor (con Claude) | Genesis, commit de G6: filtros (mes, año y selector global de DMs), tarjetas, tabla por DM, gráfica, históricos mensual y trimestral y glosario, con estado en la URL. 633 pruebas de Vitest, lint, cobertura y build en verde. Comprobada en el navegador con los datos reales importados (corte 29/10/2026: C 66.7 %, TP 9) en claro y oscuro y a 390 px. Pendiente: contraste AA sin medir, DMs sin enlace al detalle (esa pantalla no existe en Genesis) y permisos (G6b) |
| G6b | Permisos reales del piloto | G6, P1 | bloqueado | — | Pruebas sin sesión, sin permiso y con permiso |

### Fase 4 — Fuentes y trabajos

| ID | Tarea | Depende | Estado | Responsable | Terminado cuando |
|---|---|---|---|---|---|
| G7 | Modelos de datos base (clientes, personas, proyectos, Clockify, Azure) e importación por lotes desde D3 | G5 | terminado | Héctor (con Claude) | Genesis, commit de G7: 23 modelos (migración `0002`), `importar_datos_dm` por subconjuntos y por lotes, y 110 pruebas del módulo. Con datos reales (catálogos, hojas, EVA y Clockify, 2.4 GB) en SQLite: 202 s de carga y diferencias cero en 536,344 entradas, 4,498 grupos mes x proyecto, 1,939,720,091 segundos y los demás conteos. Azure con datos reales también idéntico (227,782 work items, 781,913 revisiones; el exportador perdía los microsegundos y se corrigió). Pendiente: medir en PostgreSQL (P2), acuerdos y logos |
| G8 | Tipos de job de sync (Clockify, Azure DevOps, Sheets) con D5, reencolado periódico y candados | G7, D5, P3 | bloqueado | — | Reintento, idempotencia, lease y reinicio probados con marcador `postgres` |

### Fase 5 — Resto de pantallas

Orden recomendado; cada bloque repite: contrato D1 → servicio portado → endpoint → pantalla React → ambos temas → evidencia.

| ID | Bloque | Depende | Estado |
|---|---|---|---|
| G9 | EVA1 y Summary (inventario, cortes, iteraciones) | G7 | terminado (G9a-G9e), con paridad con datos reales en SQLite |
| G10a | Operativa, capacidad, facturabilidad, inversión | G7 | en curso, ver el desglose |
| G10a0 | Motor GSE (horas del mes por área, persona y categoría desde Bandas/rol, CatalagoProyectos y las horas guardadas de Clockify) | G7 | terminado: paridad con el contrato; sin endpoint |
| G10a1 | Facturabilidad general, por especialidad y por recurso (mes y año sobre GSE) | G10a0 | implementado localmente; general coincide en 12 periodos y Especialidad/Recurso en 9 consultas sobre el mismo GSE real. Roles y estado de plantilla conservados; revisión visual clara/oscura a 1440, 390 y 320 px; gates completos pendientes |
| G10a2 | Inversión (etiquetas de inversión y proyectos EVA sobre las horas guardadas) | G10a0 | piloto local con desglose por recurso/proyecto, búsqueda, orden, páginas, CSV y regreso desde el proyecto. Resumen y desglose coinciden en tres escenarios sobre los mismos registros; probado en ambos temas a 1440, 390 y 320 px. 25 de 186 proyectos sin cobertura histórica completa; paridad de extracción y gates completos pendientes |
| G10a3 | Capacidad (diaria y por proyecto) | G7 | implementado localmente; paridad completa en septiembre, octubre y noviembre 2026; gates completos pendientes |
| G10a4 | Centro Operativa (EVA, facturabilidad, capacidad e inversión) | G10a1-G10a3 | implementado localmente; 134 pruebas de Management pasan; revisión visual y gates completos pendientes |
| G10b | EVA2/EVA3/EVA4 | G7 | terminado: EVA2 cubierta por EVA 1 (misma población al corte de hoy); EVA-04 y EVA 3 con paridad con datos reales |
| G10c | Business Overview, financiera, costos, márgenes, comercial | G7 (P1 solo decide quién ve cada pantalla; mientras tanto, superusuario como en los pilotos) | desglose abajo, sin empezar |
| G10c0 | Motor de costos por proyecto (`revenue_costs`: IDs de DataRevenue y MPB, banda vigente por persona con Master rates, horas de Clockify por tarifa, AER/ROC por mes) | G10a0 | pendiente |
| G10c1 | Costos por cuenta y proyecto (`costos_revenue`, ingreso por proyecto) | G10c0 | pendiente |
| G10c2 | Márgenes por oportunidad (`margins_screen`, `opportunity_profitability`) | G10c1 | pendiente |
| G10c3 | Financiera (`financial_cache`, bandas del mes o la última válida del año) | G10c0 | pendiente |
| G10c4 | Comercial (`commercial*`, `executive_commercial`) | G10c3 | pendiente |
| G10c5 | Business Overview (`ejecutiva`) | G10c1-G10c4 | pendiente |
| G10d | Cuenta y Horas por mes (CSV, regreso a cuenta) | G7 | piloto local para superusuarios; Horas por mes coincide en 53 IDs y sus celdas en 3 cuentas (sep–oct 2026); navegación Cuenta → Proyecto → pestañas → Cuenta verificada en claro y oscuro a 1440, 390 y 320 px; permisos P1 y gates completos pendientes |
| G10e | Detalle de proyecto y pestañas (AER/IXS, RAID, Azure, recursos) | G7, G8 | piloto local de solo lectura para superusuarios: Ejecutivo, Planeación, Esfuerzo y Recursos de EVA 1 y EVA 3 vigente/finalizado, Gestión RAID, Cliente, Azure DevOps, Acciones y Comunicación. Selector de periodo MPB, Burn histórico conservado y catálogo paginado. Acciones con conteos y tres contratos sintéticos; Cliente con directorio, filtros, información, gobierno, documentos y matriz de participación, coincidente en cuatro contratos AER/IXS. Faltan copias locales de Cliente/seguimiento, escrituras y paridad integral |
| G10f | Pestañas de IA vía `ai_hub/llm` | G10e, A11 | piloto local de análisis ejecutivo agregado bajo demanda; proveedor real, historial y flujos de IA originales pendientes |

Desglose de G9 (EVA1). G8 solo hace falta para actualizar datos; EVA1 lee cortes guardados, así que puede avanzar con G7.

| ID | Paso | Estado |
|---|---|---|
| G9a | `apps/portal/services/eva1_screen.py` (`build_eva1_screen(cut, manager, service)`): el contexto de la página sin petición ni plantilla; `views.eva1` solo lee `corte`, `manager` y `service` y lo pinta. 387 pruebas de EVA, acceso y refresco en verde, ruff y mypy limpios | terminado |
| G9b | Escenario sintético de EVA1 y contrato JSON: `tests/contracts/test_eva1_contract.py` guarda en `tests/contracts/eva1_db/` cinco cuerpos (corte por omisión, con DM, con servicio, DM sin proyectos y corte anterior) y el paquete de exportación (`EvaExtraction`, `EvaAzureSource`, `EvaScopeSnapshot`). Seis fuentes: cuatro abiertas (horas repartidas entre sprint y CR con una entrada automática, sin Clockify, suspendida), una cerrada y confirmada, una AER y una posterior al corte; las tres últimas no deben aparecer. Verificado: S1 con 120 h de 200 (60 %), CR1 con 50 h de 40 (125 %, 5 días tarde), T 75 % y C 25 %. Nota: un alcance sin etapa Discovery no tiene fecha de inicio y queda fuera, por regla (Start = Discovery). 1,809 pruebas de contratos y portal en verde | terminado |
| G9c | Portar a `dashboard_management` los cálculos que alimentan el contexto, sin cambiar reglas (sección 9). G9c1 terminado: `eva_iteraciones`, `eva_horas` y `eva_totales`. G9c2: `eva_vista`. G9c3: `eva_clockify`, `eva_metricas`, `eva_inventario` y `eva_pantalla`, con paridad en los cinco cuerpos de `eva1_db/`. G9c4: `eva_motor` y `eva_historia` (`build_row`, `metric_rows`, `attach_history` con su caché); `test_eva1_historia_contract.py` suma un flujo de 15 revisiones y tres cuerpos con historia, idénticos en Genesis; 222 pruebas del módulo. Pendiente de G9d: variable de entorno con la identidad del flujo y `EVA_MONTHLY_CLOSES_ENABLED` | terminado |
| G9d | `GET /api/management/eva1/` con `corte`, `manager` y `service`; paridad con el contrato de G9b y G9c4. Terminado: la API devuelve los seis cuerpos del contrato (por omisión, con DM, con servicio, DM sin proyectos, corte anterior y con historia); variables `EVA_MONTHLY_CLOSES_ENABLED` y `EVA_AZURE_FEED_IDENTITY`; OpenAPI y referencias al día; 17 pruebas de la API | terminado |
| G9e | Pantalla React de EVA 1 en `components/views/management/eva/`: filtros (corte, DM, servicio), tarjetas TP, Suspendidos, T y C, pivotes por DM, tabla de 27 columnas con orden, búsqueda y CSV, claro y oscuro. Verificada en el navegador (AA en 231 textos por tema, sin desborde a 390 px) y con 659 pruebas de Vitest. No están los menús de filtro por columna ni el filtro de fechas del dashboard | terminado |

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
| 03/11/2026 | Héctor (con Claude) | G10a0: motor GSE en Genesis con paridad | Dashboard: `tests/contracts/test_gse_contract.py` y `gse_db/`; Genesis, commit de G10a0 (`gse_base.py`, `gse_catalogo.py`, `gse_equipo.py`, `gse_mes.py`) | 11 casos idénticos al dashboard, 98 % de cobertura del módulo, mypy y ruff limpios; sin endpoint ni pantalla | Seguir con G10a1 (Facturabilidad: mes y año sobre el motor, endpoint y pantalla). Aún sin push |
| 03/11/2026 | Héctor (con Claude) | G10b-EVA3: EVA 3 en Genesis con paridad con datos reales | Dashboard: `tests/contracts/test_eva3_contract.py` y `eva3_db/`; Genesis, commit de EVA 3 (`mpb.py`, `eva3_consumo.py`, `eva3.py`, endpoint `eva3/`, sección EVA 3) | Cuerpo real idéntico (15 en progreso, 40 finalizados, 0 diferencias); 702 pruebas de Vitest; navegador con AA en claro, oscuro y 390 px | Seguir con Operativa (G10a: capacidad, facturabilidad, inversión) o con Cuenta y Horas por mes (G10d, regla 3 de AGENTS); G10c y G10e esperan P1 y G8. Aún sin push |
| 03/11/2026 | Héctor (con Claude) | G10b-EVA4: EVA-04 en Genesis con paridad con datos reales | Dashboard: `tests/contracts/test_eva4_contract.py` y `eva4_db/`; Genesis, commit de EVA-04 (`eva4*.py`, `texto.py`, `fechas.py`, `hojas.py`, endpoint `eva4/`, sección EVA-04) | 5 de 5 meses reales idénticos al dashboard; 682 pruebas de Vitest; navegador con AA en claro, oscuro y 390 px | EVA 3 (AER y T&M, hoja MPB): contrato en el dashboard, `build_aer_tym_summary` y consumo de Clockify en Genesis; después Operativa (G10a) y Cuenta y Horas por mes (G10d). Aún sin push |
| 03/11/2026 | Héctor (con Claude) | Tablas `management_` y datos reales en la base local de Genesis; paridad de EVA 1 con datos reales | Genesis, commit de la migración `0003` y los `db_table`; dashboard: plan | Importación real de 26 tablas en `Genesis/db.sqlite3` (7 min 33 s) y 9 de 9 consultas de EVA 1 idénticas al dashboard | Probar la pantalla en el navegador con esos datos y seguir con EVA 2-4 (G10b) u Operativa (G10a); la carga en PostgreSQL y los permisos (P1, P2) esperan acceso. El paquete `tmp/genesis-export-real` (3.9 GB, ignorado) sirve para cargarlo a Postgres |
| 03/11/2026 | Héctor (con Claude) | G9e: pantalla React de EVA 1 en Genesis | Genesis, commit de G9e (`eva/`, `managementService.leerEva1`, `management.css`) | 659 pruebas de Vitest, lint, formato, cobertura y build; navegador en claro, oscuro y 390 px con AA | Comparar EVA 1 con datos reales (importar el paquete de Azure y EVA en una base desechable y cotejar cortes contra el dashboard); luego EVA2-4 (G10b) o Operativa (G10a); medir en PostgreSQL (P2) cuando haya acceso |
| 03/11/2026 | Héctor (con Claude) | G9d: endpoint `/api/management/eva1/` en Genesis | Genesis, commit de G9d (`views.py`, `urls.py`, `settings.py`, OpenAPI y docs de referencia) | El endpoint devuelve los cuerpos del contrato del dashboard; 305 pruebas, 97.6 % de cobertura | G9e: pantalla React de EVA 1 en `components/views/management/eva/` (tarjetas TP, Suspendidos, T y C; pivotes por DM; tabla de 27 columnas con filtros, orden y CSV; selector de corte), claro y oscuro, con `managementService.leerEva1` |
| 03/11/2026 | Héctor (con Claude) | G9c4: motor de métricas e historia de Azure en Genesis | Dashboard: `test_eva1_historia_contract.py` y `eva1_db/export_historia/`; Genesis, commit de G9c4 (`eva_motor`, `eva_historia`) | Tres cuerpos con historia idénticos a los del dashboard; 222 pruebas del módulo, 97 % de cobertura | G9d: endpoint `GET /api/management/eva1/` (corte, manager, service), variables de entorno (identidad del flujo y cierres), OpenAPI y permisos de sesión; luego G9e (pantalla React) |
| 03/11/2026 | Héctor (con Claude) | G9c3: lectura del inventario guardado y pantalla EVA 1 en Genesis, con paridad | Genesis, commit de G9c3 (`eva_clockify`, `eva_metricas`, `eva_inventario`, `eva_pantalla`, `plano`) | 5 cuerpos idénticos a los del dashboard; 192 pruebas del módulo, 97 % de cobertura, ruff y mypy estricto | G9c4: motor de métricas de Azure para cortes pasados (`build_row`, `attach_history`) y escenario con revisiones; luego G9d (endpoint `/api/management/eva1/` y variable `EVA_MONTHLY_CLOSES_ENABLED`) |
| 03/11/2026 | Héctor (con Claude) | G9c1-G9c2: iteraciones, horas, totales y vista de EVA en Genesis | Genesis, dos commits locales (`eva_*.py`) | Pruebas del módulo en verde, ruff y mypy estricto; los cuatro módulos nuevos con cobertura completa | G9c3: leer el inventario guardado y `at_cut`; luego G9c4 (motor de métricas de Azure) y G9c5 (paridad con `eva1_db/`) |
| 03/11/2026 | Héctor (con Claude) | G9b: contrato JSON de EVA1 | Dashboard: `tests/contracts/test_eva1_contract.py` y `eva1_db/` | Cinco cuerpos y paquete de exportación congelados; 1,809 pruebas de contratos y portal | G9c: portar a `dashboard_management` `summary_iterations`, `at_cut` y la atribución de horas, `azure_history`, `dm_totals`, `eva2` y `select_view`, y comprobar contra `eva1_db/` copiado a `tests/datos/` de Genesis |
| 03/11/2026 | Héctor (con Claude) | G9a: contexto de EVA1 sin petición ni plantilla | Dashboard: `eva1_screen.py` y `views.eva1` | 387 pruebas de EVA, acceso y refresco; ruff y mypy | G9b: escenario sintético y contrato JSON de EVA1 (hay que armar fuentes, alcances y horas de Clockify). Luego G9c (portar cálculos) |
| 03/11/2026 | Héctor (con Claude) | G7 cerrado con Azure real; contraste AA de KPIs | Dashboard: exportador con microsegundos; Genesis: `management.css` (pestaña activa y degradado del encabezado) | Azure y EVA reales idénticos (conteos, JSON y campos); 536 textos por tema cumplen AA | Medir la carga en PostgreSQL (P2); G8 (espera P3) o G9 (EVA1); decidir si el encabezado conserva el degradado |
| 02/11/2026 | Héctor (con Claude) | G7: datos base en Genesis | Genesis, commit de G7 (local, sin push); Dashboard `852bd80` | Paridad con datos reales de Clockify y catálogos; 110 pruebas del módulo | Importar el grupo de Azure con datos reales y medir en PostgreSQL; luego G8 (trabajos de sincronización, espera P3 para credenciales) o G9 (EVA1) |
| 02/11/2026 | Héctor (con Claude) | G6: pantalla de KPIs de DM en React | Genesis, commit de G6 (local, sin push) | 633 pruebas de Vitest, cobertura y build; navegador con datos reales en claro, oscuro y 390 px | G6b (permisos, espera P1), medir contraste AA, y decidir el siguiente bloque (EVA1 o Capacidad). Antes de UAT: exportar e importar los demás grupos de tablas |
| 02/11/2026 | Héctor (con Claude) | G5: backend de KPI DM en Genesis | Genesis `e32c1f0` y commits siguientes (locales, sin push); Dashboard `bbd90e7`, `fc840ef` | Paridad con el dashboard en 6 consultas; 95 pruebas y 99 % de cobertura del módulo; suite de Genesis sin nuevas fallas (ver `odd/tasks/dashboard-management.md`) | G6: pantalla KPI DM en React; antes, importar `tmp/genesis-export-kpi` a una base local de Genesis para probar con datos reales |
| 02/11/2026 | Héctor (con Claude) | D3: comando de exportación | Dashboard, commit del comando `export_for_genesis` | Export real del grupo `kpi` verificado; 139 pruebas de datastore | D5 y G5 (modelos e importación de KPI DM en Genesis desde `tmp/genesis-export-kpi`, que no se sube a Git) |
| 02/11/2026 | Héctor (con Claude) | G4 en Genesis; D1, D2 y D4 de KPI DM en el dashboard | Genesis `070ab65` (local, sin push); Dashboard `d8242ee`, `f139547` | Servicio, hook y estados con 27 pruebas Vitest, build y cobertura en verde; contratos y refactor de KPI DM con 2955 pruebas de servidor, 473 de Node y 28 e2e de KPIs | D3 (comando de exportación), D5 (sincronizaciones sin hilos) y G5; el piloto necesita el export y P1 para sus permisos |
| 02/11/2026 | Héctor (con Claude) | G1–G3: rama al día, app `dashboard_management` y módulo `/management` con modo oscuro | Genesis `c2170d0`, `a471580`, `9b1afe7` (locales, sin push) | Vista comprobada en 3 temas y 390 px; backend 5250 pruebas y frontend 11 relacionadas en verde; límites de Windows documentados en `odd/tasks/dashboard-management.md` | G4 (servicio y estados) y D1–D5; esperar P1–P4. Decisión pendiente: el gradiente del encabezado choca con la regla 3 del sistema de diseño de Genesis |
| 02/11/2026 | Héctor (con Claude) | D6 terminado: tokens de modo oscuro | Dashboard, commit de `diseno-modo-oscuro.md` | Medición de colores por hoja (sección Diagnóstico) | Seguir con G1–G3 |
| 02/11/2026 | Héctor (con Claude) | Limpieza previa: 62 documentos históricos, transporte RPC de pruebas, fotos JSON del diseño y herramienta de carga | Dashboard `1f2759e`, `915bbfd`, `7499608` | Servidor 2928; Node 473; e2e 691 + 3 corregidas tras la corrida (33 en sus archivos) | Empezar D1/D3/D6 y G1–G3 |
| 02/11/2026 | Héctor (con Claude) | Revisión completa de Genesis, limpieza del dashboard, preguntas P1–P4, este plan | Dashboard `5b3d7f5` + commit de este plan | Node 473, servidor 1937, e2e capacidad 18 | Empezar D1/D3/D6 y G1–G3; esperar P1–P4 |
