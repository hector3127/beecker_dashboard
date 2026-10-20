# Cómo se llena la base de datos

Este documento explica, paso por paso, **qué consulta `sync_datastore` a Google
Sheets, Clockify y Azure DevOps, y en qué tabla guarda cada cosa**. Se escribió
leyendo el código de `apps/datastore/` (no es una propuesta: describe lo que hay
en la rama `main`) y los conteos salen de la base local del 2026-10-20.

Para la propuesta original y las fases ver
[propuesta-base-datos-postgres.md](propuesta-base-datos-postgres.md); para
programar las ejecuciones ver [ejecucion-programada.md](ejecucion-programada.md).

---

## 1. Resumen en una tabla

| Paso (`--pasos`) | Fuente | Qué consulta | Tablas que llena | Frecuencia recomendada |
|---|---|---|---|---|
| `hojas` | Google Sheets | 1 consulta de metadatos + 1 lectura por lotes (`batchGet`) de 12 hojas | `SheetSnapshot` | cada hora |
| `azure` | Azure DevOps | Por cada Team Project: work items, RAID, campos de Risk e iteraciones | `AzureProject`, `AzureWorkItem`, `AzureIteration` | cada hora |
| `clockify` | Clockify | Un reporte detallado de **todo el workspace** por mes, más el bloqueo y los totales por mes | `ClockifyTimeEntry`, `ClockifyMonthSync` | cada día |
| `catalogos` | **Ninguna** (usa las hojas ya guardadas y las horas ya guardadas) | — | `Client`, `ClientAlias`, `Person`, `PersonAlias`, `Project` | con `hojas` y con `clockify` |
| (siempre) | — | — | `SyncRun` (bitácora de Clockify), `SyncLock` (candados) | — |

Orden de ejecución dentro de una corrida: **hojas → azure → clockify → catálogos**
(`STEPS` en `sync_datastore.py`).

```bash
# cada hora
python manage.py sync_datastore --pasos hojas,azure,catalogos
# cada día
python manage.py sync_datastore --pasos clockify,catalogos
# carga inicial (tarda cerca de una hora) y recargas puntuales
python manage.py sync_datastore --desde 2024-08
python manage.py sync_datastore --mes 2026-10
```

---

## 2. Cómo se dispara una corrida

`apps/datastore/management/commands/sync_datastore.py`

1. Se eligen los pasos (`--pasos`, `--solo-hojas`, `--solo-azure`, `--sin-hojas`,
   `--sin-azure`, `--sin-catalogos`; sin opciones corre todos).
2. **Cada paso toma un candado** en la tabla `SyncLock` (restricción `UNIQUE`,
   igual en SQLite y PostgreSQL). Si otra ejecución lo tiene, el paso se omite
   con un aviso. Si un proceso muere sin soltarlo, el candado vence solo:

   | Paso | Vence a los |
   |---|---|
   | hojas | 15 min |
   | azure | 30 min |
   | clockify | 3 h (la carga inicial tarda cerca de una hora) |
   | catálogos | 15 min |

3. Cada paso guarda **en una transacción**: las pantallas siguen viendo los
   datos anteriores hasta que termina y después ven los nuevos, nunca una
   mezcla.
4. Si algún paso falla, el comando termina con error (`CommandError`) al final,
   después de haber intentado los demás.

---

## 3. Clockify → `ClockifyTimeEntry` y `ClockifyMonthSync`

Código: `clockify_sync.py` (descarga y guardado), `change_detection.py`
(qué meses descargar), `retry.py` (reintentos).

### 3.1 Qué se pregunta a Clockify

| # | Llamada | Para qué | Cuántas |
|---|---|---|---|
| 1 | `GET https://api.clockify.me/api/v1/workspaces/{id}` | Leer `workspaceSettings.lockTimeEntries` (fecha hasta la que Clockify tiene bloqueados los registros) | 1 por corrida diaria |
| 2 | `POST https://reports.api.clockify.me/v1/workspaces/{id}/reports/summary` agrupado por `PROJECT` | Verificar que el total de cada mes guardado (registros y segundos) siga coincidiendo con Clockify | 1 por mes guardado que no se va a descargar de todos modos (hoy 27 meses) |
| 3 | `POST https://reports.api.clockify.me/v1/workspaces/{id}/reports/detailed` | Descargar los registros de un mes completo | 1 por página de 1,000 registros, por mes a descargar |

Cuerpo del reporte detallado (`build_month_payload`): rango del primer al último
día del mes en la zona `America/Mexico_City`, `pageSize: 1000` (el máximo de
Clockify), `sortColumn: ID`, sin redondeo, `amountShown: HIDE_AMOUNT`. Se
descarga **un solo reporte para todo el workspace por mes**, en vez de uno por
proyecto como hacía el modo en vivo.

Protecciones de la descarga (`download_month`):

- pausa de 0.25 s entre páginas;
- máximo 200 páginas por mes;
- si una página se repite, falta el campo `timeentries` o un registro no trae ID,
  **no se guarda el mes** (nunca se guarda un mes incompleto);
- `403` → error "La API key no tiene permiso para el reporte del workspace";
- fallas de conexión se reintentan 3 veces con espera de 5 s y 20 s; un código
  HTTP de error (403, 500…) no se reintenta;
- si la verificación de totales falla 3 veces seguidas por conexión, se omite el
  resto de la verificación hasta la siguiente corrida (es opcional).

### 3.2 Qué meses se descargan (corrida diaria, `plan_daily`)

Clockify bloquea los registros con más de 8 días, pero un administrador puede
desbloquear y editar meses antiguos. Por eso cada día se revisan dos cosas:

1. **La fecha de bloqueo** (`lockTimeEntries`):
   - sin lectura posible → solo la ventana abierta;
   - sin bloqueo (`""`) → se revisan **todos** los meses guardados;
   - con bloqueo anterior a la ventana → desde el mes del bloqueo hasta hoy;
   - si no, la **ventana abierta**: los meses de los últimos 10 días (el actual
     y, a principios de mes, el anterior).
2. **Los totales por mes**: se compara cada mes guardado contra el reporte
   resumido (registros y segundos). El mes que no cuadra se vuelve a descargar.
   Cubre ediciones hechas mientras el mes estuvo desbloqueado y que se
   bloquearon de nuevo antes de la siguiente corrida.

Otras corridas: `--mes AAAA-MM` (recarga un mes, tipo `manual_month`) y
`--desde AAAA-MM [--hasta AAAA-MM]` (carga inicial, tipo `backfill`).
`--sin-verificar` omite la comparación de totales.

### 3.3 Cómo se guarda (`save_month`)

Por mes, en una transacción: se **borran** los registros de ese mes
(`ClockifyTimeEntry.month = mes`), se insertan los nuevos en lotes de 2,000 y se
actualiza `ClockifyMonthSync`. Un registro cuyo inicio cae en otro mes se deja
para ese mes. Un mes que falla no borra a los demás.

#### Campo por campo: reporte de Clockify → `ClockifyTimeEntry`

| Columna | De dónde sale en el JSON del reporte |
|---|---|
| `entry_id` (llave primaria) | `_id` o `id` |
| `project_id` | `projectId` / `project.id` |
| `project_name` | `projectName` / `project.name` |
| `task_id`, `task_name` | `read_task_id` / `read_task_name` (campos de tarea del reporte) |
| `user_id`, `user_name` | `userId` / `user.id`, `userName` / `user.name` |
| `tags` | nombres de las etiquetas (`read_tag_names`) |
| `description` | `description` |
| `billable` | `billable` |
| `start`, `end` | `timeInterval.start` y `.end`, tal cual (ISO 8601) |
| `entry_date` | día local (México) de `timeInterval.start` |
| `month` | primer día del mes de `entry_date` |
| `duration_seconds` | `timeInterval.duration` convertido a horas y luego `round(horas × 3600)` |

Índices: `(project_id, month)`, `(user_id, entry_date)` y `(month)`. Restricción:
`duration_seconds >= 0`.

#### `ClockifyMonthSync` (una fila por mes guardado)

`month` (único), `entries_count`, `total_seconds`, `synced_at` y la corrida
(`run`) que lo guardó. Es la referencia contra la que se compara el reporte
resumido, y la lista de meses que las pantallas pueden leer de la base: **un mes
que no está aquí se sigue leyendo de Clockify en vivo**.

#### `SyncRun` (bitácora)

Una fila por corrida de Clockify: `kind` (`daily`, `backfill`, `manual_month`),
`status` (`running`, `ok`, `failed`), inicio y fin, `months`, `entries`,
`requests`, `error`, la `lock_seen` (fecha de bloqueo vista) y `notes` (por qué
se eligieron esos meses).

---

## 4. Google Sheets → `SheetSnapshot`

Código: `sheet_sync.py`. Lee siempre de Google (`build_sheet_repository(use_store=False)`),
nunca de la base.

### 4.1 Qué se pregunta a Google

1. Los **metadatos del Spreadsheet** (nombres e IDs de las pestañas), para saber
   qué hojas existen.
2. **Una lectura por lotes** (`values.batchGet`, `valueRenderOption=UNFORMATTED_VALUE`,
   `dateTimeRenderOption=SERIAL_NUMBER`) con las hojas que existen de la lista
   de abajo.

### 4.2 Las 12 hojas guardadas (`STORED_SHEETS`)

| Hoja | Filas hoy | Para qué la usa el portal (resumen) |
|---|---|---|
| `Proyectos` | 176 | Detalle de proyectos (cliente, scrum master, servicio) |
| `Historico_Proyectos` | 1,381 | Línea de tiempo de etapas (A:J operativo; L:… ID exacto y cliente) |
| `MPB` | 821 | Contratos/presupuesto y burn por proyecto |
| `ROC` | 228 | Procesos ROC activos |
| `DataRevenue` | 4,587 | Facturación/ingresos por proyecto y fecha |
| `Recursos` | 90 | Asignación de personas a proyectos |
| `Riesgos` | 12 | Riesgos capturados |
| `Bandas/rol` | 247 | Banda y rol por persona, con su ID de Clockify |
| `Master rates` | 11 | Tarifas por banda |
| `Banda salarial` | 239 | Salarios por banda y persona |
| `Backlog_Proyectos` | 1,590 | Oportunidades comerciales |
| `CatalagoProyectos` | 507 | Catálogo de proyectos con cliente y servicio |

No entran las hojas grandes de Clockify: esas horas viven en `ClockifyTimeEntry`.

### 4.3 Cómo se guarda

Cada hoja es **una fila** de `SheetSnapshot`: `name` (único), `rows` (la matriz
completa como JSON), `row_count` y `synced_at`. Se guardan todas en **una sola
transacción**. Una hoja que ya no existe en el Spreadsheet se omite y **su copia
anterior se borra**. Además se guarda una fila especial `__sheet_ids__` con el
diccionario nombre → ID de pestaña.

Una hoja que no está en esta lista **se sigue leyendo de Google**, con la caché
normal (por ejemplo `Clockify_Vinculos`).

---

## 5. Azure DevOps → `AzureProject`, `AzureWorkItem`, `AzureIteration`

Código: `azure_sync.py` (lectura) y `azure_store.py` (guardado). Las llamadas
HTTP corren en hilos (hasta 4 a la vez, `MAX_PARALLEL_REQUESTS`) y **solo el hilo
principal escribe** en la base.

### 5.1 Qué se pregunta a Azure DevOps (API 7.1)

| Llamada | Para qué |
|---|---|
| `GET {org}/_apis/projects` (hasta 500) | Lista de Team Projects |
| `POST {proyecto}/_apis/wit/wiql` con `SELECT [System.Id] … ORDER BY [System.ChangedDate] DESC` | IDs de los work items del proyecto (se toman los **1,000 más recientes**) |
| `GET {proyecto}/_apis/wit/workitems?ids=…` en lotes de **180** | Detalle de esos work items |
| `POST {proyecto}/_apis/wit/wiql` filtrado a `Risk`/`Opportunity` en estado `Active`/`Proposed` | IDs del RAID |
| `GET {proyecto}/_apis/wit/workitems?ids=…&$expand=fields` en lotes de 180 | Detalle del RAID con todos sus campos (un lote fallido se omite) |
| `GET {proyecto}/_apis/wit/workitemtypes/Risk/fields` | Campos del tipo Risk (si falla, el proyecto se guarda con `risk_fields_ok = false`) |
| `GET {proyecto}/_apis/wit/classificationnodes/iterations?$depth=15` | Árbol de iteraciones/sprints |

Autenticación: token personal (PAT) en cabecera Basic.

### 5.2 Cómo se guarda (`save_project`)

Por proyecto, en una transacción, se **reemplaza todo lo suyo**:

- `AzureProject` (`name` único): `position` (lugar en la lista de Azure),
  `risk_fields`, `risk_fields_ok`, `raid_version` (versión del RAID en la caché
  cuando se guardó) y `synced_at`.
- `AzureWorkItem`: `kind` = `latest` (los 1,000 más recientes) o `raid`;
  columnas de consulta (`work_item_id`, `item_type`, `state`, `title`,
  `iteration_path`, `assigned_to`, `changed_at`) **y `payload`**, que es la
  respuesta de Azure sin tocar. Por eso lo que lee el gateway de la base es
  idéntico a lo que leería en vivo.
- `AzureIteration`: `name`, `path`, `start_date`, `finish_date` y su `payload`.

Reglas de seguridad:

- un proyecto que **falla conserva su copia anterior** (se avisa en la salida);
- los proyectos que ya no existen en la organización **se borran** (solo en
  corridas completas, no con `only=`);
- si no se pudo leer ningún proyecto, la corrida marca error;
- si Azure no está configurado (`AzureDevOpsConfigurationError`) el paso se
  omite con aviso y no es un error.

---

## 6. Catálogos con alias → `Client`, `ClientAlias`, `Person`, `PersonAlias`, `Project`

Código: `catalogs.py`. **No consulta Google ni Clockify**: se arma con las filas
de `SheetSnapshot` ya guardadas y con los usuarios de `ClockifyTimeEntry`. Si no
hay hojas guardadas, el paso solo avisa.

Cada cliente, persona y proyecto se guarda **una sola vez**. Las hojas lo
escriben distinto (acentos, mayúsculas, espacios dobles, `GPO.001_ CR`); el
catálogo agrupa esas variantes por su forma normalizada y guarda cada una como
alias. Una variante se une a otro registro cambiando su alias en el admin: queda
como **manual** y las siguientes sincronizaciones la respetan.

Cada lectura de columna verifica el **encabezado esperado**: si ya no está en esa
columna, se omite y se avisa (en lugar de leer otra columna).

### 6.1 Clientes (`Client`, `ClientAlias`)

| Hoja | Columna (base 0) | Encabezado esperado |
|---|---|---|
| Proyectos | 2 | Cliente |
| Historico_Proyectos | 1 y 11 | Account / Client |
| MPB | 1 | CLIENTE |
| ROC | 0 | Client |
| DataRevenue | 1 | Cliente |
| Backlog_Proyectos | 0 | Account Name |
| CatalagoProyectos | 7 | Cliente |

### 6.2 Personas (`Person`, `PersonAlias`)

| Hoja | Columna | Rol que se anota |
|---|---|---|
| Proyectos | 4 (Scrum_Master) | `scrum_master` |
| Historico_Proyectos | 0 y 10 (Delivery Manager) | `delivery_manager` |
| MPB | 20 (Delivery Manager) | `delivery_manager` |
| ROC | 10 (Account Manager) / 11 (Delivery Manager) | `account_manager` / `delivery_manager` |
| Backlog_Proyectos | 2 (Delivery Manager) | `delivery_manager` |
| Recursos | 2 (Nombre del recurso) | `recurso` |
| Bandas/rol | 0 (Nombre) | `recurso` |
| Banda salarial | 0 (Nombre) | `recurso` |

Además: el **ID de Clockify** de cada persona sale de `Bandas/rol` (columna 2,
"ID Clockify"), y los usuarios distintos que registraron horas en
`ClockifyTimeEntry` se agregan con el rol `usuario_clockify` (si la persona no
tiene ID en `Bandas/rol`, se usa el de Clockify).

### 6.3 Proyectos (`Project`)

Clave: `internal_id` (único); `base_id` es el ID sin sufijos `S#`, `CR#` o `QA#`.
Solo se aceptan IDs con forma `AMK.008`, `ROC.AIN.001`, `AIN.001_S1`; conceptos
como `TBD` o `Viaticos` se descartan (se cuentan en `skipped_ids`). **El orden
manda: la primera hoja que trae un dato (nombre, servicio, cliente, manager) lo
fija.**

| Orden | Hoja | ID | Nombre | Servicio | Cliente | Manager |
|---|---|---|---|---|---|---|
| 1 | Proyectos | 0 | 1 | 3 | 2 | — |
| 2 | Historico_Proyectos | 2 | 4 | 3 | 1 | 0 |
| 3 | MPB | 2 | 4 | 5 | 1 | 20 |
| 4 | ROC | 3 (ROC ID) | — | 5 | 0 | 11 |
| 5 | ROC | 4 (BOT ID) | — | 5 | 0 | 11 |
| 6 | DataRevenue | 4 | — | 3 | 1 | — |
| 7 | CatalagoProyectos | 3 | — | 8 | 7 | — |

`sources` guarda en qué hojas apareció el proyecto y `spellings` cómo se escribió.
Los proyectos que ya no aparecen en ninguna hoja **se borran**.

---

## 7. Qué NO llena la base (sigue en vivo)

- **Azure DevOps de Daily e IXS**: esos módulos consultan Azure directamente.
- **Lista de proyectos y tareas de Clockify** (`GET /projects`, `GET /tasks`): no
  se guardan.
- **Hojas que no están en `STORED_SHEETS`**, como `Clockify_Vinculos`.
- **Tipo de cambio (FX)**: sigue consultando la API externa.
- **Escrituras a Sheets** (por ejemplo, llenar el Burn en MPB): siempre van a
  Google.
- Las **tablas normalizadas por hoja** (`project_stage`, `mpb_contract`,
  `roc_process`, `revenue_line`) **no se construyeron**: hoy cada hoja se guarda
  completa en una fila de `SheetSnapshot`.

---

## 8. Quién lee cada tabla

| Tabla | La lee | Bandera |
|---|---|---|
| `ClockifyTimeEntry` / `ClockifyMonthSync` | `time_entry_loader` (`_stored_month`), `stored_base` (base de horas de GSE, Facturabilidad), `eva4_index` | `CLOCKIFY_STORE_ENABLED=1` |
| `SheetSnapshot` | `StoredSheetReadCache`, que usa `build_sheet_repository` | `SHEETS_STORE_ENABLED=1` |
| `AzureProject` / `AzureWorkItem` / `AzureIteration` | `AzureDevOpsGateway` (`stored_*`) | `AZURE_STORE_ENABLED=1` |
| `Client`, `Person`, `Project` y sus alias | Admin de Django y el resto de la base; las pantallas aún no dependen de ellos | — |

Las banderas se leen con `== "1"`: **solo vale `1`**; `true`, `yes` o la variable
vacía la dejan apagada sin avisar. Un mes de Clockify que no está en
`ClockifyMonthSync` se sigue leyendo de Clockify.

Frescura: `python manage.py check_datastore` falla si las hojas o Azure pasan de
3 h sin sincronizarse, o si el mes actual de Clockify pasa de 30 h
(`--hojas-horas`, `--azure-horas`, `--clockify-horas`).

---

## 9. Para qué sirve cada tabla: qué muestra la interfaz y cómo lo obtiene

La relación tabla → pantalla sale de **qué módulos leen cada dato**
(`apps/portal/services/`, `apps/ejecutivo/`, `apps/capacidad/`,
`apps/gse/`, `apps/azure_devops/`) y de las rutas de `apps/portal/urls.py`. No se
verificó pantalla por pantalla con la aplicación corriendo.

### 9.1 Los tres caminos de lectura

| Dato | Camino cuando la bandera está en `1` | Si la bandera está apagada o el dato no está |
|---|---|---|
| **Hojas** | Pantalla → servicio → `build_sheet_repository()` → `StoredSheetReadCache.get_values(hoja)` → `SheetSnapshot.rows` | Se lee de Google con la caché normal |
| **Horas** | Pantalla → servicio → `build_clockify_loader()` → `ClockifyTimeEntryLoader._stored_month(proyecto, mes)` → `ClockifyTimeEntry` filtrado por proyecto y mes. Solo si el mes está en `ClockifyMonthSync` | Reporte de Clockify en vivo, proyecto por proyecto |
| **Horas para GSE y EVA-4** | `stored_base` agrega `ClockifyTimeEntry` por mes, persona, tarea y etiquetas (sustituye a la hoja «08.Base Clockify AAAA», de 164,000 filas que se recorrían celda por celda) | Esa hoja de Sheets |
| **Azure** | Pantalla → servicio → `AzureDevOpsGateway.stored_*()` → `AzureWorkItem`/`AzureIteration`; devuelve el `payload` sin tocar | API de Azure en vivo |

En todos los casos la pantalla recibe **la misma estructura** que recibiría de
la fuente original; la base solo cambia de dónde sale.

### 9.2 `SheetSnapshot`: una fila por hoja

| Hoja | Qué datos aporta | Dónde se ve |
|---|---|---|
| `Proyectos` | Registro de cada proyecto: cliente, scrum master, servicio, estado, fechas y presupuesto | Pantalla de **Proyecto**, **Delivery Manager**, KPIs de Delivery Managers y la precarga de costos |
| `Historico_Proyectos` | Etapas de cada proyecto y fechas (línea de tiempo A:J; ID y cliente exactos en L:M) | **Proyecto**, **Cuenta**, KPIs históricos por mes y trimestre, población de proyectos de Operations (ETC) y el inventario de costos |
| `MPB` | Contratos y presupuesto de horas, burn guardado, fechas de inicio y fin | **EVA 3** (proyectos AER y T&M), **Cuenta**, ETC/FTE de **Business Overview**, **Capacidad instalada** |
| `ROC` | Procesos ROC: estado, inicio y fin, bot asociado, Account/Delivery Manager | **EVA-04** (automatización, renovaciones y procesos), **Cuenta** (proyectos ROC), **Capacidad instalada** |
| `DataRevenue` | Facturación por cliente, proyecto, estado y fecha (columnas G y H) | **Business Overview** (facturación, cobranza, rentabilidad mensual, ranking 70/30), **Todas las cuentas**, **Detalle de costos**, **Cuenta** |
| `Recursos` | Asignación de personas a proyectos | **Capacidad instalada**, **Facturabilidad**, costos |
| `Riesgos` | Riesgos capturados por proyecto | Pantalla de **Proyecto** y KPIs |
| `Bandas/rol` | Banda y rol de cada persona por mes y su ID de Clockify | **Costos** (para saber la tarifa), **Capacidad instalada**, **Facturabilidad** |
| `Master rates` | Tarifa por banda | **Costos**: horas × tarifa |
| `Banda salarial` | Salarios por banda y persona | **Costos** y KPIs |
| `Backlog_Proyectos` | Oportunidades comerciales (ganadas y abiertas) | **Comercial** y el bloque comercial de **Business Overview** (booking y oportunidades abiertas, en USD con el tipo de cambio) |
| `CatalagoProyectos` | Catálogo de proyectos con cliente y servicio | Refresco de GSE y construcción de los catálogos |

### 9.3 `ClockifyTimeEntry` y `ClockifyMonthSync`: las horas

Cada fila es un registro de tiempo (quién, qué proyecto, qué tarea, qué día,
cuántos segundos, etiquetas, facturable). Con ellas se calculan:

- **Costos** de Business Overview, Todas las cuentas y Detalle de costos: horas
  del periodo × tarifa de la banda de la persona, sin duplicar el ID de registro.
- **Consumo (burn) y avance** de cada proyecto en **EVA 1, 2 y 3**, **Proyecto**,
  **Delivery Manager** y **Cuenta**.
- **ETC y FTE** de Business Overview: presupuesto de horas menos horas consumidas.
- **Facturabilidad** (global, por especialidad y por recurso) y **Capacidad
  instalada**: horas facturables frente a la capacidad del equipo.
- **Inversión operativa y comercial**: horas por categoría, según las etiquetas
  del registro.
- **EVA-04**: consumo por tarea y mes.

`ClockifyMonthSync` no se muestra: es el control. Dice qué meses puede servir la
base (los que no están se piden a Clockify en vivo) y su sello entra en las
llaves de la caché para que una sincronización invalide las páginas guardadas
con la base anterior.

### 9.4 `AzureProject`, `AzureWorkItem` y `AzureIteration`

- **EVA 2** (proyectos IXB y RaaS): el avance sale de los work items y de las
  iteraciones; se combina con el histórico de etapas y las horas de Clockify.
- **Proyecto**: etapas, work items, sprints y riesgos/oportunidades (RAID) del
  Team Project que corresponde al proyecto (se resuelve por nombre normalizado).
- **Delivery Manager** y la tarjeta de Operations de Business Overview: avance y
  consumo de sus proyectos IXB/RaaS.
- El RAID se lee con la versión (`raid_version`) que tenía la caché al guardarlo,
  para no mostrar un RAID anterior a una limpieza.

### 9.5 Catálogos, bitácora y candados

- `Client`, `Person`, `Project` y sus alias: **hoy ninguna pantalla los lee**
  (solo importan `apps.datastore` el gateway de Azure, el cargador de Clockify,
  la base de horas de GSE y el índice de EVA-04). Sirven para unificar nombres
  y se administran en el admin de Django.
- `SyncRun`, `SyncLock`: control interno y revisión con `check_datastore`; no se
  muestran en el portal.

### 9.6 Lo que la interfaz sigue leyendo de Google aunque las banderas estén en `1`

Hojas que usa el código pero **no** están en `STORED_SHEETS` (lista completa
en `core/sheets/sheet_names.py`):

| Hoja | Quién la lee |
|---|---|
| `Sprints`, `Dashboard_Historico_KPIs` | La carga del portafolio (`DASHBOARD_SHEETS`) que alimenta la página de **Proyecto** |
| `Clockify_Vinculos` | El cargador de Clockify, para ligar un ID de proyecto con su proyecto de Clockify (afecta a todo lo que pide horas) |
| `Minutas` | El módulo de minutas y el dashboard ejecutivo de proyecto (`project_orchestrator`) |

Por eso la página de **Proyecto**, el emparejamiento de proyectos con Clockify
y las minutas **siguen dependiendo de Google** y de su caché, aunque las tres
banderas estén en `1`. Para quitar esa dependencia hay que agregar esas hojas a
`STORED_SHEETS`.

---

## 10. Tamaño actual de la base local (2026-10-20)

| Tabla | Filas |
|---|---|
| `ClockifyTimeEntry` | 529,837 |
| `ClockifyMonthSync` | 27 (2024-08 a 2026-10) |
| `SheetSnapshot` | 13 (12 hojas + `__sheet_ids__`) |
| `AzureProject` | 111 |
| `AzureWorkItem` | 39,114 (39,097 `latest` + 17 `raid`) |
| `AzureIteration` | 760 |
| `Client` / `ClientAlias` | 257 / 257 |
| `Person` / `PersonAlias` | 293 / 293 |
| `Project` | 1,790 |
| `SyncRun` | 5 |

Tiempos medidos en esta máquina: corrida horaria (hojas + Azure) ≈ 57 s; corrida
diaria de Clockify ≈ 161 s. La carga inicial de Clockify (≈ 530 mil registros en
27 meses, unas 530 páginas de 1,000) tarda cerca de una hora. Los números
dependen de la red y de la API de reportes de Clockify, que tiene picos
intermitentes.

## 11. Límites conocidos

- Con PostgreSQL aún no se probó el llenado completo (solo SQLite).
- PostgreSQL no admite el carácter NUL en textos: se buscó en los datos y hay 0
  casos, pero una captura futura con ese carácter haría fallar el guardado.
- Si un administrador edita Clockify sin desbloquear ni cambiar totales
  (por ejemplo, intercambiar horas entre dos registros del mismo mes), la
  comparación por totales no lo detecta; se corrige en la siguiente recarga del
  mes.
