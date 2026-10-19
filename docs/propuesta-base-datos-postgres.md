# Propuesta: base de datos PostgreSQL para el panel — 16/10/2026

Estado: **propuesta para revisión del equipo**. No hay código ni tablas
creadas.

## Objetivo

Que el frontend cargue toda la información desde una base de datos propia,
llenada al inicio de cada día, para que cambiar un filtro, recargar o entrar a
un módulo no dependa de Clockify, Google Sheets ni Azure DevOps. Cuando una
fuente cambia, la base se actualiza en segundo plano sin afectar lo que se
muestra.

## Mediciones que respaldan la propuesta

Medido el 16/10/2026 contra el workspace real de Clockify.

| Medición | Resultado |
| --- | --- |
| `warm_cache` con caché vacía (como hoy) | 1,150 s (19 min); 2,528 solicitudes HTTP |
| De esas, reportes de Clockify por proyecto | 2,480 (230 proyectos, 27 meses) |
| Reportes vacíos | 1,000 (40 %) |
| Reportes de meses futuros (nov-2026 a abr-2027) | 33 |
| `warm_cache` con las horas ya locales | 183 s (3 min); 5 solicitudes a Clockify |
| Reporte detallado JSON | Máximo 1,000 registros por página («Maximum page size is 1,000») |
| Registros por mes en todo el workspace | 15,000 a 24,000 |
| Reporte detallado CSV, 2026 completo (01/01-16/10) | 1 solicitud, 104 s, 49.3 MB, 164,036 registros |
| Reporte resumido de un mes (proyecto → tarea → usuario) | 1 solicitud, 3.4 s |
| Convertir el CSV anual a registros de horas | 14.5 s; indexar 1 s; recargar ya procesado 2.6 s |
| Consultar un proyecto-mes en la base indexada | 0.3 ms |

Conclusión: Clockify representa unos 16 de los 19 minutos de la precarga en
frío. Sheets, Azure y los cálculos son los 3 minutos restantes.

Clockify bloquea automáticamente los registros con más de 8 días
(`automaticLock: OLDER_THAN 8 DAYS`) y tiene aprobación de horas activa: lo
anterior a esa fecha no cambia salvo que un administrador lo desbloquee.

## Por qué PostgreSQL

| | Sheets | Excel | SQLite | PostgreSQL |
| --- | --- | --- | --- | --- |
| Capacidad | 10 millones de celdas: unos 2 años de horas | Lento con 164,000 filas | Suficiente | Suficiente |
| Lectura | Lenta, por API y bloques | Lenta | Milisegundos | Milisegundos |
| Varios procesos o servidores | Cuotas de la API | Bloqueo de archivo | Una sola máquina | Sí |
| Actualizar sin afectar la página | No | No | Transacciones | Transacciones y vistas materializadas concurrentes |
| Power BI y respaldos automáticos | — | — | Limitado | Sí |

Decisión: el panel se integrará a la plataforma Genesis, que usa PostgreSQL
Flexible Server en UAT/PROD y SQLite en local, con `dj-database-url`
(`DATABASE_URL`) y `psycopg2-binary` con `ssl_require=True`. Se usa lo mismo.

### Implicaciones del stack de Genesis

- Gunicorn con 3 workers en Azure App Service Linux (contenedor): la base debe
  ser compartida; no se cargan los datos en memoria de cada proceso.
- El contenedor no tiene Programador de tareas de Windows y su disco es
  efímero y por instancia: la caché en archivos (`.cache/`) se pierde al
  reiniciar. Los datos viven en PostgreSQL y la tarea diaria se dispara desde
  fuera (ver «Pendiente de verificar»).
- El frontend de Genesis es una SPA React que consume DRF. La capa de datos
  se escribe como servicios independientes de las plantillas, para exponerla
  después por API.

## Fuentes

| Grupo | Hojas o fuentes | Tratamiento |
| --- | --- | --- |
| Se cargan cada día (solo lectura) | Historico_Proyectos, MPB, ROC (y la tabla de topes «EVA-04 Report» o «ROC \| Desgloce por Bot AAAA»), DataRevenue, Proyectos, Recursos, Riesgos, Bandas/rol, Master rates, Backlog_Proyectos, CatalagoProyectos, Clockify_Vinculos, Clockify, Azure DevOps y tipo de cambio (open.er-api.com) | El frontend las lee solo desde la base |
| Se dejan de usar | `08.Base Clockify AAAA`, `GSE_Base_Control`, `Registros_Tiempo` | Las reemplazan `time_entry` y `clockify_month_sync` |
| Las escribe la aplicación (fase 3) | AER_*, IXS_*, Pendientes_Daily, Ajustes_UAT, Ajustes_Garantia, WorkItems_Avance, Minutas, Pendientes_Minutas, Comunicados, Areas_Reglas, Validaciones_IA_Clockify, hitos de Proyectos (columna L en adelante) | Pasan a tablas propias; la aplicación escribe en la base |

Los festivos se calculan en `apps/portal/services/holidays.py` y no requieren
tabla.

## Modelo

```text
CATALOGOS:   client ◄ client_alias      person ◄ person_alias      project ──► client, person
FUENTES:     project_stage   mpb_contract   roc_process   revenue_line   project_plan
             project_milestone   resource_assignment   risk   opportunity   exchange_rate
PERSONAS:    person_band_month   band_rate
CLOCKIFY:    clockify_project ◄ project_link   clockify_task   tag   time_entry ── time_entry_tag
             project_category
AZURE:       azure_team_project   azure_work_item   azure_iteration
RENDIMIENTO: hours_daily   hours_monthly (vista materializada)   precomputed_view
CONTROL:     sync_run   data_version   clockify_month_sync   raw_sheet_rows
```

Cada entidad compartida (cliente, persona, proyecto) se guarda una sola vez y
las fuentes la referencian. Las diferentes formas de escribir un nombre se
resuelven con tablas de alias, revisadas una vez, en lugar de buscar
coincidencias por nombre en cada cálculo.

### Catálogos compartidos

| Tabla | Columnas | Alimentada por |
| --- | --- | --- |
| `client` | id, name, country | MPB, ROC, Histórico, DataRevenue, Backlog, Clockify |
| `client_alias` | source, raw_name, client_id | Variantes del nombre por fuente |
| `person` | id, name, email (único), clockify_user_id, azure_unique_name, active | Bandas/rol, Recursos, Clockify, DM/AM de las hojas, Azure |
| `person_alias` | source, raw_name, person_id | Variantes del nombre por fuente |
| `project` | internal_id (único), name, client_id, service, delivery_manager_id, base_project_id, azure_team_project_id | Histórico A:I (principal), MPB para AER/T&M, ROC para procesos |

`base_project_id` relaciona las variantes `_CR`, `_CR1` o `_S2` con su
proyecto base.

### Datos de las hojas

| Tabla | Hoja | Columnas |
| --- | --- | --- |
| `project_stage` | Historico_Proyectos A:I + J | project_id, stage, is_estimate (filas EST), start, finish, budget_hours |
| `mpb_contract` | MPB | project_id, start, end, original_end, status, fte, budget_hours, burn_hours, horas por rol (DEV, ARQ, IA, SM, BA, TT, CR, DM) |
| `roc_process` | ROC y tabla de topes | project_id, bot_id, process_name, status, start, finish, monthly_limit_hours, limit_source, package_limit_hours, package_available_hours, risk, account_manager_id |
| `revenue_line` | DataRevenue | project_id (E), client_id, status (A), revenue_date (G), amount_usd (H), is_factoring |
| `project_plan` | Proyectos | project_id, product, scrum_master_id, status, priority, start, estimated_end, progress_pct, budget_hrs, burn_hrs, etc_hrs, risk_level, deviation_days, updated_at |
| `project_milestone` | Proyectos (L en adelante) | project_id, type, name, date, observation |
| `resource_assignment` | Recursos | person_id, project_id, role, assigned_hours_week, available_hours_week |
| `risk` | Riesgos | risk_code, project_id, description, impact, probability, status, owner_id, detected_on, review_on, mitigation, origin |
| `opportunity` | Backlog_Proyectos | client_id, name, service, stage, probability, amount, currency, amount_usd, expected_close, owner_id |
| `exchange_rate` | API de tipo de cambio | date, currency, rate_to_usd |
| `person_band_month` | Bandas/rol | person_id, month, band, role, status (vigente o BAJA) |
| `band_rate` | Master rates | band, rate_usd, valid_from |
| `project_category` | CatalagoProyectos | clockify_project_id, category |

`resource_assignment` guarda una fila por persona y proyecto; hoy
`Proyectos_Asignados` es una lista en una celda.

### Clockify

| Tabla | Columnas |
| --- | --- |
| `clockify_project` | clockify_id (único), name, client_id, archived |
| `project_link` | project_id, clockify_project_id, task_nomenclature (`CR`, `CR1` o vacío), source (manual o auto). Reemplaza la búsqueda por nombre y `Clockify_Vinculos` |
| `clockify_task` | clockify_id, clockify_project_id, name, status |
| `tag` | clockify_id, name, category (`INV_OPERATIVA`, `INV_COMERCIAL`, …) |
| `time_entry` | clockify_id (único), clockify_project_id, task_id, person_id, start_at, end_at, entry_date (día local), month, duration_seconds, billable, description, approval_status, custom_fields |
| `time_entry_tag` | time_entry_id, tag_id |
| `clockify_month_sync` | month, entries_count, total_seconds, downloaded_at, run_id |

### Azure DevOps

| Tabla | Columnas |
| --- | --- |
| `azure_team_project` | azure_id, name |
| `azure_work_item` | azure_id (único), team_project_id, project_id (por ID base y sufijo S/CR/QA), type, title, state, severity, probability, assigned_to_id, iteration_path, parent_id, changed_at |
| `azure_iteration` | team_project_id, path, start, finish |

### Rendimiento

| Tabla o vista | Contenido |
| --- | --- |
| `hours_daily` | project_id, person_id, task_id, date, billable, tag_category, seconds |
| `hours_monthly` | Vista materializada por proyecto, persona y mes; `REFRESH MATERIALIZED VIEW CONCURRENTLY` |
| `precomputed_view` | run_id, module, filters_key, payload (JSONB) |
| `open_risks` | Vista que une `risk` y `azure_work_item` de tipo Risk |
| `person_cost_month` | Vista de persona, mes, banda y tarifa para Finanzas |

### Control

| Tabla | Contenido |
| --- | --- |
| `sync_run` | kind (daily, change, manual_month, manual_current), status, started_at, finished_at, lock_date_seen, months_refreshed, error |
| `data_version` | Una fila con la corrida publicada que leen las páginas |
| `raw_sheet_rows` | run_id, sheet, row_number, data (JSONB). Se conservan las últimas 3 corridas |

## Buenas prácticas

- Tres capas: crudo (`raw_sheet_rows`, respuesta de Clockify), limpio
  (catálogos y fuentes) y agregado (`hours_daily`, `hours_monthly`,
  `precomputed_view`). Las páginas leen la capa agregada.
- IDs de Clockify, Azure y proyecto interno con restricción `UNIQUE`; llaves
  primarias numéricas internas.
- Llaves foráneas, `NOT NULL` y `CHECK (duration_seconds >= 0)`.
- Dinero en `Decimal(14,2)`; horas en segundos enteros, redondeadas al mostrar.
- `USE_TZ` activo, `start_at` con zona horaria y `entry_date`/`month`
  calculados en America/Mexico_City (igual que `REPORT_TIMEZONE`).
- Nombres nuevos sin alias van a una lista de pendientes, no se muestran como
  error.
- Índices en (project_id, date), (person_id, date), month y tag_category.
- Los valores calculados por la aplicación (salud, ETC, desviación) solo se
  guardan en `precomputed_view`.
- `JSONField` en lugar de `ArrayField`, para que las pruebas sigan corriendo
  con SQLite en el CI.

## Carga y actualización

```text
6:00, al detectar un cambio o con los botones:
  1. Tomar un candado (pg_advisory_lock): una sola corrida a la vez
  2. Leer las 13 hojas una vez → raw_sheet_rows
  3. Clockify: ventana abierta y meses que cambiaron → time_entry
  4. Azure: work items e iteraciones; API: tipo de cambio del día
  5. Normalizar → catálogos (alias) y tablas de cada fuente
  6. Recalcular hours_daily, hours_monthly y precomputed_view
  7. Validar contra el reporte resumido de Clockify
  8. Publicar data_version; todo dentro de una transacción
     Si algo falla: rollback, se conserva la versión anterior
```

- Clockify: reporte detallado JSON del workspace, 1,000 registros por página.
  La carga inicial puede usar CSV (2026 completo en 104 s). Cada mes se
  reemplaza completo (borrar e insertar) para reflejar registros borrados.
- Ventana diaria: los últimos ~10 días (mes actual y, antes del día 10, el
  anterior). 7-20 solicitudes, 15-40 s.
- Detección de cambios en meses bloqueados:
  1. Comparar `lockTimeEntries` con el valor anterior; si retrocede, volver a
     bajar desde esa fecha. 1 solicitud.
  2. Comparar horas y conteos por mes contra el reporte resumido. Solo se
     vuelve a bajar el mes que no cuadra. ~12 solicitudes, ~40 s.
- Botones: «Actualizar datos» (mes actual) y «Recargar mes» para
  administradores.
- Las páginas muestran «Datos al: fecha y hora» de la versión publicada y usan
  el ID de la versión en sus claves de caché.

Día normal estimado: ~30 solicitudes y 4-5 minutos, una vez al día.

## Cambios en el código

- Repositorio de lectura sobre PostgreSQL con la misma interfaz que
  `build_sheet_repository()`, para que los servicios del portal no cambien.
- `apps/clockify/services/time_entry_loader.py` arma los mismos `TimeEntry`
  desde `time_entry` en lugar de descargar reportes por proyecto.
- Se conserva la lógica de CR (`matches_cr_task`), tarifas y horas fuera de
  horario.
- Con el tiempo, los cálculos pesados pasan a consultas sobre `hours_daily`.
- Dependencias `psycopg2-binary` y `dj-database-url` (versiones de Genesis);
  conexión con `DATABASE_URL` en `.env`, `ssl_require=True` en Azure y
  `CONN_MAX_AGE`. Sin `DATABASE_URL` se usa el `db.sqlite3` local.

## Fases

0. Corregir la consulta de meses futuros en `_monthly_report`
   (`time_entry_loader.py`): elimina 33 solicitudes sin datos.
1. Base, carga diaria, control, catálogos con alias, Clockify y `hours_daily`.
2. Hojas del portal y Azure: Ejecutiva, Operativa, Comercial, EVA,
   Facturabilidad, Delivery Manager y Cuenta leen solo desde la base.
3. Hojas que escribe la aplicación pasan a tablas propias: el detalle de
   proyecto deja de depender de Sheets.
4. Dar de baja `08.Base Clockify AAAA`, `GSE_Base_Control` y
   `Registros_Tiempo`.
5. Medir cada módulo al cambiar filtros y precalcular los que superen 1-2 s.

## Pendiente de verificar

- Columnas reales de cada hoja. Los nombres provienen del código
  (`ejecutivo/constants.py`, `eva4.py`, `kpi_sources.py`, `revenue.py`,
  `sheet_schema.py`, `history_stages.py`); hay encabezados alternos, por
  ejemplo «Tope Mensual» o «Average Limit» en ROC.
- Columnas de Backlog_Proyectos y CatalagoProyectos.
- Uso de la hoja `Banda salarial` (está en la precarga de `warm_cache`) y si
  es distinta de Bandas/rol.
- Cómo se dispara la tarea diaria en App Service: pipeline programado de
  Azure DevOps, Azure Functions con temporizador o un job de contenedor que
  ejecute `manage.py sync_datastore`.
- Si la caché de Django en Genesis es compartida entre instancias; si no,
  `precomputed_view` en PostgreSQL sustituye la caché en archivos.
- Valores de `USE_TZ` y `TIME_ZONE` en `config/settings`.
- Comportamiento de `lockTimeEntries` cuando un administrador desbloquea:
  si queda vacío o con otra fecha.
- Si las tarifas de `memberships` de Clockify pueden sustituir alguna fuente.
- Si se conserva el dashboard anterior (`--legacy`); en ese caso se agregan
  Sprints y Dashboard_Historico_KPIs.
- Que el «menos de 1-2 s» al cambiar filtros se cumpla; se mide en la fase 5.
- Las hojas de la fase 3 se editan manualmente: moverlas implica capturar
  desde el panel.
- La base guardará nombres y correos del personal: definir acceso y
  respaldos.
