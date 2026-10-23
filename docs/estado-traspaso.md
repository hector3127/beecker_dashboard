# Estado de traspaso de la migración (24/10/2026)

Lee primero `AGENTS.md` y `docs/plan-migracion-frontend.md`.

## Bloque actual: fase 10, Ejecutivo IXB/SaaS/RaaS (pantalla aún parcial)

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
- **Siguiente: Esfuerzo IXB/SaaS/RaaS**, reutilizando componentes, sin cambiar
  su diseño ni cálculos. Después las demás pestañas. La pantalla grande y la
  fase 10 siguen parciales; no eliminar el JS anterior ni el shim RPC.

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
  las pestañas siguen construyéndose con el JS anterior, incluyendo eventos
  en línea y acciones RPC. No eliminar todavía el shim ni sus archivos.
- **Continuación:** Esfuerzo IXB/SaaS/RaaS y luego las demás pestañas.
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
