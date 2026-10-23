# Estado de traspaso de la migración (24/10/2026)

Lee primero `AGENTS.md` y `docs/plan-migracion-frontend.md`.

## Bloque: fase 10, paneles de capacidad y cambios de IA (parcial)

- `sections/ixs_ai_panels_view.js` presenta capacidad y cambios entre cortes
  con DOM seguro, iconos originales y evento externo para Ver recursos.
  Recibe resultados del modelo ya separado, sin recalcularlos. La extensión
  anterior delega estos dos paneles; la ruta de comparación conserva su HTML.
- Misma tabla, columnas, decimales, balance, estados y mensajes. Conserva
  recursos sin estimación/excedidos, exclusión de inactivos y comparación
  completa/incompleta/ausente. No se añadieron endpoints ni acciones de IA.
- **32 pruebas navegador/soporte aprobadas**, incluidas 15 comparaciones de
  cajas/estilos contra la anterior: cinco variantes a 1450/900/390 px.
  La prueba nueva comprueba delegación, texto de recursos/fecha como texto
  seguro sin ejecutar HTML, y navegación a Recursos. **16 Node aprobadas**
  de modelo, fuentes y cliente. Ruff/formato y diff aprobados.
- Capturas en `tmp/migration/project_detail/ixs_ai_sources/`; inspeccionada
  `comparable/1450/new.png`. Fuentes simuladas, sin modelos/servicios reales.
- IA y fase 10 siguen parciales: falta el resto de vista/eventos (cabecera,
  resumen, atención, recomendaciones, fuentes, preguntas, minutas y Drive),
  y las acciones/formularios por API. Continuar por apartados con comparación;
  mantener shim y script anterior. Sin push.

## Bloque: fase 10, modelo de IA IXB (parcial)

- `sections/ixs_ai_model.js` separa contexto, snapshot de memoria, cambios
  entre cortes y capacidad por recurso. Recibe estado y dependencias explícitas;
  no consulta servicios ni modifica datos. Las cuatro funciones anteriores
  delegan en la ruta nueva y mantienen su código para comparar.
- Conserva agrupaciones, redondeos, estados cerrados, normalización de nombres,
  recursos inactivos y límites de minutas. Atención: contexto excluye duraciones
  negativas y suma por personas con nombre; snapshot suma todas las duraciones
  numéricas. Esa diferencia ya existía; se mantiene sin ajustar cálculos.
- Cuatro pruebas Node nuevas comparan cada salida con las funciones originales,
  con datos completos, vacíos y fuentes parciales; verifican no mutación y
  snapshot diferido cuando no hay memoria. Suite dirigida: **16 aprobadas**.
- **35 pruebas aprobadas** de navegador/soporte: 34 de IA, entrada y soporte
  frontend, más una nueva que comprueba delegación real de las cuatro funciones
  y resultados idénticos en el navegador. Incluye nueve comparaciones visuales
  a 1450/900/390 px. Capturas regeneradas en
  `tmp/migration/project_detail/ixs_ai_sources/`; inspeccionada escritorio.
  Ruff/formato y diff aprobados. Servicios simulados, sin llamadas reales a IA.
- IA sigue parcial: presentación y eventos, generación/preguntas y formularios
  aún son anteriores. Siguiente vista segura reutilizando este modelo; después
  acciones por API con permisos y CSRF. Fase 10 parcial, sin push.

## Bloque: fase 10, fuentes e historial de IA IXB (parcial)

- `apps/portal/api/project_ai.py` expone seis GET de `screens/proyectos/<id>/`:
  `cliente/`, `ia/analisis/`, `ia/memoria/`, `ia/minutas/`,
  `ia/drive/carpetas/` e `ia/drive/archivos/`. Conserva servicios, stores y
  `run_safely` anteriores. Lecturas con `view_operations` y alcance total;
  configuración de carpetas conserva `manage_integrations` y alcance total.
- `sections/ixs_ai_sources.js` carga seis fuentes, historial y Drive por API.
  Conserva resultados parciales, reintento, selección de transcripciones y
  análisis guardado; descarta respuestas de proyectos o cargas anteriores.
  El script anterior delega estas cargas y conserva el fallback de comparación.
- Tres CSS externos conservan los IDs originales y el orden base, referencia,
  extensión. No hay cambios de cálculos ni diseño. La presentación, contexto,
  generación, preguntas y formularios siguen en el script anterior: **IA no
  está completamente migrada** y la fase 10 sigue parcial.
- Evidencia: **43 pruebas API**, **13 e2e** (nueve comparaciones con la anterior,
  completa/vacía/parcial a 1450/900/390 px), seis pruebas Node nuevas.
  Regresión dirigida: **91 aprobadas** incluyendo entrada, Azure y soporte.
  Node completo: **176 aprobadas y tres fallos anteriores**
  (`cost_sprint_details`, `executive_report`, `financial`). Ruff, formato,
  comprobación Django y diff aprobados; mypy conserva seis errores previos en
  otros archivos, ninguno en el módulo nuevo.
- Capturas: `tmp/migration/project_detail/ixs_ai_sources/`; inspeccionada
  `full/1450/new.png`. Servicios simulados: sin consultas reales a IA, Drive,
  Azure ni Gmail. No es una regresión completa del portal.
- Siguiente: extraer contexto/snapshot/cambios/capacidad y presentación de IA
  conservando cálculos; después migrar acciones y formularios con sus permisos
  y CSRF. Mantener shim, comparación y script anterior. No hacer push.

## Bloque: fase 10, pestaña Azure DevOps IXB completa

- Entrada en `sections/ixs_azure_tab.js`, estructura en `ixs_azure_tab_view.js`.
  `_ixsRenderTab` delega antes de ejecutar la plantilla anterior. Reutiliza
  carga, resumen y agrupaciones ya migrados, con API v1 y DOM seguro.
- Tabla compartida con Planeación en `ixs_planning_azure.js`: modo Azure
  conserva comentarios visibles, tabla plegada inicialmente, IDs, etiquetas,
  controles, filtros exactos y búsqueda sin normalizar acentos. Modelo puro
  `ixs_azure_table_model.js`; dos pruebas Node contra las funciones originales.
- Reutiliza `ixs_work_item_actions.js` para los cuatro campos y comentarios.
  Azure guarda fecha y recalcula la fila sin mutar/repintar sus alertas; en
  Planeación se conserva la actualización de alertas. Mantiene mensajes,
  comentario vacío, borrador tras error y confirmación de tres segundos.
  Sesiones/filas desmontadas impiden respuestas tardías y comentarios duplicados.
- Actualizar conserva filtros si la opción sigue disponible y la búsqueda;
  entrar de nuevo reinicia controles, pero conserva la posibilidad anterior
  de buscar en el corte previo mientras llega el nuevo. Los selectores se
  pueblan cuando responde la API. Sin nuevos endpoints ni cambios de negocio.
- Pruebas nuevas: 35 e2e, incluidas nueve comparaciones de pestaña y quince
  de fila guardada contra la anterior a 1450/900/390 px; filtros/fechas,
  errores con reintento, respuestas tardías, texto seguro y datos previos
  durante la carga. Capturas en `tmp/migration/project_detail/ixs_azure_table/`.
- Regresión final: **152 aprobadas** (100 e2e de Azure/Planeación/Work Items,
  41 API de permisos/guardados/cargas y 11 de soporte frontend). Incluye los
  casos tardíos de Work Items que habían fallado en ejecuciones anteriores;
  en esta ejecución pasaron. Node completo: **170 aprobadas y tres fallos
  anteriores** (`cost_sprint_details`, `executive_report`, `financial`).
  Ruff/formato y diff aprobados; inspeccionada la captura completa de
  escritorio. Fuentes simuladas, sin Azure/Gmail reales. No es una regresión
  completa de todas las pantallas del portal.
- Azure DevOps deja de ser pendiente dentro de IXS, pero **la fase 10 sigue
  parcial**. Siguiente IA, Cliente/Acciones y Comunicación; luego pestañas AER
  pendientes y encabezado/navegación compartidos. No retirar shim ni script
  anterior todavía. Horas por mes y ACCESS_ENFORCED se conservan.

## Bloque: fase 10, indicadores y resumen de Azure DevOps IXB

- `sections/ixs_azure_summary{,_model,_view}.js`: seis indicadores, dona,
  distribución/avisos, atención prioritaria, carga por asignado, fechas y
  resumen de estados. DOM seguro, eventos externos y barras/colores por CSSOM.
  Mantiene las reglas de estados distintas de resumen y agrupaciones.
- Conserva denominadores, promedio/redondeo, deduplicación de riesgo, orden,
  fechas y límites: atención muestra 3 y permite hasta 8; carga muestra 5;
  fechas muestra 5 y permite hasta 8. Ver más/menos y reinicio al actualizar
  son modulares. No se cambiaron servicios ni API/cálculos de negocio.
- Cinco pruebas Node contrastan cifras, distribución, orden y fechas con las
  variables de la función anterior; verifican estado vacío, lista detallada
  distinta de todos los WIs y no mutación de datos.
- 16 pruebas e2e aprobadas: doce comparaciones de todos los elementos contra
  la anterior a 1450/900/390 px (completa, vacía, cerrados y sin detalle),
  tres expandir/contraer/actualizar y texto seguro. Capturas en
  `tmp/migration/project_detail/ixs_azure_summary/`; inspeccionada escritorio.
- Regresión dirigida de agrupaciones, cargas, entrada del detalle, soporte
  frontend y escrituras visibles: **58 aprobadas** adicionales. Node completo:
  **168 aprobadas y los tres fallos anteriores** (`cost_sprint_details`,
  `executive_report`, `financial`). Ruff/formato y diff aprobados. Fuentes
  simuladas; no es una regresión completa del portal ni se usó Azure/Gmail real.
- **Azure y fase 10 siguen parciales:** siguiente estructura y tabla editable
  con filtros/acciones de Work Items, que aún se ejecutan en el script anterior.
  Los selectores los sigue poblando su función anterior. Después IA,
  Cliente/Acciones, Comunicación, pestañas AER y encabezado/navegación comunes.

## Bloque: fase 10, agrupaciones y desgloses de Azure DevOps IXB

- `sections/ixs_azure_groups_model.js` conserva clasificación, agrupación por
  persona/ruta de iteración y etapa, orden y búsqueda. La clasificación de
  estados de grupos difiere de la de los indicadores: se mantienen ambas,
  sin intentar unificarlas ni cambiar conteos. Tres pruebas Node contrastan
  el modelo con las funciones originales y comprueban búsqueda/inmutabilidad.
- `ixs_azure_groups_view.js` y `ixs_azure_groups.js` construyen personas,
  iteraciones, etapas y las tres ventanas de detalle con DOM seguro/eventos
  externos. Conservan foco en Cerrar, Escape, cierre por fondo, búsqueda que
  abre coincidencias y enlaces al Work Item. La ruta anterior sigue independiente.
- CSS `project_detail_ixs_azure.css` iguala las reglas anteriores de `.top`
  dentro de las ventanas, fuera del contenedor principal. No altera la barra.
- 22 pruebas e2e aprobadas: nueve comparaciones de grupos (completa/vacía/aviso)
  y nueve de ventanas (persona/iteración/etapa) a 1450/900/390 px, búsqueda,
  cierre por botón/fondo y texto seguro. Se espera al final de la animación de
  la flecha antes de comparar, sin cambiar la animación de la interfaz.
  Capturas en `tmp/migration/project_detail/ixs_azure_groups/`; inspeccionadas
  las de escritorio y móvil. Pruebas con datos simulados, sin servicios reales.
- Regresión dirigida de cargas Azure, entrada del detalle, soporte frontend y
  guardados/comentarios visibles: **36 aprobadas** adicionales. Suite Node:
  **163 aprobadas y los mismos tres fallos anteriores** (`cost_sprint_details`,
  `executive_report`, `financial`). Ruff/formato y revisión del diff aprobados.
  No se presenta esta comprobación como una regresión completa del portal.
- **Azure DevOps y fase 10 siguen parciales.** Siguiente: indicadores/resumen,
  atención prioritaria, carga por persona y próximas fechas; después tabla
  editable/filtros/acciones de Work Items y estructura de la pestaña. Mantener
  shim/script anterior; no se cambiaron API, cálculos, Horas por mes ni accesos.

## Bloque: fase 10, transporte y cargas de Azure DevOps IXB (parcial)

- GET `screens/proyectos/<id>/azure/` llama a `get_ixs_panel(id, force)`;
  `forzar=1` conserva la actualización explícita del RPC. Lectura con
  `view_operations` y alcance total. La API de Planeación conserva `False`
  incluso si recibe `forzar`; no se cambian sus consultas ni cálculos.
- `sections/ixs_azure.js`, `ixs_azure_model.js` y `ixs_azure_loading.js`
  separan transporte, forma del estado y mensajes DOM seguros. Tokens por
  consulta/sesión y comprobaciones de proyecto, pestaña y nodo evitan que
  respuestas viejas sobrescriban una vista nueva, tanto éxitos como errores.
- `_ixsLoadAzureDevOpsTab` delega en el controlador nuevo; la comparación
  anterior sigue en RPC. Resumen, filtros, tablas, agrupaciones, desgloses y
  acciones siguen en el archivo anterior: **Azure DevOps no está terminada**.
- Siguiente: migrar la presentación/agrupaciones y los controladores de filtros,
  desgloses y Work Items de Azure. Después IA, Cliente/Acciones, Comunicación
  y pestañas AER. Mantener shim y script anterior.
- Verificaciones específicas: 48 pruebas API (Azure, Planeación y alta RAID),
  11 Node del transporte y 14 e2e aprobadas. Los e2e incluyen nueve
  comparaciones con la anterior a 1450/900/390 px (completa, vacía y error),
  carga, refresco, filtros/desglose, respuestas tardías y error con reintento.
  Capturas en `tmp/migration/project_detail/ixs_azure_transport/`; inspeccionada
  también la captura completa de escritorio. Fuentes simuladas, sin Azure/Gmail
  reales. Ruff/formato y `manage.py check` aprobados.
- Regresión del detalle/Planeación/API/soporte frontend y escrituras visibles
  de Azure: **181 aprobadas**, con Chrome. No es una regresión completa del
  portal. Suite Node completa: **160 aprobadas y los tres fallos anteriores**
  (`cost_sprint_details`, `executive_report`, `financial`).
- Mypy detecta seis errores previos en cuatro archivos: `fallback_project.py`
  (3), `dashboard.py` (1), `project_orchestrator.py` (1) y el retorno de
  `RaidPromptView.get_permissions` (1). Comprobado también con el contenido de
  la API de HEAD mediante `--shadow-file`: mismos seis errores. No corregidos
  en este bloque de transporte.

## Ajuste: Margen vendido vs. real (24/10/2026)

- La pantalla nueva ya no muestra "Fecha de servicio: G · por validar" bajo
  Revenue operado ni "Pendiente / Por validar con Florencia" en Tarifa de costo
  vendida; las columnas se conservan y la celda de tarifa queda vacía. La nota
  de la tarifa sigue arriba de la tabla. La pantalla anterior (`?vista=anterior`)
  no cambia. Referencia `cuenta_margenes.json` actualizada a propósito.
- Glosario "¿Qué significa cada columna?" (plegable) con las definiciones de
  Bookings, Revenue operado, Facturado, Cobrado, Costos, Tarifa de costo vendida,
  Margen vendido, Margen real y Desviación, y enlace al diccionario de datos.
  Usa los estilos del glosario de Business Overview. Pruebas e2e nuevas (2).

## Bloque: fase 10, alta RAID (Riesgo, Issue y Oportunidad)

- API v1: GET `screens/proyectos/<id>/raid/{campos,alta-opciones}/?tipo=` y
  `screens/proyectos/raid/prompt/?tipo=`; POST `.../raid/crear/` y
  `screens/proyectos/raid/{sugerir,prompt}/`. Mismos servicios que
  `ixsRaidCamposTipo`, `ixsRaidAltaOpciones`, `ixsRaidObtenerPrompt`,
  `ixsRaidCrearRegistro`, `ixsRaidSugerirClaude` e `ixsRaidGuardarPrompt`.
  Permisos como en la política RPC: lecturas `view_operations`; crear y sugerir
  `edit_operations`; guardar prompt `manage_integrations`; escrituras con CSRF y
  alcance total. Nada se publica en Azure hasta pulsar «Crear en Azure».
- Frontend: `sections/raid_create_model.js` (reglas de publicación, plan en
  líneas, sugerencias, estado del padre; contrastado en Node con la función
  original), `raid_create_view.js` (ventana y formularios por tipo con DOM
  seguro) y `raid_create.js` (controlador `beeIxsRaid` lo usa al pulsar
  + Riesgo / + Issue / + Oportunidad). Con `?vista=anterior` queda el alta
  anterior.
- Detalle conservado: campos que pasan a lista cuando Azure responde tarde,
  iteración por defecto, buscadores de personas/iteración/WI, severidad →
  impacto, prompts guardables por usuario, avisos y tiempos. Mejora menor: el
  cálculo severidad → impacto sigue funcionando si el campo cambia a lista.
- Pruebas: 9 de API, 37 de navegador (27 comparaciones con la anterior a
  1450/900/390 en ventana inicial, formulario manual y sugerido de los tres
  tipos; el resto cubre API/CSRF, reglas de publicación, errores de Azure,
  prompts, padre y texto seguro) y 3 de Node. Regresión de proyecto/portal/Gmail/
  ejecutivo: 1298 aprobadas. Una comparación fue intermitente bajo carga y pasa
  sola (se añadió una espera de red).
- No se creó ningún registro real: Azure y Claude simulados.
- Con esto la pestaña Gestión RAID queda completa. Siguen pendientes: IA,
  Cliente/Acciones (comparten renderer con AER), Azure DevOps, Comunicación y
  las pestañas AER distintas del Ejecutivo.

## Bloque: fase 10, Gestión RAID de IXB/SaaS/RaaS (lectura y presentación)

- API v1: `GET screens/proyectos/<id>/raid-registro/` (`?forzar=1` omite la
  caché), mismo servicio que `ixsRaidListarProyecto` (`ixs_rpc.list_raid`);
  lectura con los permisos de las demás lecturas del detalle.
- Frontend: `sections/raid_model.js` (severidad, cerrados, KPIs, dona, matriz,
  etapas, carga, filtros y campos del detalle; contrastado en Node contra las
  funciones originales), `raid_view.js` (DOM seguro, sin `innerHTML`; incluye
  los tres paneles de detalle y el genérico) y `raid.js` (controlador
  `window.beeIxsRaid`: conserva la última vista si Azure falla, Sincronizar,
  filtros, "Ver más"). CSS `project_detail_raid.css` solo para lo que antes eran
  atributos `style`.
- **Sigue en el script anterior:** el alta (modal "+ Riesgo/Issue/Oportunidad",
  sugerencias, prompts de Claude y creación en Azure). `ixsRaidCargar(true)`
  delega en el controlador nuevo, así que tras crear se refresca por API.
  Con `?vista=anterior` queda todo como antes.
- Pruebas: 6 de API, 22 de navegador (comparación elemento por elemento con la
  anterior a 1450/900/390 en página, filtros y los cuatro paneles de detalle;
  texto seguro, "Ver más", sincronizar, error inicial y error conservando la
  vista) y 3 de Node. Regresión de proyecto + portal: 1141 aprobadas.
- Siguiente en esta pestaña: migrar el alta de RAID (formularios, opciones,
  prompts y creación en Azure). Después: IA, Cliente/Acciones, Azure DevOps,
  Comunicación y las pestañas AER.

## Bloque: comunicados del proyecto (Extensión, Suspensión, Reanudación, Cierre)

- Backend (`apps/gmail`): `POST /gmail/reply/` acepta `kind` (por defecto
  `extension`; también `suspension`, `reanudacion`, `cierre_ixb`,
  `cierre_aer`). `communique.py` tiene las plantillas nuevas (suspensión y
  reanudación dirigidas a ROC, con saludo por hora; cierre IXB con MCO; cierre
  AER/T&M con "el día de hoy" solo si la fecha es hoy); `extension_reply.py`
  valida (`parse_communique`) y entrega (`deliver_communique`) en el mismo hilo
  "Inicio de ..." que la extensión. Enlace opcional en todas menos extensión
  (roadmap obligatorio); el cierre IXB exige MCO como archivo o enlace.
- Frontend: `sections/communique{,_model,_view,_actions}.js`, CSS
  `project_detail_communique.css` (mismos estilos de la ventana de extensión
  anterior). Una sola ventana con selector de tipo: IXB/SaaS/RaaS tiene los
  cuatro botones; AER/T&M solo Extensión y Cierre (botones nuevos en el
  Ejecutivo AER). `ixsAbrirExtension` delega en `window.beeProjectCommunique`;
  con `?vista=anterior` queda la ventana anterior. Conserva conexión a Google,
  búsqueda de hilos, adjuntos, vista previa y copiar texto.
- Pruebas: 3 de vista y 14 de servicios Gmail nuevas, 5 Node, 9 e2e (extensión
  idéntica a la anterior a 1450/900/390 sin el selector nuevo, tipos, validación,
  adjunto, texto escapado, AER). Las comparaciones AER anteriores quitan los
  botones nuevos antes de medir.
- **Ojo:** el `.env` local tiene `GMAIL_DELIVERY_MODE=send`: aquí "Generar
  comunicado" ENVÍA el correo (con confirmación). Las pruebas fijan `draft` y
  usan Gmail simulado; no se envió nada real.
- Supuestos a validar con negocio: los cierres y la extensión AER responden en
  el hilo "Inicio de ..."; la extensión de AER conserva el campo Etapa
  (Discovery/Development/Deployment) y su frase de la plantilla.

## Dónde nos quedamos (23/10/2026, antes de pasar el repo a pruebas)

- Último commit de migración: editor de hitos del histórico (`7e9e651`, API en
  `641a08c`) y arreglo de horas por rango MPB (último commit de código). Todo empujado a `main`.
- **En pausa para pruebas de tu compañero.** No se empezó la extensión del
  proyecto ni sus integraciones; es el siguiente bloque (ver más abajo).
- Corrección de horas: `ProjectDateRangeResolver._resolve_from_mpb` ahora une
  todas las filas de MPB con el mismo ID (AER.CCO.008 tiene dos: una terminada
  18–20/05 y otra en curso 11/05–31/12). Antes tomaba la primera y Esfuerzo
  mostraba 92 h. Aplica a todo consumidor de `resolve()` (AER, ejecutivo,
  tareas, validación). AER.CCO.008 ahora da 5,050.9 h (coincide con Horas por
  mes). Presupuesto vs consumo usa su rango por fila de cuenta; no se tocó.
- Proyectos que no están en la hoja Proyectos (AER/T&M **e IXB/RaaS/SaaS**):
  `apps/ejecutivo/services/fallback_project.py` arma la ficha desde MPB
  (inicio mín., fin máx., presupuesto sumado, estatus, DM) y, si falta una
  fecha, desde las etapas de Historico_Proyectos. Lo usan el dashboard AER
  (`mpb_project_row`) y el ejecutivo (`load_executive_dashboard`, que también
  pasa la ficha al detalle por recurso). Sin Discovery en el histórico, el
  rango de Clockify cae al de MPB (`_mpb_fallback`, cualquier servicio).
  `proyecto.datosFaltantes` (solo si hay avisos) lista qué falta o de dónde
  salen los datos (fechas, presupuesto, "no está en Proyectos"); se pinta como
  aviso sobre el Ejecutivo (`sections/data_notice.js`, IXS y AER). Si el ID no
  está en ninguna hoja, el error ahora dice "en Proyectos, en MPB ni en
  Historico_Proyectos" (fixtures de paridad actualizados). Las pruebas de
  paridad ignoran `datosFaltantes`. Verificado con datos locales (ABI.004,
  AEC.001, SLC.001, AER.CCO.003); el aviso, con una prueba e2e de IXS; el de
  AER sin prueba de navegador. La lista de la cuenta usa solo la fila reciente
  de MPB, así que presupuesto/consumo pueden no coincidir con el detalle.
- Fallos conocidos sin relación: `test_ixs_effort::test_modals_match_previous`
  (activity, fondo por hover; falla igual sin estos cambios) y
  `test_late_response_does_not_modify_reentered_view` de Work Items.
- Pruebas: `tests/clockify`, `tests/ejecutivo`, `tests/portal` 1259 aprobadas;
  hitos 17 e2e + 15 API + 3 Node. Fallan 3 pruebas tardías de Work Items
  (`test_late_response_does_not_modify_reentered_view`), también sin estos
  cambios, sin investigar. JS: 3 fallos anteriores documentados.
- No comiteados (ajenos): `tools/migracion/inline2css.py`,
  `tools/migracion/migrate_page.py`, `shots_tmp/`, `tests/e2e/test_zz_*.py`.
- Para correr en otra máquina: `.env`, `key.json` y `db.sqlite3` no van en
  Git; hay que crear `.venv`, instalar dependencias y configurar credenciales.
- Siguiente: extensión del proyecto + integraciones (Azure DevOps, IA,
  Clockify) y pestañas IXB/AER restantes; luego limpieza y CSP. Fase 10 sigue
  parcial: no retirar el shim RPC ni `proyecto_detalle.js`.

## Bloque: fase 10, editor de hitos adicionales (modal del histórico)

- API v1: `GET screens/proyectos/hitos/tipos/` (view_operations) y POST
  `screens/proyectos/<id>/hitos/{guardar,editar,eliminar}/` (edit_operations,
  alcance total, CSRF aun con accesos apagados). Llaman sin cambios a
  `apps.ejecutivo.write_rpc` (`get_milestone_types`, `save_milestone_batch`,
  `edit_milestone_entry`, `delete_milestone_entry`) y devuelven su dict tal
  cual en `{data, meta}`; el ID de ruta prevalece.
- Frontend: `sections/milestones_model.js` (validación, tipo nuevo con ícono,
  fechas), `milestones_view.js` (DOM seguro, sin `innerHTML`) y
  `milestones.js` (controlador `window.beeProjectMilestones`). Estilos en
  `project_detail_milestones.css`. `proyecto_detalle.js` delega
  `abrirModalHito`, `editarHitoDesdeCard` y `eliminarHitoDesdeCard` si el
  módulo existe; con `?vista=anterior` sigue el código y RPC anteriores.
- Conserva textos, orden secuencial (ediciones y luego lote de altas),
  confirmaciones y recarga del dashboard. Fugas de `components.css` en `.btn`
  y `box-sizing` corregidas en la hoja.
- Pruebas: 15 de API (`tests/portal/test_milestone_api.py`), 17 de navegador
  (`tests/e2e/test_ixs_milestones.py`: comparación de cajas/estilos con la
  anterior a 1450/900/390 en vacío, tipo existente y tipo nuevo; alta, edición
  + alta, validaciones, error con reintento, borrado, cierre) y 3 de Node.
  Capturas: `tmp/migration/project_detail/ixs_milestones/<caso>/<ancho>/`.
  Regresión `tests/portal` + proyecto: 1101 aprobadas; fallan 3
  `test_late_response_does_not_modify_reentered_view` de Work Items, que
  también fallan sin estos cambios (anteriores, sin investigar).
- Pendiente: **extensión del proyecto e integraciones**; el botón de la
  tarjeta AER y los marcadores del timeline usan este mismo módulo.

## Bloque anterior: fase 10, escrituras de Work Items (Planeación parcial)

- API v1: `screens/work-items/<id>/{avance,comentarios}/`, solo POST. Invoca
  exactamente `daily.save_work_item_progress` y `daily.add_comment`, sin
  cambiar store/proyecto activo, validaciones ni el fechado del comentario.
  El ID de ruta prevalece sobre el cuerpo. Exige `edit_operations`, alcance
  total y CSRF incluso con accesos apagados; el comentario hereda la misma
  protección. Son servicios globales como el RPC, no validación por cuenta.
- `ixs_work_item_actions.js`: guardado y comentarios de Planeación; actualiza
  la barra con DOM seguro y CSS externo, conservando la ecuación anterior y
  leyendo los controles actuales. La fecha límite actualiza el mismo item y
  repinta alertas. Comentarios conservan trim, alertas, estados y tres segundos
  del mensaje de éxito; bloquean doble envío y descartan respuestas de filas
  desmontadas u otra sesión/proyecto. API compartida conserva 90 segundos/CSRF.
- `workItemCall` en el script anterior lleva estas dos escrituras a API también
  en la pestaña Azure, que todavía conserva su vista/controlador anterior.
  Con `?vista=anterior` se mantiene RPC independiente. No dar esa pestaña por
  migrada debido a este puente.
- **Diseño:** `.ixs-plan-table` oculta la columna de comentarios (última celda)
  en la versión original. Se conserva. Las pruebas de ese controlador usan
  eventos DOM sin mostrarla; otra prueba envía desde Azure DevOps con controles
  visibles. No se publican comentarios reales: fuentes y RPC simulados.
- Veintinueve pruebas API nuevas, 25 de navegador para escrituras y dos Node
  (contrato del cliente y contraste de la fórmula con la función original).
  Doce comparaciones después de dev/QA/fecha/comentario a 1450/900/390 px,
  cuatro campos/CSRF, vacío, errores/reintentos y respuestas tardías.
  Específicas: **80 aprobadas**, incluidas 26 de la vista de Planeación.
  Capturas: `tmp/migration/project_detail/ixs_work_items/<caso>/<ancho>/`.
- Regresión de proyecto: **321 aprobadas** (APIs del detalle/Recursos/
  Planeación/Work Items, soporte frontend y vistas migradas AER/IXS), con
  Chrome. No es una nueva corrida de todo el portal. JavaScript:
  **140 aprobadas y tres fallos anteriores** (`cost_sprint_details`,
  `executive_report`, `financial`). Ruff, formato, mypy de la API,
  comprobación de Django y revisión del diff aprobados.
- Las primeras pruebas intentaban usar campos ocultos y luego disparaban dos
  eventos (manual y blur nativo), o esperaban un valor ya presente antes de la
  respuesta. Se corrigió el arnés sin cambiar el diseño ni los cálculos.
- **Siguiente:** editor de hitos del histórico y extensión con integraciones.
  La fase 10 continúa parcial. No retirar shim/JS anterior, activar accesos,
  cambiar Horas por mes, tocar pendientes ajenos ni hacer push.

### Bloque anterior: presentación y cargas de Planeación IXS (parcial)

- `sections/ixs_planning{,_model,_view,_azure}.js`: controlador de consultas,
  indicadores, alertas, calendario de seis semanas, registros de vacaciones,
  resumen de Work Items y tabla/filtros locales. Construcción DOM segura y
  eventos externos; estilos estáticos en `project_detail_ixs_planning.css` y
  valores dinámicos por CSSOM. Cálculos y diseño anteriores conservados.
- Reutiliza `timeline()` del Ejecutivo con callback opcional de edición:
  mantiene botones, índices, títulos, eventos simultáneos y categorías.
  Sin callback, Ejecutivo conserva sus marcadores sin edición. El histórico
  diferido llama a `paint()` sin volver a insertar el Gantt anterior.
- El controlador usa API v1 para Planeación y Azure, en el orden anterior,
  con los estados existentes para interoperar con acciones pendientes. Los
  tokens y la identidad del proyecto descartan respuestas obsoletas. El
  cargador compartido de estados de recursos se conserva mediante callback.
- Dos pruebas Node contrastan plazos/estados, ranking, indicadores y semanas
  con las funciones originales; comprueban también que no se mutan fuentes.
  Las 30 pruebas existentes de Planeación aprobaron; las 26 nuevas también:
  dieciocho variantes visuales a 1450/900/390 px, dos comparaciones de carga,
  respuestas tardías entre pestañas/proyectos, acciones, editor de hito del
  Gantt, histórico diferido y texto seguro. Capturas:
  `tmp/migration/project_detail/ixs_planning_view/<caso>/<ancho>/`.
- Regresión de proyecto: **264 aprobadas** (APIs, soporte frontend y vistas
  migradas de AER/IXS). Tras esa corrida se preservó también el texto vacío
  de Azure cuando faltan ID/título, igual que el renderizador previo: las
  **36 pruebas finales** de vista/transporte aprobaron, incluidas tres
  comparaciones de ese caso. No se afirma una nueva regresión de todo el portal.
- JavaScript: **138 aprobadas y tres fallos anteriores** (`cost_sprint_details`,
  `executive_report`, `financial`). Ruff, formato, comprobación de Django y
  revisión del diff aprobados. No hubo cambios de Python de aplicación.
- **Pendiente:** escrituras/comentarios de Azure y su recálculo visual, editor
  de hitos del histórico y extensión con integraciones todavía usan RPC y
  controladores anteriores mediante callbacks. No contar Planeación ni la
  fase 10 como terminadas; no retirar shim/JS anterior. Después siguen las
  demás pestañas inventariadas y encabezados/navegación compartidos.
- No se cambian servicios, permisos, Horas por mes ni pendientes ajenos.
  No activar accesos ni hacer push.

### Bloque anterior: editores de Planeación IXB/SaaS/RaaS (parcial)

- Modelo, vista y controlador de formularios en
  `sections/ixs_planning_editor*.js`. Conservan campos, opciones, valores,
  títulos y validación nativa de vacaciones y actividades/hitos. CSS externo
  en `project_detail_ixs_planning.css`, DOM seguro y eventos externos.
- El puente `ixsAbrirPlanEditor` abre el módulo en la ruta activa; la anterior
  conserva su editor. Altas, edición y eliminación usan la API ya migrada.
  Se mantiene la confirmación de borrado y se bloquean envíos duplicados.
- Cada apertura tiene sesión propia: una respuesta de una ventana cerrada
  no cierra ni sobrescribe otra. Se conserva el formulario ante errores y
  permite reintentar. Las respuestas de otro proyecto se descartan.
- Pruebas nuevas `test_ixs_planning_editor.py`: doce comparaciones contra
  la anterior (alta/edición de vacaciones e hitos a 1450/900/390 px), también
  con valores/opciones/required. Altas y reintentos reutilizan las pruebas
  del transporte; nuevas cubren UID con comilla/barra, confirmación de borrado,
  fallos de fuente/transporte/permisos, doble envío, respuesta tardía,
  cancelación y texto seguro. Las **30 específicas** aprobaron (20 nuevas,
  diez del transporte). Capturas:
  `tmp/migration/project_detail/ixs_planning_editor/<tipo>/<modo>/<ancho>/`.
- La primera prueba detectó atributos `style` vacíos que deja el normalizador
  compartido en inputs. La comprobación ahora exige cero declaraciones CSS
  y cero manejadores inline; no se cambió el normalizador ni el diseño.
- Regresión de este bloque: **241 aprobadas** (APIs del detalle, Recursos y
  Planeación; soporte frontend y todas las vistas de proyecto ya migradas:
  entrada, ambos Ejecutivos, Esfuerzo, Recursos, transporte y editores de
  Planeación). Ejecutada con Chrome; no es una nueva corrida de todo el portal.
  JavaScript: **136 aprobadas y tres fallos anteriores** (`cost_sprint_details`,
  `executive_report`, `financial`). Ruff, formato, comprobación de Django y
  revisión del diff aprobados. No hubo cambios Python de aplicación.
- **Siguiente:** presentación general de Planeación y sus cargas, incluido
  calendario y Gantt editable. Después, ediciones/comentarios de Azure y
  extensión con integraciones, además de las demás pestañas ya inventariadas.
  No contar Planeación ni la fase 10 como terminadas; mantener shim/JS previo.
- Servicios, permisos, Horas por mes y pendientes ajenos se conservan.
  No activar accesos ni hacer push.

### Bloque anterior: transporte de Planeación IXB/SaaS/RaaS (parcial)

- La ruta activa usa API v1 para vacaciones/compromisos (`planeacion/`) y
  panel Azure (`planeacion/azure/`), sin forzar refresco. POST por tipo para
  guardar y eliminar, con el mismo store y los servicios anteriores.
- Lecturas con `view_operations` y alcance total; escrituras con
  `edit_operations`, alcance total y CSRF aun con accesos apagados. ID de
  ruta autoritativo; UID exacto en cuerpo; 90 segundos en el cliente.
- Puente temporal `projectPlanningCall` conserva callbacks y estados del
  controlador existente. La comparación anterior mantiene su RPC propio.
- Pruebas nuevas en `test_project_planning_api.py` y
  `test_ixs_planning_transport.py`; contratos de lectura ampliados y prueba
  del cliente. Comparación de página y editor a 1450/900/390 px; altas,
  edición, eliminación, reintento, resumen y filtros locales de Azure.
  Capturas en `tmp/migration/project_detail/ixs_planning_transport/<ancho>/`.
- Validación final: **1427 aprobadas, una omitida** en portal/core/access/e2e,
  con Chrome y los cuatro temporales ajenos excluidos. Incluye 94 pruebas
  API del detalle/planeación y diez de navegador del transporte de Planeación.
  Primera ronda específica: 103 aprobadas; después se añadió el caso de
  filtros con datos de Azure, incluido en la regresión final.
- JavaScript: **136 aprobadas y los mismos tres fallos anteriores**
  (`cost_sprint_details`, `executive_report`, `financial`). Ruff, formato,
  mypy de la API, `manage.py check` y revisión del diff aprobados.
  Las dos primeras ejecuciones restringidas se detuvieron al no iniciar el
  navegador; la específica y la regresión aprobaron fuera de ese entorno.
- **Siguiente:** separar modelo, vista y controlador de Planeación, incluidos
  Gantt editable, calendario y editores. Sus ediciones/comentarios de Work
  Items y la extensión todavía usan componentes anteriores y RPC. Después
  las seis pestañas IXS restantes y las siete AER restantes; también falta
  separar encabezados/pestañas compartidos. Inventario completo en el plan.
- No contar Planeación ni la fase 10 como terminadas. Sin cambios de diseño,
  reglas de negocio, Horas por mes ni pendientes ajenos. No retirar shim/JS
  anterior ni activar accesos. Sin push.

### Bloque anterior: Recursos IXB/SaaS/RaaS (pantalla aún parcial)

- Modelo, vista y controlador en `sections/ixs_resources*.js`: tabla, mezcla
  de base y asignaciones, alertas, editor, agregar/editar/asignar recursos.
  DOM seguro y eventos externos; cinco reglas estáticas nuevas en
  `project_detail_ixs_resources.css`. Diseño y cálculos conservados.
- Lecturas existentes `recursos/` y `registros/`, en el mismo orden, sin RPC.
  Guardado nuevo `POST screens/proyectos/<id>/recursos/guardar/` con el
  mismo `save_resource`, store y validaciones. El ID de la ruta prevalece
  sobre el del cuerpo. Exige `edit_operations`, alcance total y CSRF, incluso
  con accesos apagados; `apiSend` conserva 90 segundos.
- El editor mantiene datos y permite reintentar tras errores; bloquea doble
  envío. Un éxito invalida los estados para Ejecutivo/Esfuerzo. Las cargas
  tardías no sustituyen otra lectura ni otra pestaña/proyecto.
- Treinta y una pruebas nuevas de navegador: contenido y editor contra la
  anterior a 1450/900/390 px; carga a 1450/390 px. Altas, edición, asignación,
  errores y reintentos, CSRF, doble envío, invalidación, cancelación, texto
  seguro y respuestas tardías. Capturas:
  `tmp/migration/project_detail/ixs_resources/<caso>/<ancho>/`.
  Trece pruebas API nuevas y dos contrastes Node con las funciones anteriores;
  el cliente también prueba POST con CR, payload y timeout.
- Validación específica: **44 aprobadas** (31 de navegador, trece de API).
  JavaScript: **135 aprobadas y tres fallos anteriores** (`cost_sprint_details`,
  `executive_report`, `financial`). Ruff, formato, mypy de la API y revisión
  de Django aprobados. Los pendientes ajenos siguen sin modificar.
- Regresión final: **1378 aprobadas, una omitida**, con Chrome y los cuatro
  temporales excluidos. La primera corrida se detuvo con 700 aprobadas y dos
  fallos en la captura de carga: Playwright pasaba `request` al segundo
  parámetro que se había usado para enlazar la lista de peticiones retenidas.
  Se cambió a un cierre de fábrica; las 44 específicas y la regresión completa
  pasaron después. No se cambió la pantalla para corregir esa prueba.
- **Siguiente: Planeación IXB/SaaS/RaaS**, preservando calendario, hitos,
  recursos y permisos. La pantalla y la fase 10 siguen parciales. No retirar
  todavía el shim ni el JS anterior. Sin cambios en Horas por mes ni servicios.

### Bloque anterior: Esfuerzo IXB/SaaS/RaaS

- `sections/ixs_effort*.js`: modelo, vista, controlador, registros/actividades
  y ventana de excedidas. DOM seguro y eventos externos, reutilizando iconos,
  barras, formatos, badges y expansión de horas del Ejecutivo.
- Incluye los cinco indicadores, tabla de recursos, actividades por persona,
  tendencia de últimos cinco meses, rango de registros, detalle de actividad,
  lista completa y excedidas por persona con fechas, orden, páginas y CSV.
  Los valores dinámicos usan CSSOM; tres reglas estáticas nuevas en
  `project_detail_ixs_effort.css`.
- API nueva `screens/proyectos/<id>/registros/`: mismo `project_entries`,
  repositorio, ID y alcance total que RPC. Tasks/recursos reutilizan API.
  Caché y semana local conservadas, incluido el error de registros anterior;
  se reinicia al cambiar de proyecto, aunque solo se abra su Ejecutivo.
  Las respuestas tardías no sustituyen otra pestaña o proyecto.
- Veinticinco pruebas de navegador: contenido y las tres ventanas contra la
  anterior a 1450/900/390 px, fechas, orden, páginas, caché, navegación, CSV,
  errores de fuente/transporte, texto seguro, Escape y respuestas tardías.
  Comparación de CSV byte por byte, incluido el nombre y la protección de
  fórmulas. Capturas: `tmp/migration/project_detail/ixs_effort/<caso>/<ancho>/`.
  Cuatro pruebas Node contrastan modelos originales, semanas y caché.
- Validación específica: **55 pruebas API y 25 nuevas de navegador**;
  junto con las catorce del Ejecutivo IXB aprobaron **94**. JavaScript:
  **132 aprobadas y tres fallos anteriores** (`cost_sprint_details`,
  `executive_report`, `financial`). Ruff, formato, mypy de la API y
  comprobación de Django aprobados.
- Regresión final: **1334 aprobadas, una omitida** con Chrome y los cuatro
  temporales excluidos. La primera corrida tuvo 1333 aprobadas y una falla:
  la prueba de respuestas tardías del Ejecutivo retenía también la nueva
  consulta de tasks de Esfuerzo. Se ajustó para retener solo las lecturas
  del primer Ejecutivo, conservando su comprobación de respuestas obsoletas;
  el bloque de 94 pruebas y la regresión completa pasaron después.
- Recursos IXB/SaaS/RaaS se completó en el bloque posterior descrito arriba.
  El detalle grande y la fase 10 siguen parciales; no eliminar el JS anterior
  ni el shim RPC. Horas por mes y cálculos de servicios no se modificaron.

### Bloque anterior: Ejecutivo IXB/SaaS/RaaS

- Modelo, vista y controlador separados en `sections/ixs_executive*.js`;
  iconos SVG originales en `ixs_icons.js`. El contenido ejecutivo se construye
  con nodos seguros y eventos externos. Las reglas de presentación y cálculos
  se contrastan con las funciones originales, que siguen independientes.
- CSS IXS compartido extraído completo a `project_detail_ixs.css`, con enlace
  `ixs-v74-styles` para evitar la inyección anterior en la ruta modular.
  Los estilos estáticos propios están en `project_detail_ixs_executive.css`;
  las barras y la distribución por área usan CSSOM para sus valores.
- API v1 nueva: `screens/proyectos/<id>/{raid,tasks,etapas,recursos}/`.
  Usa los servicios originales, IDs exactos, errores y alcance total del RPC.
  Las actualizaciones de estados y del Gantt siguen el controlador existente;
  Planeación conserva su Gantt editable. RAID/tasks se montan por ejecutivo
  y descartan respuestas cuando ese contenido ya se desmontó.
- Catorce pruebas nuevas de navegador: cada elemento contra la anterior
  (1450/900/390 px; completo, vacío, alertas), expansión por teclado,
  fuentes y errores de transporte, recuperación al regresar, texto seguro y
  respuestas tardías. Capturas:
  `tmp/migration/project_detail/ixs_executive/<caso>/<ancho>/`.
  Dos pruebas Node contrastan 32 escenarios ejecutivos y diez de Gantt.
  El cliente de datos mantiene 90 segundos e IDs con CR en todas las lecturas.
- Validación específica: **48 pruebas API y catorce de navegador aprobadas**.
  Las diez de la entrada también aprobaron con el nuevo ejecutivo. JavaScript:
  **128 aprobadas y tres fallos anteriores** (`cost_sprint_details`,
  `executive_report`, `financial`). No se cambiaron sus archivos.
- Regresión general: **1302 aprobadas, una omitida** con Chrome, sin los
  cuatro temporales `test_zz_*`. Ruff, formato, mypy de la API y comprobación
  de Django aprobados. Los pendientes ajenos se conservaron sin cambios.
- Esfuerzo IXB/SaaS/RaaS se completó en el bloque posterior descrito arriba.
  La pantalla grande y la fase 10 siguen parciales; no eliminar el JS anterior
  ni el shim RPC.

### Bloque anterior: Ejecutivo AER/T&M

- Ejecutivo AER/T&M ya se construye con nodos seguros en
  `sections/aer_executive.js`; sin `innerHTML` con datos ni eventos HTML.
  `aer_executive_model.js` conserva las reglas de presentación del anterior:
  dimensiones/fuentes faltantes, fechas, cierre, dependencias, prioridades,
  porcentajes, redondeos, resúmenes y formatos. No se modificaron servicios.
- El CSS AER compartido se extrajo íntegro a `project_detail_aer.css`.
  Su `<link id="aer-dashboard-styles">` evita la inyección anterior en la ruta
  modular. Las declaraciones estáticas del HTML ejecutivo viven en
  `project_detail_aer_executive.css`; anchos y valores dinámicos usan CSSOM.
  La comparación anterior conserva el renderer y CSS originales independientes.
- `_aerRenderTab()` delega Ejecutivo en `window.beeProjectExecutive` cuando
  existe. El resto del controlador, el encabezado y otras pestañas mantienen
  sus funciones previas. Los enlaces del nuevo componente llaman al controlador
  existente para abrir Acciones, Planeación y Riesgos, también mediante teclado.
- Trece pruebas nuevas de navegador: comparación de **cada elemento** con la
  anterior a 1450, 900 y 390 px, con datos completos, vacíos y de atención;
  navegación por teclado, retorno al componente y protección del texto HTML.
  Capturas: `tmp/migration/project_detail/aer_executive/<caso>/<ancho>/`.
  Dos pruebas Node comparan 27 escenarios del modelo con el renderer original,
  además de ceros, redondeos y dimensiones sin fuente.
- Regresión general del bloque: **1261 aprobadas, una omitida**. JavaScript:
  **126 aprobadas, tres fallos anteriores** (`cost_sprint_details`,
  `executive_report`, `financial`). Las trece pruebas nuevas de navegador y
  las diez de la entrada están incluidas en la regresión. Ruff, formato y
  comprobación de Django aprobados. No se modificaron permisos ni servicios.
- Ejecutivo IXB/SaaS/RaaS se completó en el bloque posterior descrito arriba.
  El detalle completo sigue parcial; no eliminar el JS anterior ni el shim RPC.

### Entrada del detalle completada en el bloque anterior

- `proyectos/<id>/` sirve `pages/project_detail.html`, con el mismo contexto,
  CSRF, permisos y regreso de `views.proyecto_detalle`. La anterior queda en
  `?vista=anterior` mientras `anterior_disponible()` lo permita.
- `project_detail/main.js` carga el shim y el componente anterior en orden;
  `data.js` llama a API v1 para filtros, dashboard ejecutivo y dashboard AER.
  También Actualizar usa esas lecturas, con timeout de 90 segundos. El archivo
  anterior tiene dos helpers transitorios: con entrada modular usan API; en
  comparación conservan RPC. Las demás llamadas y acciones no se modificaron.
- Servicios Python, cifras y payloads idénticos. Se conserva el alcance total
  exigido por esas tres lecturas RPC, porque todavía contienen bloques del
  portafolio. No abrirlas a alcance limitado sin recortar antes sus servicios.
- Comparación visual de las entradas AER e IXB a 1450 y 390 px; datos de prueba
  iguales, tablas/cajas/estilos y capturas en
  `tmp/migration/project_detail/entry/<aer|ixb>/<ancho>/`. Se prueban reintento
  de red, fallo de filtros, descarga fallida del componente y Actualizar.
- Validación: **21 pruebas API, diez de navegador y las dos pruebas anteriores
  del contenedor** aprobaron juntas (33). Dos pruebas Node nuevas y los cinco
  recorridos anteriores del motor pasaron juntos. Regresión general:
  **1248 aprobadas, una omitida**. JS completo: **124 aprobadas, tres fallos
  anteriores** (`cost_sprint_details`, `executive_report`, `financial`). Ruff,
  formato, mypy y `manage.py check` aprobados. No se activaron los permisos.
- **No está completada la pantalla ni la fase 10:** salvo ambos Ejecutivos,
  Esfuerzo y Recursos IXB/SaaS/RaaS,
  las pestañas siguen construyéndose con el JS anterior, incluyendo eventos
  en línea y acciones RPC. No eliminar todavía el shim ni sus archivos.
- **Continuación:** Planeación IXB/SaaS/RaaS y luego las demás pestañas.
  Conservar las reglas de presentación, fuentes, cifras y comparación visual.
  Siguen pendientes Planeación, Riesgos/RAID, Acciones, Recursos, Cliente e IA;
  IXB además contiene Comunicación y Azure DevOps. No duplicar el archivo
  completo ni cambiar los servicios mientras se separa la interfaz.
  Ambos Ejecutivos se completaron después de esta entrada, como se indica arriba.

## Última pantalla terminada
- **Proyecto simple** (`proyecto/<id>/`): `pages/project.html`, CSS externo y
  `project/main.js`. La ruta activa conserva el mismo contexto Python,
  redondeos, decisiones, riesgos, equipo, historial y alcance por cuenta.
  Siete pruebas de servidor y seis de navegador cubren datos, barras,
  navegación a la cuenta con regreso, errores parciales y comparación visual
  a 1450 y 390 px, con información completa y estados vacíos. Capturas en
  `tmp/migration/project/<ancho>/<full|empty>/`.
  Regresión general: **1215 aprobadas, una omitida**. Después se amplió la
  comparación a los estados vacíos, preservando también su relleno y color
  originales: cierre dirigido de Proyecto simple **19 aprobadas** (incluye
  sus seis pruebas de cálculo anteriores, sin modificarlas). Ruff, formato,
  mypy y comprobación de Django aprobados. JavaScript: **122 aprobadas y
  los tres fallos anteriores** (`cost_sprint_details`, `executive_report`,
  `financial`). La intermitencia de sesión en Acuerdos no apareció en esta
  regresión; no se modificó ni se da por corregida su causa.
  La cuadrícula conserva el desbordamiento móvil de la versión anterior;
  esta migración no rediseña la pantalla. **Siguiente: detalle grande del
  proyecto (`proyectos/<id>/`) por pestañas.**
- **EVA 1, 2 y 3**: plantillas `pages/eva{1,2,3}.html`, CSS y módulos
  separados; contexto Python, diseño y cálculos conservados. Los históricos
  existentes de EVA 1 y EVA 3 usan JSON y nodos DOM seguros. EVA 2 sigue sin
  desplegable de cerrados, como antes. EVA 1 mantiene filtros y CSV; EVA 3
  conserva lotes de dos proyectos, carga parcial, promedio de consumos,
  corte de 2026 y guardado del Burn pendiente en MPB, con reintento.
  Quince pruebas e2e aprobadas (1450 y 390 px, tablas y estilos, históricos
  originales frente a nuevos), 29 pruebas de API y dos comparaciones Node
  contra los scripts anteriores. Se mantienen los permisos y CSRF.
  JavaScript: 122 aprobadas y los tres fallos anteriores sin modificar.
  La primera regresión completa tuvo 1203 aprobadas y el fallo intermitente
  ya documentado de Acuerdos (HTTP 403 al cambiar un estado). Sus tres
  pruebas aisladas pasaron sin cambios. La segunda corrida tuvo también
  1203 aprobadas, una omitida y un fallo, esta vez en
  `test_flujos::test_acuerdos_se_consultan_y_modifican_con_sesion`: al
  recargar, la sesión terminó en el login. No se da por limpia la suite.
  Las tres pruebas de Acuerdos, ese recorrido de sesión y las quince de EVA
  pasaron juntos después: **19 aprobadas**, sin modificar permisos, sesiones
  ni pruebas de Acuerdos. La investigación de esa intermitencia queda aparte.
  Proyecto simple se completó después, como se indica arriba.
- **Facturabilidad por área** (`pages/billability_area.html`): General,
  Detalle recurso, KPIs, % Recurso y Detalle HRS. Datos mediante API v1;
  módulos separados, DOM seguro y CSS externo. Se conservan los servicios
  originales de GSE, deduplicación, lotes, caché, fuentes, errores por mes,
  festivos, jornadas, filtros, bandas/bajas, paginación y exportaciones.
  Pruebas de API: 41 aprobadas. Dos pruebas Node comparan el modelo con
  el JS anterior. Comparación visual a 1450 y 390 px de los cinco apartados
  y de un área seleccionada, con texto idéntico en las tablas.
  Veinte pruebas e2e aprobadas; regresión completa: **1160 aprobadas,
  1 omitida**. JavaScript: **120 aprobadas y los mismos tres fallos
  anteriores** del código sin migrar. Ruff, formato, mypy y comprobación
  de Django aprobados. La prueba anterior que exigía el shim ahora verifica
  tanto la ruta activa modular como `?vista=anterior`, sin perder controles
  de año, navegación, cookie CSRF ni enlaces.
  EVA 1–3 se completaron después, como se indica arriba.
- **Facturabilidad general, especialidad y recurso**: plantillas
  `pages/billability*.html`, CSS y JS separados, con el mismo contexto
  Python y los mismos permisos. Selector de periodo compartido, sin
  scripts ni estilos en línea en las plantillas. Doce pruebas e2e de
  cifras, filtros, navegación, errores y comparación visual a 1450 y
  390 px (selectores abiertos y cerrados); doce pruebas de servidor.
  Las anteriores siguen disponibles con `?vista=anterior`.
  La vista por área se completó después, como se indica arriba.
- **Capacidad: detalle diario** (`/capacidad-instalada/`):
  `pages/capacity_daily.html`, CSS separado y módulos `model.js`, `view.js`,
  `main.js`. API `screens/capacidad/diaria/` y `.../proyecto/`, sin shim RPC
  en el frontend activo. Se conservaron filtros, matriz, recursos, paginación,
  CSV, concurrencia de dos proyectos y reglas de horas. Comparación visual
  a 1450 y 390 px de matriz y recursos; nueve pruebas e2e y trece de API.
- **Capacidad: asignaciones mensuales** (`/operativa/capacidad-instalada/`):
  `pages/capacity.html`, CSS y JS separados; filtros GET y CSV sin cambiar.
  Tres pruebas e2e aprobadas (filtros/exportación y comparación visual a 1450
  y 390 px). El detalle diario también se completó después.
- **Inversión** completada en `0028959` con cinco pruebas e2e.
- **Costos** (`/ejecutiva/costos/detalle/?vista=proyectos`), commit `5c945dc`.
- Antes, con commit cada una: Comercial `a8239ca`, Todas las cuentas `b314f35`, Business Overview `dca99b5`, KPIs de DMs `b02e623`, diccionario `cf702aa`, cuenta `5277a21`, Delivery Manager `56d169e`, márgenes `8f53c08`, EVA-04 `8d50bb0`, Operativa `ca4434d`.
- `AGENTS.md` y `tools/migracion/`: `86c69d0`.

## Inversión completada al retomar

Se conservaron y completaron los cambios pendientes descritos abajo.
La diferencia de alto era el margen superior de un encabezado anulado por
`.ds .card h2`; se corrigió su prioridad sin modificar el diseño anterior.
`tests/e2e/test_inversion.py`: cinco pruebas aprobadas usando Chrome instalado
(`--browser-channel chrome`); compara estilos y cajas a 1450, 900 y 390 px,
además de datos, cambio de mes, barras, regreso y error de fuente.
Capturas: `tmp/migration/investment/<ancho>/previous.png` y `current.png`.
Los cálculos y las fuentes no cambiaron. El siguiente bloque es Capacidad.

### Cambios recibidos de Claude (registro histórico)

Inversión (`/operativa/inversion/`), inicialmente sin commitear:
Sin commitear (en el árbol de trabajo):
- `frontend/templates/pages/investment.html`, `frontend/static/styles/pages/investment.css`, `frontend/static/scripts/pages/investment/main.js`.
- `apps/portal/pages.py` (vista `investment`), `apps/portal/urls.py` (ruta), `apps/portal/views.py` (`inversion` usa `render_page`).
- `tools/migracion/migrate_page.py` e `inline2css.py` (ajustes: quita el `<main class="page">` anterior, cambia el include del encabezado y genera estilos `.x.x`).

Pendientes recibidos de Inversión (ya resueltos; referencia histórica):
1. Una diferencia de alto: la tarjeta «Por especialidad» mide ~15 px menos que la anterior (`two` 249 contra 263). Comparar `h2`, `.hs` y el pie `tfoot`, que probablemente tienen otro relleno por `components.css`.
2. Prueba e2e `tests/e2e/test_inversion.py` (estructura, cambio de mes que recarga con `?mes=`, barras con ancho, regreso a Operativa).
3. Correr la suite, comitear y actualizar el plan.

## Pruebas recibidas de Claude (referencia histórica)
- Última corrida completa (antes de Inversión): `pytest tests/portal tests/core tests/access tests/e2e` → 1044 pasaron, 1 omitida; `ruff check` limpio.
- node (`node --test tests/frontend/*.test.*`): 3 fallos que ya existían, del JS anterior (`executive_report`, `executive_numbers`/Comercial y `cost_sprint_details`); se retiran en la limpieza.
- Inversión: solo comparación de estilos contra la anterior (formulario y celdas iguales; queda la diferencia de alto). Todavía no se ha corrido pytest con ella.

## Siguiente paso concreto
Migrar el detalle grande del proyecto (`proyectos/<id>/`) por pestañas.
Proyecto simple, EVA 1–3 y Facturabilidad completa ya usan `frontend/`;
sus históricos y consultas diferidas están conservados.
El área lee `screens/facturabilidad/area/` y conserva sus cinco apartados.
Las pruebas comparan con `?vista=anterior`; las capturas se generan bajo
`tmp/migration/billability_area/`. El CSS anterior oculta la navegación de
apartados en móvil: se conservó y documentó, sin dar por probada una navegación
que ya no estaba disponible. Después del detalle por pestañas: limpieza.

## Publicación
- Se verificó `origin/main` y se publicó mediante push normal el rango
  `45c93bf..9e93e52` (17 commits), con autorización explícita del usuario.
- El detalle diario se completó y validó después, en un commit separado;
  publicación mediante push normal, manteniendo los pendientes ajenos fuera.

## Verificación al retomar con Codex
- EVA: **15 e2e y 29 de API aprobadas**, más dos contrastes Node con los
  scripts originales. Ruff, formato, mypy y `manage.py check` aprobados.
  JS completo: **122 aprobadas, tres fallos anteriores**. Dos regresiones
  completas: **1203 aprobadas, 1 omitida, 1 fallida** cada una, con los dos
  recorridos de sesión de Acuerdos descritos arriba. Corrida conjunta
  de esos recorridos y EVA: **19 aprobadas**. No atribuir a esta evidencia
  una regresión completa limpia ni marcar resuelta la intermitencia.
- Último bloque, Facturabilidad por área: **1160 aprobadas, 1 omitida**
  en la regresión completa; veinte pruebas e2e de esta pantalla y 41 de API.
  JavaScript: 120 aprobadas y tres fallos anteriores documentados. Los dos
  contrastes nuevos del modelo pasan. Los pendientes de Claude siguen fuera
  del commit, sin cambios.
- Facturabilidad: comparación visual y funcional de las tres vistas
  completada (`tests/e2e/test_facturabilidad.py`: 12 aprobadas).
  Validación de servidor: `tests/portal/test_billability_pages.py` y
  `test_views.py`: 68 aprobadas. Ruff, formato, mypy y revisión de Django
  aprobados. JavaScript conserva 118 aprobadas y los tres fallos anteriores.
- Regresión completa después de esas tres vistas: **1098 aprobadas,
  1 omitida**, con Chrome y los cuatro temporales excluidos. Se conservaron
  los pendientes de Claude sin modificarlos ni incluirlos en los commits.
- Última suite, tras detalle diario: **1074 aprobadas, 1 omitida**, con Chrome
  instalado y los mismos cuatro temporales excluidos. `ruff check`, formato,
  `mypy` de páginas/API y `manage.py check` aprobados.
- JavaScript actual: **118 aprobadas, 3 fallidas**. Las tres fallidas siguen
  siendo las del código anterior, sin cambios en sus archivos. Las tres
  pruebas nuevas del modelo diario pasan y contrastan sus resultados con el
  modelo anterior.
- En la primera regresión del detalle diario hubo una falla intermitente en
  `test_person_with_edit_changes_a_status_and_it_is_saved` (Acuerdos, HTTP
  403). Sus tres pruebas aisladas pasaron y la repetición completa pasó.
  No se modificaron la prueba, sus permisos ni el código de Acuerdos.
- Suite tras Inversión: **1049 aprobadas, 1 omitida** (Chrome instalado,
  `--browser-channel chrome --no-cov`; se excluyen los cuatro `test_zz_*`
  temporales recibidos).
- Suite final tras Capacidad mensual: **1052 aprobadas, 1 omitida** con el
  mismo comando. `ruff check` y `mypy apps/portal/pages.py` aprobados.
- JavaScript: **115 aprobadas y 3 fallidas**, las ya documentadas del código
  anterior: `cost_sprint_details.test.cjs`, `executive_report.test.cjs` y
  `financial.test.cjs`. No se modificaron sus archivos ni sus reglas.
- La prueba de cambio de mes de Inversión emite un único evento: Playwright
  ya genera `change` al rellenar un campo `month`; duplicarlo ocasionaba una
  carrera de navegación en la suite completa.
- Se usa Chrome instalado porque no está descargado el Chromium de Playwright.
- Comparación visual reproducible: `tests/e2e/test_inversion.py` y
  `tests/e2e/test_capacidad.py`; capturas bajo `tmp/migration/`.
- Se preservaron sin modificar los cambios recibidos de las herramientas
  `inline2css.py` y `migrate_page.py`, además de los temporales de Claude.

## Temporales (no comitear; borrar al terminar)
`shots_tmp/`, `tests/e2e/test_zz_*.py`, el worktree `../bd_op`. Copias versionadas de las herramientas en `tools/migracion/`.
