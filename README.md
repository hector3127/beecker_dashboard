# Beecker Dashboard (Django)

Migración a Python/Django del dashboard Beecker que hoy vive en Google
Apps Script. Los datos **siguen en Google Sheets**; Django reemplaza la
lógica de los archivos `.gs` y sirve el mismo panel HTML.

La estructura sigue el orden de `qa_automation_platform`
(`config/`, `apps/<modulo>/services`, `schemas`, `exceptions`) y el
manual de buenas prácticas **MCR_PY v03**.

## Important tips

- El panel original (`index.html`, `js_main.html`, `view_*.html`) se
  copió sin cambios a `templates/legacy/`. El archivo
  `core/static/core/js/gas_shim.js` imita `google.script.run`, así que
  cada llamada del frontend llega a `POST /api/rpc/<nombreFuncion>/`.
- Las funciones que todavía no se migran responden
  `ERR_RPC_NOT_MIGRATED` y el panel muestra el error en su
  `withFailureHandler`, sin romper las demás vistas.
- Cada función migrada se registra con **el mismo nombre que tenía en
  Apps Script** (`@register_rpc("getDashboardData")`) y regresa **el
  mismo JSON**, para no tocar el frontend.
- El Spreadsheet se comparte con el correo de la cuenta de servicio
  (`key.json`) con permiso de **editor**.
- Con `TIME_ENTRY_SOURCE=clockify` las horas salen del reporte detallado
  de Clockify. Llena `CLOCKIFY_API_KEY` y `CLOCKIFY_WORKSPACE_ID`; para
  ver el ID del workspace corre `python manage.py clockify_workspaces`.
- Los vinculos manuales ID interno -> proyecto de Clockify que en Apps
  Script vivian en PropertiesService ahora van en la hoja opcional
  `Clockify_Vinculos` (columnas `ID_Proyecto` y `Clockify_Project_ID`).
- Igual que el original, si un proyecto no tiene rango de fechas o no
  coincide en Clockify, la carga completa falla y se muestra el ultimo
  respaldo (hasta 6 horas) con una alerta.
- Los IDs de trazabilidad `BKD.xxx.yyy` de cada módulo son provisionales:
  reemplázalos por los IDs del DFR/DAT del proyecto (manual 4.3).

## Requirements

- Python 3.12 (`.python-version`) y uv 0.12.7 o pip.
- Dependencias fijadas en `pyproject.toml` / `requirements.txt` según el
  stack tecnológico: Django 5.2.3, djangorestframework 3.16.0,
  gunicorn 25.3.0, whitenoise 6.9.0, python-dotenv 1.0.1,
  requests 2.32.4, anthropic 0.84.0, google-api-python-client 2.200.0,
  google-auth 2.57.1.
- Desarrollo: ruff 0.16.7, mypy 2.3.1 (strict) con django-stubs 6.1.0 y
  djangorestframework-stubs 3.18.1, pytest 9.1.1, pytest-django 4.14.0,
  pytest-cov 7.1.0 (mínimo 80 %), pytest-mock 3.15.1, freezegun 1.5.5.

Instalación:

```bash
uv sync                       # o: pip install -r requirements-dev.txt
copy .env.example .env        # y llena los valores
python manage.py migrate      # solo sesiones y usuarios de Django
python manage.py init_sheets  # crea hojas faltantes (Setup.gs)
python manage.py clockify_workspaces  # muestra el ID del workspace
python manage.py warm_cache   # precalienta la cache (ver abajo)
python manage.py runserver
```

## Functions

| Apps Script | Django | Estado |
|---|---|---|
| `Config.gs` (`SHEETS`, `getSecret`) | `core/sheets/sheet_names.py`, `.env` + `config/settings` | Migrado |
| `Sheetservice.gs` (`readSheetAsObjects`, `upsertRow`, `appendHistorico`, `logAutomatizacion`) | `core/sheets/repository.py`, `core/sheets/audit.py` | Migrado |
| `Setup.gs` (`inicializarSistema`) | `python manage.py init_sheets` | Migrado |
| `Código.gs` (`doGet`, `include`, `getFiltrosDisponibles`) | `core/views.py`, `templates/`, `apps/dashboard/rpc.py` | Migrado |
| `ProyectosService.gs` (`getDashboardData` y auxiliares) | `apps/dashboard/services/*` | Migrado |
| `RecursosDetalleService.gs` (`leerRegistrosTiempo`, tarifas) | `core/time_entries/` (incluye `resource_rates.py`) | Migrado |
| `RecursosDetalleService.gs` (vista de Recursos: `getResumenRecursos`, `getProyectosConHoras`, `getPersonasConHoras`, `obtenerProyectosAsignadosPersona`, `getDetallePersona`) | `apps/recursos/` | Migrado |
| `ClockifyService.gs` (horas por proyecto, reporte detallado, `obtenerConfigClockify`, `listarWorkspacesClockify`) | `apps/clockify/` | Migrado (sin la consulta alterna por usuario cuando el reporte da 403) |
| `MinutasService.gs`, `MinutasViewService.gs` | `apps/minutas/` + `python manage.py scan_minutes` | Migrado |
| `CapacidadInstaladaService.gs` (`capacidadInstaladaBase`, `capacidadInstaladaDatosProyecto`) | `apps/capacidad/` | Migrado |
| `GSEService.gs` (lecturas: `gseObtenerAreas`, `gseObtenerMes`, `gseObtenerAnoBase`, `gseObtenerLoteBase`, `gseLeerResultadoCache`, `gseGuardarResultadoCache`) y `CapacidadInstalada.html` con la pestana GSE | `apps/gse/` | Migrado (la descarga por API Clockify no guarda todavia la base en Sheets) |
| `GSEService.gs` (`gseBaseGuardar_`) y `ClockifyIDsService.gs` (`gseObtenerIDsClockify`) | `apps/gse/` | Pendiente (escriben en Sheets) |
| `ResumenAltoNivelService.gs` (`obtenerTopRiesgosPortafolioAzure`, `obtenerRaidProyectoEjecutivoAzure`) | `apps/azure_devops/` | Migrado |
| `DailyPanelService.gs` (`obtenerResumenAERTYMMPB`, `obtenerConsumosResumenAERTYMMPB`) | `apps/ejecutivo/` | Migrado |
| `ResumenAltoNivelService.gs` (`obtenerResumenIXBRaaS`) y `calcularHitosProyecto` | `apps/ejecutivo/` | Migrado |
| `ProyectoEjecutivoService.gs` (`getDashboardEjecutivoProyecto`, `obtenerHitosAdicionales`) y `getDetalleProyectoCompleto` | `apps/ejecutivo/` | Migrado (incluye `guardarHitosAdicionalesLote`, `editarHitoAdicional`, `eliminarHitoAdicional`, `obtenerTiposHitosExistentes`, `agregarRiesgoManual`) |
| `DailyPanelService.gs` (configuracion de Azure, work items, riesgos, pendientes, ajustes UAT/Garantia, avance de work items) | `apps/daily/` | Migrado |
| `DailyPanelService.gs` (panel IXS: `obtenerPanelAzureProyectoIXS`, `ixsRaidListarProyecto`, `ixsRaidCamposTipo`, `ixsRaidAltaOpciones`, `ixsRaidCrearRegistro`) | `apps/daily/` | Migrado |
| `DailyPanelService.gs` (vista IXS: `ixsClienteAcciones*`, contactos, info, gobierno, documentos, acciones y pendientes, `ixsRecursos*`, `ixsPlan*`, `beeComListar`, `beeComGuardar`) | `apps/daily/` | Migrado |
| `DailyPanelService.gs` (vista de cuenta Beecker: `obtenerVistaCuentaBeecker`, `obtenerOportunidadesCuentaBeecker`, `beeCuentaGuardarOportunidad`, `obtenerConsumosMPBCuenta`) | `apps/ejecutivo/` | Migrado |
| `AERTYMProyectoService.gs` (`getDashboardAERTYMProyecto`, `getRegistrosClockifyAERRango`, planeacion, riesgos, acciones, vacaciones, evaluaciones y cliente: 28 funciones) | `apps/aer/` | Migrado |
| `AERIAService.gs` (IA por proyecto AER/T&M: analisis, resumen ejecutivo, preguntas, correos y minutas con Claude; carpeta de minutas en Drive; pendientes Beecker / Cliente: 18 funciones) | `apps/aer/services/ai_*.py`, `apps/aer/ai_rpc.py` | Migrado (sin prueba en vivo de Claude) |
| `ClockifyService.gs` (vistas de proyecto: `obtenerRangoClockifyProyecto`, `obtenerEtapasHistoricoAIProyecto`, `getRegistrosClockifyProyecto`, `obtenerResumenTasksTagsClockifyProyecto`; diagnosticos: `diagnosticoClockify`, `diagnosticoClockifyCompleto`; `guardarApiKeyClockify`, `guardarWorkspaceClockify`; panel de conexion: `listarProyectosClockify`, `guardarVinculoProyectoClockify`, `diagnosticarConexionClockifyProyecto`, `diagnosticarHorasClockifyProyecto`) | `apps/clockify/services/project_views.py`, `apps/clockify/services/diagnostics.py`, `apps/clockify/services/connection_panel.py`, `apps/clockify/project_rpc.py` | Migrado |
| `ClockifyService.gs` (validacion de registros: `obtenerRegistrosMalRegistrados`, `obtenerAreasReglas`, `guardarAreaRegla`, `eliminarAreaRegla`, `limpiarValidacionesIAClockify`, `_validarReglaAreaConIA`) | `apps/clockify/services/entry_validation.py`, `apps/clockify/validation_rpc.py` | Migrado (sin prueba en vivo de la regla con Claude) |
| `DailyPanelService.gs` (Claude: `guardarApiKeyClaude`, `obtenerConfigClaude`, `guardarPromptPersonalizadoClaude`, `generarSugerenciaRiesgoConClaude`, `ixsRaidGuardarPrompt`, `ixsRaidObtenerPrompt`, `ixsRaidSugerirClaude`) | `apps/daily/` + `core/integrations/claude_client.py` | Migrado |
| `DailyPanelService.gs` (IA IXS: `ixsIAAnalizar`, `ixsIAPreguntar`, `ixsIAAnalisisLeer`, `ixsIAMemoria*`, `ixsIAMinuta*`, `ixsIADrive*`) | `apps/daily/` | Migrado |

Equivalencias de servicios de Google:

| Apps Script | Django |
|---|---|
| `SpreadsheetApp` | `GoogleSheetRepository` con la API v4 y cuenta de servicio |
| `PropertiesService` | Variables de entorno en `.env` |
| `CacheService` | Cache de Django (archivos en `.cache/`) |
| `google.script.run` | `gas_shim.js` + `core/rpc` |
| `UrlFetchApp` | `requests` |
| Triggers | Comandos `manage.py` programados |

### Dashboard (`apps/dashboard`)

Cada archivo de `services/` tiene una sola responsabilidad (manual 4.1):

- `record_reader.py`: lee Proyectos, Riesgos y Sprints como registros.
- `project_status.py`: categoría de estado y nivel de riesgo.
- `project_metrics.py`: burn, ETC, avance, desviación, tendencia, salud.
- `portfolio_costs.py`: costos y margen (las tarifas vienen de
  `core/time_entries/resource_rates.py`).
- `weekly_hours.py`: horas FACT de la semana y foco rojo.
- `kpi_calculator.py`: tarjetas de KPI.
- `kpi_history.py`: snapshot y comparativo contra la semana anterior.
- `alerts.py`, `portfolio_health.py`, `top_risks.py`,
  `delivery_managers.py`, `filters.py`.
- `response_builder.py`: arma el JSON con las llaves originales.
- `orchestrator.py`: coordina todo (equivale a `getDashboardData`).

### Proyecto ejecutivo (`apps/ejecutivo`)

- `project_detail.py`: filas por recurso, totales, roles, areas e
  insights (`getDetalleProyectoCompleto`).
- `project_hours.py`: horas del proyecto con la nomenclatura IXB/RaaS
  (`obtenerHorasClockifyPorProyectoJerarquia`).
- `history_stages.py`: etapas A:I del historico y avance por etapas
  (`obtenerEtapasHistoricoAIProyecto`, `_ixsHitosDesdeEtapasEjecutivo_`,
  `_ixsAvanceEstimadoEtapasEjecutivo_`).
- `additional_milestones.py`: hitos de la columna L en adelante
  (`obtenerHitosAdicionales`).
- `project_dashboard.py` y `project_orchestrator.py`: dashboard
  ejecutivo (`getDashboardEjecutivoProyecto`).
- `milestone_writer.py`: alta, edicion y baja de hitos adicionales.
- `manual_risks.py`: riesgos manuales en Riesgos e Historico_Riesgos.
- Las funciones que escriben estan en `apps/ejecutivo/write_rpc.py`.

### Vista de cuenta Beecker (`apps/ejecutivo`)

- `account_view.py`: junta para una cuenta el historico
  (Historico_Proyectos desde la columna K), ROC, el estado de Proyectos,
  los proyectos AER/T&M de MPB y las oportunidades abiertas. La hoja del
  backlog se busca por sus encabezados en todas las pestanas (una sola
  lectura de las primeras 12 filas) y se recuerda 6 horas.
- `account_actions.py`: alta de oportunidades al backlog y consumo de
  Clockify por lotes de hasta 4 proyectos. Las horas de un proyecto
  finalizado se guardan en la columna BL de MPB cuando esta vacia, como
  el original.

### Dashboard AER / T&M (`apps/aer`)

- `manual_store.py`: hojas manuales AER_Planeacion, AER_Riesgos,
  AER_Acciones, AER_Vacaciones, AER_Evaluaciones, AER_Contactos,
  AER_ClienteInfo, AER_ClienteGobierno y AER_ClienteDocs. Se crean si no
  existen y se agregan al final los encabezados que falten, como el
  original.
- `plan.py`: actividades, hitos y compromisos. La identidad de una
  actividad es proyecto + actividad + responsable + fechas compromiso;
  al editar se borran sus clones fisicos.
- `risks_actions.py`: riesgos y acciones. Al leerlos se borran las filas
  repetidas del proyecto (queda la mas completa), igual que el original.
- `people_client.py`: vacaciones, evaluaciones y datos del cliente.
- `dashboard.py`: KPIs de horas de Clockify (facturables, fuera de
  horario 8-18 h, consumo contra budget y tiempo), salud, alertas y
  registros. Las horas usan el rango de MPB del proyecto. Los registros de
  Clockify ahora guardan su hora de inicio y fin (`started_at`,
  `ended_at`) para calcular las horas fuera de horario.

### Minutas IA (`apps/minutas`)

- `rule_parser.py`: lee las notas de Gemini por reglas
  (`extraerDatosPorReglas`, `limpiarMarkdown`).
- `drive_folder.py`: recorre la carpeta de Drive y exporta cada Google
  Doc a texto con la cuenta de servicio (`recorrerCarpeta`,
  `exportarDocComoTexto`).
- `minute_scanner.py`: guarda minutas, pendientes y riesgos
  (`escanearMinutasNuevas`, `procesarMinuta`).
- `minutes_view.py`: vista con filtros (`getMinutasViewData`,
  `getProyectosConMinutas`).
- El activador de tiempo se reemplaza con
  `python manage.py scan_minutes` en el Programador de tareas.
- La carpeta (`GOOGLE_MINUTES_FOLDER_ID`) debe compartirse con el correo
  de la cuenta de servicio como lector. En Apps Script se leia con la
  cuenta del usuario.

### Panel Daily (`apps/daily`)

- `azure_connection.py`: la organizacion y el PAT vienen del `.env`
  (como la configuracion compartida del original). El proyecto activo
  inicia con `AZURE_DEVOPS_PROJECT` y el selector del panel lo cambia;
  se guarda en la cache sin expiracion.
- `azure_config.py`: modal de conexion, lista de proyectos y prueba de
  conexion. Guardar solo cambia el proyecto; la organizacion o un PAT
  distinto al del `.env` se rechazan con un mensaje.
- `work_items.py`: tarjetas y tablas (pendientes, Risk, Opportunity,
  To Be/CR con su avance, sin seguimiento, inspeccionar campos), con
  cache de 5 minutos por proyecto.
- `risk_form.py`: formulario y alta de riesgos, buscadores y
  comentarios.
- `daily_sheets.py`: hojas Pendientes_Daily, Ajustes_UAT,
  Ajustes_Garantia y WorkItems_Avance.
- `project_links.py`: sprints internos y resumen ejecutivo del proyecto.
- `ixs_panel.py`: panel Azure de la vista IXS por proyecto interno
  (WIQL con reintentos, hasta 750 work items en lotes de 150, filtro
  por ID base y sufijo S/CR/QA, avance de WorkItems_Avance). Cache de
  5 minutos y copia de la ultima consulta completa por 6 horas para
  fallos temporales de Azure.
- `ixs_raid.py`: lista RAID (Risk, Issue, Opportunity) con sus campos
  de detalle y relaciones, y alta de registros validando el Iteration
  Path real, los campos editables y los valores permitidos del proceso.
  El alta no se reintenta (evita duplicados) y verifica el enlace
  Parent despues de crear.
- `claude_assist.py`: configuracion de Claude, prompts personalizados
  (Risk, Issue y Opportunity; los estandar estan en `apps/daily/prompts/`)
  y sugerencias para los formularios RAID. Nunca crea nada en Azure.
- `ixs_ai_facts.py`, `ixs_ai.py`: analisis y preguntas de la IA IXS.
  Claude solo recibe hechos con identificador (PR-1, WI-101...) y se
  descartan las afirmaciones que no los citan o que escriben numeros
  que no aparecen en sus evidencias. Memoria, ultimo analisis y minutas
  en IXS_IA_Memoria, IXS_IA_Analisis e IXS_IA_Minutas.
- `ixs_drive.py`: carpetas de Drive por proyecto (IXS_IA_Carpetas),
  lectura de Google Docs y TXT y borrador de minuta con transcripciones.
- `ixs_client.py`, `ixs_planning.py`, `bee_com.py`: hojas propias de la
  vista IXS (IXS_Cliente_*, IXS_Acciones*, Recursos, IXS_Planeacion y
  Comunicados), con una fila JSON por registro como el original.
  `ixs_functions.py` tiene las envolturas con las firmas del original
  (por ejemplo `ixsEliminarContacto(uid, id)`). Las escrituras usan un
  candado como `LockService`; vale dentro de un proceso del servidor.
  Al leer Recursos, si existe la hoja anterior IXS_Recursos_Asignados,
  sus asignaciones se copian a Recursos y la hoja se elimina (igual que
  el original).

### Capacidad instalada (`apps/capacidad`)

- `sheet_table.py`: ubica los encabezados en las primeras 20 filas
  (`ciTabla_`, `ciCampo_`).
- `capacity_text.py`: normalizacion, horas y reglas por concepto
  (`ciNorm_`, `ciNumero_`, `ciRegla_`).
- `mpb_projects.py`: proyectos AER/T&M de MPB (`ciProyectoMPB_`).
- `capacity_base.py`: asignaciones y bandas del mes
  (`capacidadInstaladaBase`).
- `azure_range.py` y `project_range.py`: inicio y fin desde MPB o desde
  las iteraciones de Azure (`ciRangoAzure_`,
  `capacidadInstaladaProyecto`).
- `daily_hours.py`: horas de Clockify por persona y dia, filtradas por
  la nomenclatura de la Task (`ciRegistroDeVariante_`,
  `capacidadInstaladaDatosProyecto`). Clockify se consulta con la
  coincidencia estricta (`load_strict_project_report`).
- `orchestrator.py`: coordina ambas consultas.

### GSE: horas por area (`apps/gse`)

Pestana GSE de `CapacidadInstalada.html`: horas de Clockify por area (ROL
de `Bandas/rol`), persona y categoria.

- `cells.py`: `gseNorm_`, `gseBaseFecha_` y lectura de celdas que pueden
  faltar al final de una fila.
- `catalog.py`: ficha de `CatalagoProyectos` y categorias de cada
  registro (`gseCatalogo_`, `gseFichaCatalogo_`, `gseCategorias_`).
- `roster.py`: personas, areas y banda del mes de `Bandas/rol`
  (`gseObtenerAreas`).
- `base_store.py`: lee la base `08.Base Clockify AAAA` y su cobertura en
  `GSE_Base_Control` (`gseBaseLeer_`, `gseBaseMes_`). La llave de
  conexion se calcula igual que en Apps Script (workspace + huella de la
  API key), asi que lee la base que ya guardo el Apps Script.
- `month_report.py`: `gseObtenerMes` (fuente `sheet` o API).
- `year_base.py` y `batch_read.py`: `gseObtenerAnoBase` y
  `gseObtenerLoteBase` (bloques de 1,500 filas, las mas recientes
  primero).
- `clockify_month.py`: reporte detallado de todo el workspace
  (`gseReporteMes_`), con la base guardada y la cache de 1 h por delante.
- `result_cache.py`: resultado anual 6 h (`gseLeerResultadoCache`,
  `gseGuardarResultadoCache`).

Diferencias con el original: no existe el corte a los 40 s con
`pending` (la consulta se hace en una sola llamada) y la cache es la de
Django, compartida entre usuarios.

## Velocidad y cache

La primera carga consulta Clockify y Azure por cada proyecto, igual que
el Apps Script. Para acelerarla:

- Clockify descarga 3 reportes a la vez y Azure 4 consultas a la vez;
  cada hilo usa su propia conexion HTTP.
- Todo queda en la cache de Django (`.cache/`): reportes de Clockify
  6 h (24 h si el rango del proyecto ya terminó), horas del portafolio
  15 min, dashboard 6 min, work items de Azure 15 min y lista de Team
  Projects 1 h.
- Las hojas de Sheets se guardan 15 min entre peticiones
  (`SHEETS_READ_CACHE_SECONDS`, 0 la apaga). Cada escritura de la app
  invalida su hoja; un cambio hecho a mano en el Spreadsheet se ve al
  vencer ese tiempo.
- El RAID ejecutivo de cada Team Project se guarda 15 min. Crear un
  riesgo desde el Daily o el IXS lo invalida.
- `python manage.py warm_cache` consulta todo en este orden: hojas de
  Sheets, dashboard, resumen de Recursos, riesgos de Azure, IXBRaaS, RAID
  de cada Team Project y consumos AER. Solo lee; no escribe en Sheets,
  Azure ni Clockify. En Windows se programa cada 10 minutos con el
  Programador de tareas:

```powershell
schtasks /Create /SC MINUTE /MO 10 /TN "BeeckerWarmCache" /TR "C:\beecker_dashboard\.venv\Scripts\python.exe C:\beecker_dashboard\manage.py warm_cache"
```

- No programes `--refresh`: borra toda la cache, incluidos el proyecto
  activo del Daily y las respuestas de Claude. Usalo solo a mano.

## Ejemplo de uso

```bash
curl -X POST http://127.0.0.1:8000/api/rpc/getDashboardData/ \
     -H "Content-Type: application/json" \
     -d "{\"args\": [{\"proyecto\": \"Todos los proyectos\", \"cliente\": \"ACME\"}]}"
```

Respuesta: `{"ok": true, "result": {"kpis": {...}, "tabla": [...]}}`.

## Imports

Agrupados en estándar, terceros y locales, siempre absolutos
(manual 4.5 y 6.1). Ruff los valida con las reglas `I` y `TID`.

## Variables de entorno

| Variable | Uso |
|---|---|
| `DJANGO_SECRET_KEY` | Obligatoria. |
| `DJANGO_ALLOWED_HOSTS` | Hosts permitidos. |
| `GOOGLE_SPREADSHEET_ID` | ID del Spreadsheet (reemplaza al Sheet contenedor). |
| `GOOGLE_CREDENTIALS_FILE` | Ruta al JSON de la cuenta de servicio. |
| `GOOGLE_MINUTES_FOLDER_ID` | Carpeta de Drive con las notas de Gemini (antes `CARPETA_MINUTAS_ID`). |
| `TIME_ENTRY_SOURCE` | `sheet` o `clockify`. |
| `DASHBOARD_CACHE_TTL_SECONDS` | Duración de la cache del dashboard (360). |
| `SHEETS_READ_CACHE_SECONDS` | Segundos que se reutiliza una hoja leída de Sheets (900; 0 = sin cache). |
| `CLOCKIFY_API_KEY`, `CLOCKIFY_WORKSPACE_ID` | Horas reales desde Clockify. |
| `AZURE_DEVOPS_ORGANIZATION`, `AZURE_DEVOPS_PAT` | Riesgos y work items de Azure DevOps. El panel Daily crea riesgos y comentarios: el PAT necesita "Work Items > Read & Write". |
| `AZURE_DEVOPS_PROJECT` | Team Project inicial del panel Daily. |
| `ANTHROPIC_API_KEY` | API key de Claude para las sugerencias de RAID y la IA IXS. Solo se configura aqui; el panel muestra sus ultimos 4 caracteres. |
| `CLAUDE_MODEL` | Modelo de Claude (vacio: `claude-haiku-4-5-20251001`, el del original). |

## Error Handling

- Todas las excepciones heredan de `core.exceptions.DashboardError` con
  `code`, `public_message` y `http_status` (mismo patrón que
  `msp_qa/exceptions.py`).
- El endpoint RPC responde `{"ok": false, "code", "message"}` y el
  adaptador lo entrega al `withFailureHandler` del frontend.
- Los errores de Google (`HttpError`, autenticación, red) se traducen en
  `SheetsError` y sus subclases; no se usa `except Exception` (manual
  6.3.2).
- El snapshot y el comparativo de KPIs registran la falla y continúan,
  igual que el original.

Diferencias intencionales con el Apps Script:

1. Si hoy no hay margen promedio, el comparativo de margen queda en
   `null`. El original convertía `null` a 0 y mostraba una variación
   falsa.
2. Los IDs se comparan como texto, así que un ID numérico en Sheets
   coincide con el mismo ID escrito como texto.
3. Las fechas escritas como texto se leen como `dd/mm/aaaa` o ISO.
4. Hitos adicionales: se guarda el dia elegido en el calendario. El
   original lo convertia desde medianoche UTC y en Mexico guardaba el
   dia anterior.
5. Hitos adicionales: en la observacion solo se cambia `|` por `/` y
   `::` por `:`. La expresion regular del original (`/\\|/g`) tambien
   coincidia con la cadena vacia e intercalaba `/` entre cada letra.
6. Vista IXS: si una fila de IXS_Acciones tiene un JSON corrupto, "Limpiar
   duplicados" responde con el error de Python en lugar del texto de
   `JSON.parse` de JavaScript. En ambos casos no se borra nada.
7. beeCom: Sheets entrega las fechas como numero de serie; un numero en
   la columna Fecha se lee siempre como fecha.
8. Consumo de la cuenta: si MPB tiene menos de 64 columnas, el original
   agregaba columnas antes de escribir BL; aqui la escritura falla, se
   registra en el log y la respuesta no cambia (el original tambien
   ignoraba los errores al guardar BL).
9. `guardarApiKeyClaude` no guarda la key: responde que se configura en
   `ANTHROPIC_API_KEY` del `.env`, para no guardar secretos desde el
   navegador.
10. Los prompts personalizados de Claude se guardan en la cache de Django
    (carpeta `.cache`, sin expiracion) y son los mismos para todos los
    usuarios; el original los guardaba por usuario en PropertiesService.
11. Las carpetas de Drive de la IA IXS se leen con la cuenta de servicio:
    hay que compartir cada carpeta con su correo. El original usaba la
    cuenta de quien abria el panel.
12. Las fechas de IXS_IA_Analisis, IXS_IA_Memoria e IXS_IA_Minutas se
    regresan como `yyyy-MM-dd HH:mm`; el original regresaba el texto
    largo de la fecha de JavaScript en el ultimo analisis.
13. Si Claude regresa un JSON que no se puede leer, el mensaje de error
    es el de Python en lugar del de `JSON.parse`.
14. AER: la columna Actualizado se regresa como `yyyy-MM-dd HH:mm:ss` y
    se compara por fecha. El original regresaba el texto largo de la
    fecha de JavaScript ("Fri Oct 02 2026 ...") y al elegir entre filas
    repetidas comparaba ese texto, que ordena por el nombre del dia.
15. Validacion de Clockify: en el original no estaban definidas
    `HOJA_AREAS_REGLAS`, `ENCABEZADOS_AREAS_REGLAS`, `HORA_LABORAL_INICIO`
    ni `HORA_LABORAL_FIN`, asi que esas funciones siempre fallaban. Se usa
    la hoja `Areas_Reglas` (`Area`, `Regla_Texto`) y horario de 8 a 18 h.
    La hora se toma en hora local del reporte; el original usaba
    `getUTCHours`. La regla por area con Claude usa `CLAUDE_MODEL` y,
    como en el original, `obtenerRegistrosMalRegistrados` no la llama.
16. `guardarApiKeyClockify` y `guardarWorkspaceClockify` no guardan nada:
    responden que la conexion se cambia en `CLOCKIFY_API_KEY` y
    `CLOCKIFY_WORKSPACE_ID` del `.env` (en el original la conexion global
    tambien bloqueaba estos cambios).
17. Diagnosticos de Clockify: no guardan en cache los miembros ni los
    usuarios del workspace, consultan los perfiles uno por uno (el
    original los pedia de 4 en 4 en paralelo) y `proyectoClockify` no
    trae `clienteId`.
18. `obtenerRangoClockifyProyecto` de un IXB/RaaS sin Discovery en
    Historico_Proyectos regresa ambas fechas en null; el original
    intentaba `calcularHitosProyecto` y regresaba la fecha de hoy como fin.
    Los mensajes de error por falta de rango tambien cambian de texto.
19. Vista de Recursos: el original convertia las fechas YYYY-MM-DD con
    `new Date()` (medianoche UTC) y en la zona de Mexico quedaban un dia
    antes: el detalle por persona mostraba cada registro con la fecha del
    dia anterior, las semanas y meses se agrupaban mal, la etiqueta de la
    grafica por dia salia un dia atras y los dias habiles del periodo se
    contaban corridos. Aqui se usa la fecha real del registro.
20. RAID ejecutivo: si falla la consulta WIQL de Azure el mensaje de error
    es el generico de Django ("Azure DevOps respondio 500...") en lugar
    del texto de Azure; el proyecto activo de respaldo es el del panel
    Daily (cache) o `AZURE_DEVOPS_PROJECT` del `.env`.
21. Panel de conexion de Clockify: `guardarVinculoProyectoClockify` guarda
    el vinculo en la hoja `Clockify_Vinculos` (ID_Proyecto,
    Clockify_Project_ID) en lugar de PropertiesService; la hoja se crea
    si no existe. `diagnosticarHorasClockifyProyecto` cuenta los usuarios
    por nombre (el reporte no trae su ID en Django) y la conexion se
    describe como "global (.env)".
22. IA AER: las respuestas de Claude se guardan en la cache de Django y
    se comparten entre usuarios (el original usaba la cache de cada
    usuario); el modelo sale de `CLAUDE_MODEL`. La carpeta de minutas se
    lee con la cuenta de servicio (hay que compartirla con su correo) y no
    usa el resourcekey de la URL. Las fechas de las hojas AER_IA_* se
    regresan como `yyyy-MM-dd` o `yyyy-MM-dd HH:mm:ss`, igual que se
    escriben.
23. Velocidad: Apps Script leia las hojas en cada llamada; Django las
    guarda `SHEETS_READ_CACHE_SECONDS` entre peticiones y el RAID
    ejecutivo 15 min (el original lo pedia a Azure en cada consulta).
    Por eso un cambio manual en una hoja puede tardar hasta ese tiempo en
    verse; los cambios hechos desde el dashboard se ven de inmediato.
    `warm_cache` amplia la precarga con las hojas, Recursos y el RAID.
24. Cache larga: la lista de Team Projects de Azure se guarda 1 h (un
    proyecto nuevo puede tardar hasta 1 h en aparecer) y el reporte de
    Clockify de un proyecto cuyo rango termino antes de hoy se guarda
    24 h; si alguien corrige horas de un proyecto cerrado se ven al
    vencer ese tiempo. Para verlas antes se borra `.cache/`.
25. GSE: la consulta del mes por API Clockify se hace en una sola llamada
    (sin el corte a los 40 s con `pending`), el resultado anual se guarda
    en la cache de Django compartida entre usuarios (en Apps Script era
    por usuario) y un `ID Registro` repetido o un mes sin cobertura
    produce el mismo mensaje que el original.

## Unit Tests

```bash
pytest                 # incluye cobertura mínima del 80 %
ruff check . && ruff format --check .
mypy .
```

- `tests/core`: utilidades, repositorio de Sheets (con mocks), fuente
  de horas y registro RPC.
- `tests/dashboard`: cálculos del dashboard. `test_orchestrator.py`
  compara contra los valores que produce el `getDashboardData()`
  original con los mismos datos de `sample_data.py`.
- `tests/capacidad`: `test_parity.py` compara contra la salida del
  `CapacidadInstaladaService.gs` original (`expected_results.json`) con
  los datos de `sample_data.py`.
- `tests/gse`: `test_parity.py` compara 53 casos (areas, mes, ano y
  bloques de la base) contra el `GSEService.gs` original
  (`expected_results.json`, bloques de 4 filas); `test_units.py` cubre
  la cache del resultado, la cobertura vencida y el reporte de Clockify.
- `tests/daily/test_daily_parity.py`: compara 79 operaciones del panel
  Daily contra el original con una organizacion de Azure simulada
  (`expected_results.json`).
- `tests/daily/test_ixs_parity.py`: compara el panel IXS y el RAID
  (lista, campos, opciones y altas con sus JSON Patch) contra el
  original (`ixs_data.json`, `ixs_expected.json`).
- `tests/daily/test_ixs_sheets_parity.py`: compara 64 operaciones de
  cliente, acciones, recursos, planeacion y beeCom, y el estado final de
  cada hoja, contra el original (`ixs_sheets_expected.json`).
- `tests/ejecutivo/test_account_parity.py`: compara la vista de cuenta,
  las oportunidades, el alta y los lotes de consumo (con sus escrituras)
  contra el original (`account_expected.json`).
- `tests/daily/test_ai_parity.py`: compara 68 operaciones de Claude y la
  IA IXS, y los cuerpos exactos enviados a Claude, contra el original
  (`ai_expected.json`).
- `tests/aer/test_aer_parity.py`: compara 65 operaciones del dashboard
  AER (lecturas y escrituras) y el estado final de cada hoja contra el
  original (`aer_expected.json`).
- `tests/minutas/test_minutes_parity.py`: compara el parser, el escaneo
  y la vista de minutas contra el original (`expected_results.json`).
- `tests/ejecutivo/test_milestone_writer.py`: compara la escritura de
  hitos y riesgos contra el original (`write_expected.json`).
- `tests/ejecutivo/test_project_parity.py`: compara el detalle y el
  dashboard ejecutivo contra el original (`project_expected.json`).
- `tests/test_api.py`: integración con Django (portal y endpoint RPC).
