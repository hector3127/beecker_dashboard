# Estado de traspaso de la migración (24/10/2026)

Lee primero `AGENTS.md` y `docs/plan-migracion-frontend.md`.

## Bloque actual: Capacidad diaria, base ad14366 (26/10)

- Retiradas vista/entrada anterior, plantilla y CSS/JS de Capacidad diaria.
  No se cambian servicios, fuentes Histórico/Azure, horas ni modelo vigente.
  El nombre de ruta y enlaces se mantienen. Cookie CSRF de la vista retirada
  conservada en pages.capacity_daily; permisos/login y alcance total intactos.
- Ocho salidas completas del modelo ANTERIOR capturadas antes de borrar en
  tests/frontend/snapshots/capacity_daily_model.json. La prueba actual ya no
  ejecuta el script eliminado. Dos contratos vigentes sustituyen tests RPC;
  la interacción/carga/forzar/CSV se mantiene en navegador con/sin vista=anterior.
- Seis snapshots vigentes de matriz/recursos a 1450/900/390 px. Capturas completas
  idénticas antes/después y sin avisos de CSP en las pruebas con bloqueo real.
  1727 servidor, 504 Node y 23 Chrome pasan; comandos en el informe del bloque.
- La prueba de standalone se adapta a la entrada actual, sin fuentes y con
  cookie/login; corrigió una expectativa antigua de clase del body, sin cambiar
  diseño. Detalles y comandos: `docs/retiro-capacidad-diaria.md`.
- Recuento real: 19 HTML/32 estáticos portal; continuar otras comparaciones y CSP.
  No retirar otros servicios o shim aún usados ni activar política/accesos
  globales. Sin push, temporales ajenos intactos. Fase 11 sigue abierta.

## Bloque previo: Facturabilidad, base 18e69a1 (26/10)

- Retiradas tres plantillas anteriores: general, especialidad y recurso. Las
  rutas y respaldo Python usan frontend mediante `_current`, con el mismo
  contexto/cálculos/permisos. Área conserva su comparación, sin cambios.
- Nueve snapshots vigentes registrados ANTES del retiro a 1450/900/390 px
  comparan cajas, estilos y tablas; se repiten con CSP real en navegador.
  Seis PNG idénticos y tres solo cambian hora global. Mes y roles de enlaces
  obsoletos se prueban expresamente; doce casos servidor adicionales mantienen
  el rechazo antes de consultar fuentes y el montaje de plantilla vigente.
- 1724 servidor, 504 Node y 36 Chrome aprobadas. Evidencia final en
  `docs/retiro-facturabilidad.md`; los casos nuevos inicialmente esperaban QA
  en un título fijo, corregidos para comprobar casillas y datos, sin cambiar
  producción. No se omiten pruebas ni se actualizan snapshots tras borrar.
- Quedan 20 HTML/35 estáticos portal. Continuar otras comparaciones/CSP sin
  retirar componentes, servicios o motor aún usados. Temporales ajenos intactos,
  sin push. No activar CSP global ni ACCESS_ENFORCED; fase 11 sigue abierta.

## Bloque previo: EVA 2 y Capacidad mensual, base 7420d17 (26/10)

- Dos plantillas anteriores retiradas; rutas y respaldo Python usan frontend,
  con el mismo contexto, permisos, filtros y CSV. No se modifica Capacidad
  diaria ni las fórmulas o datos de EVA. Se conservan enlaces obsoletos.
- Seis snapshots vigentes guardados ANTES del retiro a 1450/900/390 px:
  cajas/estilos y tablas; las pruebas posteriores usan CSP real de navegador.
  Capturas mantienen geometría, solo cambia hora global. Se conserva desborde
  móvil previo (no confundir igualdad con arreglo responsive).
- 1715 servidor, 504 Node y 34 Chrome pasan, sin omisiones. Seis casos nuevos comprueban
  alcance/login/capacidad con parámetro obsoleto. El caso nuevo de navegador
  de EVA 2 inicialmente miraba la tabla resumen; se corrigió para mirar la de
  proyectos, sin tocar producción. Evidencia final en `docs/retiro-capacidad-eva2.md`.
- Quedan 23 HTML/35 estáticos de portal. Continuar otras comparaciones y CSP
  sin borrar bases/servicios/RPC aún utilizados. Bloqueo global y accesos sin
  activar; temporales ajenos intactos. Fase 11 abierta y cambios sin push.

## Bloque previo: limpieza agrupada sobre 1e17d99 (26/10)

- 21 archivos/1 420 452 bytes retirados, con consumidores auditados. Las
  versiones anteriores de Inversión/Proyecto simple/Todas las cuentas ya no
  se sirven: `_current` conserva contexto Python y permisos. Cuatro huérfanos
  de portal también fuera. Ver inventario en `docs/limpieza-por-lotes.md`.
- /legacy/ sigue existiendo pero solo redirige; no usa core/index ni los doce
  HTML de templates/legacy ni legacy_skin. Se retiraron esos 14 archivos y
  una prueba obsoleta GSE; cinco pruebas Django mantienen redirecciones/login.
  No se toca gas_shim ni proyecto_detalle.js: otras comparaciones los usan.
- Siete snapshots JSON vigentes registrados ANTES del retiro mantienen cajas,
  estilos y textos/barras. Revalidación con CSP real de prueba. Proyecto y
  Todas las cuentas: capturas idénticas; Inversión: solo cambia hora global.
- 1711 servidor, 504 Node y 28 Chrome aprobadas; Ruff/formato y mypy pasan.
  Detalle de comandos/corridas solapadas/referencias en el informe del lote.
- Quedan 25 HTML/35 estáticos de portal; continuar por consumidores. No borrar
  servicios, RPC o CSS compartido en bloque ni activar accesos/CSP global.
  Temporales ajenos intactos. Sin push de este bloque; fase 11 sigue abierta.

## Bloque previo: retirada referencia KPIs DM, base 3c5b2fa (26/10)

- Se hizo el push solicitado hasta `3c5b2fa` antes de este bloque. No revertir
  integración Christian, logos, Comercial ni Capacidad diaria.
- Retirados vista/plantilla anterior de KPIs DM, su bifurcación y kpi_chart.js
  de portal. Sus dos pruebas Node importan la gráfica modular actual y mantienen
  todos los casos, sin VM ni archivo anterior. API/contexto/fórmulas intactos.
- Las pruebas de cortes/contexto se adaptan al constructor usado por API y al
  contrato JSON actual. Navegador cubre agrupaciones TP/T/C, nota explicativa,
  filtros, navegación, series/escala, ausencia de histórico y errores/reintento.
- Enlaces antiguos abren la modular; no cargan datos en HTML ni evitan permisos.
  Capturas idénticas a 1450/900/390 px antes/después; las posteriores con CSP real
  de pruebas. Referencias ignoradas: tmp/fase11/kpis-before y tmp/design/kpis-reference.
- 1693 servidor (incluyen las 78 dirigidas), 505 Node y 40 Chrome aprobadas; revalidación de KPIs:
  10 aprobadas (nueve solapadas + histórico ausente nuevo). Se corrigió otra
  carrera de la prueba de periodo en Facturabilidad esperando red en reposo,
  sin tocar producción ni omitir casos. Ruff/formato y mypy pasan.
- Siguiente: demás comparaciones y archivos anteriores, CSP de ventanas/
  gráficas/capturas representativas y cierre integral. Quedan 30 HTML y 36
  estáticos de portal. No retirar servicios de views.py ni bases compartidas
  en bloque; no activar CSP global ni ACCESS_ENFORCED. Nuevos cambios sin push.

## Bloque previo: integración Christian, base 3410e89 (26/10)

- No revertir logos unificados (0de6c7d), comando de datos (3410e89), Previas
  al cierre (47d0364), ni Capacidad diaria (834bbfa). Lecturas nuevas con
  apiGet o catálogo común; multipart de logos conserva su excepción.
- Reorganizadas las 17 entradas indicadas: datos puros, vistas y coordinación
  separados, JSDoc y ts-check. Las fachadas conservan imports públicos. Los
  renderizadores usan contratos de estado vivo/callbacks para no copiar filtros
  o página obsoletos. No modificar las fórmulas para coincidir con otro reporte.
- Doce CSS exclusivos integrados en seis hojas; acuerdos_reference sigue
  compartida. IA IXB conserva id base; se retiró su enlace ref redundante y se
  ajustó la comprobación de estilos. No reintroducir las hojas retiradas.
- 1691 servidor, 505 Node, 57 navegador finales aprobadas. Base 3410e89:
  54 referencias, 53 capturas (42 exactas, restantes hora/pintado). La corrida
  amplia anterior y las revalidaciones solapadas están documentadas, incluido
  un fallo de prueba por usar el selector antes de completar el módulo.
  La espera ahora usa los controles montados, sin cambiar producción.
- Leer `docs/integracion-christian.md` para la lista de pantallas y evidencia.
  El arnés local sirve assets/plantillas desde git show, sin checkout ni revertir
  cambios. Los temporales y credenciales no se incluyen. Sin push.
- Fase 11 sigue abierta: otras referencias antiguas, CSP de gráficas/ventanas
  y capturas representativas y cierre integral. No activar permisos ni CSP
  global, no borrar servicios JSON ni bases compartidas en bloque.

## Bloque previo: fase 11, diccionario y captura con CSP (26/10)

- Retiradas vista/plantilla anterior del diccionario y su bifurcación. Se
  conservan URL/nombre, búsqueda/orden/categorías, definiciones/API y login.
  Enlaces obsoletos mantienen búsqueda y pantalla modular. Referencias visuales
  vigentes idénticas antes/después a 1450/900/390 px, con CSP real en pruebas.
- La captura PNG REAL en la guía detectó dos estilos estáticos bloqueados.
  `CAPTURE_STYLE_HASHES` permite solo sus huellas exactas, sin unsafe-inline
  ni editar vendor. Revalidar si cambia html2canvas 1.4.1 o CSS de onclone.
- 1686 servidor (portal/core/accesos), 54 Chrome y 498 Node aprobadas;
  se repitieron las 15 pruebas de captura tras
  eliminar su dependencia del corte anterior. Ruff/formato y mypy pasan.
- Siguiente: otras referencias, gráficas/ventanas y capturas representativas
  con CSP real. No confundir la captura de la guía con certificación de todas
  las pantallas. Bloqueo global/accesos no activados. No borrar servicios JSON
  ni bases compartidas en bloque; quedan 31 HTML anteriores. Sin push.

## Bloque previo: fase 11 iniciada, retirada referencia EVA-04 (26/10)

- Eliminadas `views.eva4`, su plantilla `portal/eva4_anterior.html` y la
  bifurcación de `pages.eva4`. El parámetro obsoleto no rompe enlaces guardados:
  presenta frontend modular, mantiene mes y no consulta fuentes en el HTML.
- Las pruebas de disponibilidad/caducidad anteriores se sustituyeron por
  comprobaciones del contrato actual; no se eliminó cobertura de API/datos.
- Se guardaron capturas deterministas antes del retiro y se repitieron con
  CSP de bloqueo en el navegador. Son idénticas píxel a píxel a 1450/900/390.
  Referencias locales ignoradas: `tmp/fase11/eva4-before/`; resultado en
  `tmp/design/eva4-reference/`. No se modificaron estilos ni fórmulas.
- 1682 pruebas de servidor (portal/core/accesos), 498 Node y 38 Chrome aprobadas. Incluyen
  fuente/fallos/reintento, filtros, CSV, alcance limitado, navegación, logos y
  captura compartida. La captura real NO se ha certificado con CSP de bloqueo.
- Fixture `enforced_csp` en `tests/e2e/conftest.py`: aplica la política recibida
  a documentos locales del navegador de prueba, manteniendo bloqueo de red
  externa. No cambia middleware/configuración/despliegue; el caso CSP verifica
  además que recibió cabecera efectiva de bloqueo.
- `ANTERIOR_HASTA`/`anterior_disponible` siguen compartidos por otras pantallas;
  no borrarlos todavía. Próximo bloque: retirar comparaciones de otras pantallas
  con sus referencias vigentes y validar captura/gráficos/ventanas con CSP real.
  No borrar servicios de views.py ni bases compartidas en bloque. Sin push.

## Bloque previo: integración validada; entrada a fase 11 (26/10/2026)

La fase 10 sigue cerrada. Integrados y revisados los cambios de diseño/logos
de `24cd3cf` y fechas de `834bbfa`. Migración local `portal.0003_account_logo`
aplicada con respaldo previo; otros entornos deben ejecutar migrate.
Corregidos tipado/formato y regresión del rango MPB repetido: el acceso normal
vuelve a abarcar todas las filas, igual que antes de esa integración.
Se conservan los demás cambios funcionales y el diseño del compañero.

388 pruebas de servidor, 498 Node y 74 Chrome aprobadas. Una nueva prueba
CSP confirma la decodificación de la vista previa del logo con bloqueo real
solo en el navegador de pruebas; repetición completa logos/CSP: 15 aprobadas
(solapan con las anteriores). Ruff/formato, mypy, check y migraciones pasan.
No es una segunda ejecución de toda la suite general ni una certificación
visual de todas las pantallas nuevas. No se activa CSP global ni accesos.

**Continuar por `docs/preparacion-fase-11.md`:** retirar comparaciones/archivos
anteriores conservando pruebas del producto vigente, no borrar servicios JSON
ni cálculos de views.py, auditar CSP de captura/gráficos/ventanas y ejecutar
el cierre completo. No reabrir fase 10 ni dar fase 11 por terminada.
Temporales ajenos intactos. Sin push.

## Cierre previo: fase 10 completada y validada (26/10/2026)

- La plantilla activa ya no referencia `proyecto_detalle.js`, `gas_shim.js`
  ni el CSS de portal. El CSS compartido se copia sin cambios de bytes a
  `project_detail_base.css`. Main arranca directamente con sus controladores.
- Auditoría: `proyectos/<id>/` siempre siembra ID desde Django; selectores de
  cuenta/proyecto están ocultos. Cuenta usa su propia ruta modular. La ruta
  actual recupera el ID sembrado si queda el selector centinela y no recurre
  al dashboard de cuentas anterior. Controles desconectados no causan recursión.
  Las ramas de reportes/cuenta originales permanecen para comparar, no como
  dependencias del detalle activo. No se copia el megabyte a frontend.
- `project_commands.js` conserva nombres públicos como delegados a los módulos,
  sin renderizadores, formularios ni RPC. El caché Cliente/Acciones también
  tiene un accesor sobre el almacén para sus consumidores previos.
- `project_reference.py` carga definiciones originales SOLO en las pruebas
  que desactivan modelos para contrastar cálculos o el inicio especial. Las
  pruebas normales no lo usan y comprueban cero descargas de script/shim/RPC.
- **478 Node aprobadas**; **38 navegador dirigidas aprobadas** inicialmente.
  Incluyen cinco familias, ruta/controles, inicio/reintento y referencias.
  Ruff/formato (653 archivos), Django y mypy aprobados. El único cambio Python
  de producción es formato de una expresión en `project_ai.py`.
- La primera revisión amplia dio 1356 aprobadas y cinco fallos: dos espías de
  recarga antiguos, dos referencias que esperaban el script implícito y un
  cierre de Comunicados conectado al modal incorrecto. Corregidos y revisados.
- Se ejecutó la suite general completa: **3853 aprobadas, 8 fallidas y una
  parametrización vacía omitida**, de 3862 casos, en 54 min. Los ocho fallos
  eran una expectativa del script anterior, tres usos del normalizador privado
  anterior, dos espías del renderizador sustituido y dos comparaciones de
  coordenadas de nodos ocultos. Las capturas de estas últimas son idénticas
  byte por byte a 1450 y 900 px; se conservan todos los controles de texto,
  estilos, dimensiones y SVG, sin restar el origen a rectángulos nulos.
- La lista vacía de login se sustituyó por **tres APIs vigentes**, con rechazo
  anónimo antes de consultar fuentes. No se añadió ninguna marca de omisión.
- Revalidación completa de archivos afectados: **55 aprobadas, cero fallos,
  cero omisiones**, en 135 s. Código de producción estable durante la corrida
  general; las correcciones posteriores son pruebas. Resultado consolidado:
  **3864 casos Python verificados**, sin casos pendientes. No confundir esta
  evidencia (corrida general + revalidación) con una segunda corrida general.
- Comando general: `.venv/Scripts/python.exe -u -m pytest tests -q --no-cov
  --browser-channel chrome --ignore=tests/e2e/test_zz_dom.py
  --ignore=tests/e2e/test_zz_pages.py --ignore=tests/e2e/test_zz_seq.py
  --ignore=tests/e2e/test_zz_styles.py`. Solo excluye diagnósticos ajenos,
  no versionados. Incluye **1264 pruebas de navegador**, con referencias en
  tres tamaños; capturas de entrada AER escritorio e IXS móvil inspeccionadas.
- Revalidación: prueba de encabezado inicial en `tests/test_api.py`, archivos
  `test_ixs_support.py`, `test_project_entry_loading.py`, `test_generic_charts.py`
  y `tests/portal/test_executive_merge.py`, con `-q --no-cov
  --browser-channel chrome -rs`.
- **Fase 10 cerrada.** Lo pendiente es fase 11: retirar originales/pruebas de
  comparación y preparar CSP, sin modificar diseño/cálculos. No activar
  ACCESS_ENFORCED ni enviar correos reales. Proveedores simulados/red externa
  bloqueada en navegador. Temporales ajenos intactos y sin push.

Los bloques inferiores son históricos; sus estados «parcial» no sustituyen
este cierre vigente. No repetir la migración de pestañas o proveedores retirados.

## Bloque anterior: inicio especial modular (26/10/2026)

- `project_entry.startCompatibility` reemplaza el inicio especial anterior:
  sin proyecto/cuenta no hace lecturas; obtiene filtros por API, conserva
  selección por nombre sin distinguir mayúsculas y agrega opciones ausentes.
  Si existen ambos parámetros, proyecto conserva prioridad y restablece cliente.
  Lee los parámetros después de filtros, conecta Actualizar y carga una vez,
  incluso si fallan filtros. La selección segura vive en `project_entry_view`.
- El puente moderno inicia directamente con ese controlador y un contexto
  vigente, sin llamar `initDashboard(true)`. La comparación conserva el cuerpo
  anterior. No se cambian backend, cifras, diseño ni permisos.
- **475 Node aprobadas, cero fallos; 30 navegador aprobadas**: 13 nuevas
  comparan selección/opciones/metadatos/orden de carga/refresco con el inicio
  original a 1450/390 px y bloquean el callback anterior; 17 de arranque,
  entrada/recarga existentes incluyen sus comparaciones visuales. Ruff/formato,
  Django y diff aprobados. Datos simulados y red externa bloqueada.
- **Fase 10 parcial**: la carga sin proyecto (`previousLoad`), reportes y
  riesgos especiales siguen en compatibilidad. No retirar script/shim todavía.
  Mantener comparación y continuar por esos proveedores; no reabrir pestañas.
  Temporales ajenos intactos; sin push.

## Bloque anterior: estado de reportes de compatibilidad (26/10/2026)

- Los cachés AER/IXS, la secuencia de consumos y el indicador de arranque de
  reportes pertenecen a `project_state.js`. Los cuatro nombres anteriores son
  accesores sobre el mismo estado; cargar las definiciones no reinicia un corte
  existente. La comparación conserva sus valores independientes originales.
- `project_compatibility.js` obtiene cuenta y reportes directamente del DOM y
  almacén, sin proveedores de caché/cuenta del archivo anterior. Conserva la
  segunda comprobación de cuenta tras refrescar y lee el corte vigente.
- **474 Node aprobadas, cero fallos; 27 pruebas de navegador aprobadas**:
  estado compartido AER/IXS, arranque/reintentos, entrada, pestañas y recarga.
  Incluyen las comparaciones visuales existentes de entrada. No cambia markup,
  CSS, cálculos ni servicios; proveedores simulados y red externa bloqueada.
  Ruff/formato, Django y diff aprobados.
- **Fase 10 parcial.** Continúan en el archivo anterior los proveedores de
  inicio/carga y presentación de los reportes especiales y riesgos. Todavía
  carga script/shim: el cambio de dueño del estado no elimina esa dependencia.
  Seguir por esos proveedores; mantener comparación y no reabrir pestañas.
  Temporales ajenos intactos; sin push.

## Bloque anterior: contratos de compatibilidad separados (25/10/2026)

- `project_compatibility.js` conserva selección/refresco, segunda comprobación
  de cuenta, lectura actual de cachés y orden de reportes/riesgos. Inicio/carga
  conservan callbacks síncronos, argumentos y resultados. La coordinación ya
  no está en el cuerpo anterior; este suministra proveedores explícitos y
  conserva un respaldo de comparación. No se cambian cálculos, vistas ni permisos.
- Tres Node nuevos contrastan el módulo con el respaldo para las combinaciones
  de cuenta antes/después de refrescar, cachés y selector ausente; verifican
  identidad de callbacks y lectura del corte más reciente.
- **472 Node aprobadas, cero fallos**. Los tres fallos anteriores fueron
  corregidos en `1108577` (pruebas desactualizadas, sin cambios de producción).
  Cuatro pruebas backend del contrato comercial también aprobadas.
- **51 pruebas únicas de navegador aprobadas**: cinco de arranque/reintento,
  20 de entrada/pestañas/recarga, cinco del enlace anterior, nueve de genérico,
  diez de estructura y dos de runtime IXS. Conservan comparaciones AER/IXS a
  1450/390 px y contenido genérico en tres tamaños. Proveedores simulados,
  red externa bloqueada y sin operaciones reales. Django, sintaxis JS y diff
  aprobados; archivos de pruebas Python sin cambios en este bloque.
- **Fase 10 parcial.** Aún se carga script/shim por los proveedores de inicio/
  carga/cuenta, cachés y reportes. Seguir sustituyendo esas dependencias activas;
  no confundir mover el contrato con haber eliminado la dependencia. Mantener
  comparación, ACCESS_ENFORCED apagado y Horas por mes intacta. Temporales/
  herramientas ajenos conservados. Sin push.

## Bloque anterior: pruebas anteriores corregidas (25/10/2026)

- Los tres fallos Node eran pruebas desactualizadas: parser del bloque scripts
  de Costos (ahora precedido por formatter externo) y expectativas comerciales
  de contactos/Pendiente que no corresponden al contrato actual.
- Se reparan las pruebas conservando sus verificaciones de consulta única,
  no duplicar revenue, texto escapado, cifras del corte y datos faltantes.
  No se cambian producción, cálculos ni reglas para obtener coincidencias.
- **469 Node aprobadas, cero fallos**; cuatro pruebas backend del contrato
  comercial aprobadas. Detalle y evidencia en el plan.
- Fase 10 parcial. Continúa la separación de dependencias/puentes del archivo
  anterior; no retirar aún script/shim ni activar ACCESS_ENFORCED.

## Bloque anterior: arranque explícito y carga única (25/10/2026)

- Main carga las definiciones anteriores en modo manual, conecta el puente
  `projectCompatibilityBindings` y llama `beeProjectEntry.mount`. El inicio
  moderno no ejecuta renderView/projectEntryContext/initDashboard. El script
  anterior conserva autoinicio para comparar cuando no tiene el atributo manual.
- El puente mantiene los callbacks especiales previousStart/previousLoad/
  clientChanged, sus cachés, orden y puerta de cuenta. No se eliminan ni cambian
  sus reglas. Todavía dependen de definiciones del archivo anterior.
- `project_script_loader.js` reutiliza scripts evaluados entre intentos y
  comparte descargas concurrentes; una descarga fallida se elimina y puede
  reintentarse. Así el reintento tras fallar la conexión del puente no vuelve
  a declarar variables léxicas globales. Aviso/botón de recuperación conservados.
- Tres Node nuevos: carga única/concurrencia, fallo/reintento y callbacks del
  puente en cuenta/no cuenta con/sin cachés. Suite completa: **466 aprobadas y
  tres fallos anteriores** (`cost_sprint_details`, `executive_report`,
  `financial`). Cinco pruebas nuevas de navegador aprobadas: arranque AER/IXS
  bloqueando tres entradas anteriores, descarga fallida de shim/script y
  reintento después de evaluar el script sin descargarlo ni ejecutarlo de nuevo.
- **51 pruebas únicas de navegador aprobadas**: cinco nuevas, 20 de entrada/
  pestañas/recarga, cinco de navegación anterior, nueve de genérico, diez de
  estructura y dos de runtime IXS. Incluyen comparación de entrada anterior/
  nueva en AER/IXS a 1450/390 px y las comparaciones existentes en tres tamaños.
  Capturas en `tmp/migration/project_detail/entry/`, `project_previous/`,
  `generic_executive/` y `generic_layout/`. AER móvil actual inspeccionado.
  Ruff/formato, sintaxis JS, Django y diff aprobados. Proveedores simulados/
  red externa bloqueada, sin operaciones reales.
- **Fase 10 parcial.** El arranque ya pertenece a main, pero el script/shim
  aún se cargan por definiciones/puentes. Seguir por inventario de referencias
  activas y sustitución de esos contratos; no llamarlo todavía arranque
  totalmente independiente. No borrar comparación ni activar CSP (fase 11).
  ACCESS_ENFORCED apagado; Horas por mes y temporales/herramientas ajenos intactos.
  Sin cambios de backend/cálculos/permisos y sin push.

## Bloque anterior: enlace al genérico y auditoría de compatibilidad (25/10/2026)

- `project_previous.js` maneja IXS→genérico→IXS desde el respaldo de pestaña
  desconocida. Usa controladores migrados, DOM seguro y evento externo para
  regresar. Conserva objeto de proyecto, guardia por ID, pestaña resumen y
  montaje sin recarga. Main ya no invoca `ixsAbrirVistaAnterior`; sus dos
  nombres anteriores solo delegan. CSS en la hoja genérica existente.
- Auditoría: detalle usa `proyectos/<str:project_id>/`, siembra ese ID en
  `project_context` y `projectParams` lo prioriza al query. Cuenta usa su
  ruta/frontend independiente. El query de cuenta no convierte el detalle en
  la ruta de cuenta (prueba con cuenta=ACME&proyecto=OTHER y ruta AMK.008).
- Se conservan los casos especiales sin proyecto/cuenta. Siguen conectados
  por `projectEntryContext` como previousStart/previousLoad/clientChanged.
  El arranque real todavía ocurre con `renderView('dashboard')` al final del
  script anterior, cargado por main. Seguir por ese arranque y sus contratos;
  no migrar ni borrar ramas solo por inferir que no se usan en navegación normal.
- Tres Node nuevos cubren proyecto ausente, objeto/ID exactos (incluye comillas),
  montaje directo y guardia del regreso de otro proyecto. Suite completa:
  **463 aprobadas y tres fallos anteriores** (`cost_sprint_details`,
  `executive_report`, `financial`). Cinco pruebas nuevas de navegador aprobadas:
  tres comparaciones completas a 1450/900/390 px con regreso, navegación con
  cinco funciones anteriores bloqueadas y prioridad del ID ante query cuenta.
  Capturas en `tmp/migration/project_detail/project_previous/`; escritorio
  nuevo inspeccionado. Proveedores simulados/red externa bloqueada.
- **46 pruebas únicas de navegador aprobadas**: cinco nuevas, nueve de
  genérico directo, diez de estructura, dos de runtime IXS y 20 de entrada/
  pestañas/recarga. Las cinco repetidas no se suman de nuevo. Ruff/formato,
  sintaxis JS, Django y diff aprobados.
- **Fase 10 parcial.** Siguiente: arranque, contratos de compatibilidad y
  auxiliares activos. Mantener script/shim y comparación. No activar
  ACCESS_ENFORCED ni tocar Horas por mes. Sin cambios de backend/cálculos.
  Temporales/herramientas ajenos intactos; sin push.

## Bloque anterior: coordinación y derivados del Ejecutivo genérico (25/10/2026)

- `generic_executive_model.js` conserva servicio/fecha PRD, riesgo/color,
  resumen temporal y detección de cierre. Devuelve las dos asignaciones de
  proyecto completado sin mutar los datos; `generic_executive.js` las aplica
  al objeto original, como antes, y actualiza ID/hitos del almacén.
- El controlador monta directamente estructura, encabezado/KPIs, recursos,
  resumen, línea temporal, gráficas y fuentes API. No ejecuta renderer ni
  auxiliares anteriores. Error/datos faltantes conservan texto/apariencia con
  DOM seguro. `project_entry_runtime.js` llama al módulo en servicios no AER/
  IXS. El nombre anterior delega cuando están los módulos; su cuerpo original
  sigue disponible para comparar y para los respaldos temporales.
- Cinco Node nuevos contrastan contexto/asignaciones con el código original
  para cortes/servicios/estados y verifican cierre, metadatos/fechas, modelo
  sin mutación y entrada directa. Suite completa: **460 aprobadas y tres
  fallos anteriores** (`cost_sprint_details`, `executive_report`, `financial`).
- Nueve pruebas nuevas de navegador aprobadas: entrada genérica real y
  actualización/reintento con seis funciones anteriores bloqueadas, seis
  comparaciones de error/vacío a 1450/900/390 px y montaje/error con innerHTML
  bloqueado. Verifican rango/RAID/tasks por API, sin RPC, estado y regreso.
  Capturas en `tmp/migration/project_detail/generic_executive/`; error móvil
  nuevo inspeccionado. Proveedores simulados/red externa bloqueada.
- **106 pruebas únicas de navegador aprobadas**: nueve nuevas, diez de
  estructura completa, 25 de encabezado/KPIs (incluido cierre), 22 de fuentes,
  20 del formulario de riesgos y 20 de entrada/pestañas/recarga. No se suman
  de nuevo las nueve repetidas en la regresión. Ruff/formato, sintaxis JS,
  Django y diff aprobados.
- **Fase 10 parcial.** Siguiente: auditar compatibilidad sin proyecto/cuenta,
  enlace de vista anterior y auxiliares activos; después arranque independiente.
  Mantener script/shim y comparación. No activar ACCESS_ENFORCED ni tocar
  Horas por mes. Sin cambios de backend/permisos ni datos reales. Temporales/
  herramientas ajenos intactos; sin push.

## Bloque anterior: tarjetas y controles genéricos (25/10/2026)

- `generic_layout_view.js` y `project_detail_generic_layout.css` construyen la
  estructura con DOM seguro, sin HTML interpolado ni eventos inline. Conserva
  grillas, IDs, cargas, textos/iconos y resumen RAID; reutiliza los componentes
  ya migrados. Tipografía y botones conservan los valores de la anterior.
- Agregar Hito/Riesgo abre directamente los controladores migrados. Guardar
  hito recarga por el runtime modular y conserva el reintento. El renderer
  transitorio delega la estructura solo si sus componentes están disponibles;
  el HTML original sigue como respaldo de comparación/compatibilidad.
- Se compara el contenido completo contra la plantilla anterior a igual ancho
  y con cajas relativas, con datos/sin datos a 1450/900/390 px. Esto no equivale
  a completar la ruta genérica autónoma. Las limitaciones de desbordamiento
  móvil de la anterior se conservan. El test de modelo temporal desactiva la
  estructura en ambas referencias para aislar ese modelo; no cambiar sus datos.
- Capturas y diferencias en `tmp/migration/project_detail/generic_layout/`.
  Inspeccionada la captura nueva móvil completa. Suite Node completa:
  **455 aprobadas y tres fallos anteriores** (`cost_sprint_details`,
  `executive_report`, `financial`). No se cambian cálculos, backend, servicios
  ni permisos. Pruebas con proveedores simulados y red externa bloqueada.
- **84 pruebas únicas de navegador aprobadas**: diez de estructura (seis
  comparaciones de contenido completo, formularios sin helpers anteriores,
  DOM sin innerHTML y dos guardados/recarga/reintento), 12 del modelo temporal,
  20 del formulario de riesgos, 22 de fuentes y 20 de entrada/pestañas/recarga.
  Ruff/formato, sintaxis JS, Django y diff aprobados. No se suman las
  comparaciones repetidas durante el ajuste de tipografía.
- **Fase 10 parcial.** Siguiente: coordinación/estados y derivados genéricos
  que conserva `renderDashboardEjecutivoProyecto` (incluida su rama de error).
  Después: compatibilidad sin proyecto/cuenta y arranque independiente.
  Mantener script/shim y comparación. No activar ACCESS_ENFORCED ni tocar
  Horas por mes. Temporales/herramientas ajenos intactos; sin push.

## Bloque anterior: formulario de alta manual de riesgos genéricos (25/10/2026)

- `generic_risk{,_model,_view}.js` y `project_detail_generic_risk.css` conservan
  ventana, campos/opciones/defaults, validación, estados de guardado/error y
  cierre por Cancelar/cruz/fondo. DOM seguro y eventos externos. Los botones
  neutralizan las diferencias de la base nueva en tamaño/peso y deshabilitado.
- POST API v1 `screens/proyectos/<id>/riesgos-manuales/` reutiliza exactamente
  `write_rpc.add_risk`: hojas Riesgos/Histórico_Riesgos, validación y caché.
  No se cambia esta alta manual por una creación Azure. ID de la ruta,
  `edit_operations`, alcance total y CSRF. Los tres helpers anteriores solo
  delegan; éxito recarga por `beeProjectEntryRuntime.load()`, sin loadDashboard.
- Guardado único mientras está ocupado; respuesta de una ventana cerrada o
  proyecto distinto no cierra/sobrescribe el formulario nuevo. Error del
  servidor presentado como texto incluso con `innerHTML` bloqueado.
- Cinco Node nuevos: payload (solo trim de descripción), validación, guardado
  único, reintento, respuestas tardías y POST con ID codificado/timeout.
  Suite completa **455 aprobadas y tres fallos anteriores**
  (`cost_sprint_details`, `executive_report`, `financial`).
- Comparaciones en `tmp/migration/project_detail/generic_risk/`: formulario,
  validación, error de servicio y guardado a 1450/900/390 px. Inspeccionada
  ventana de error móvil y referencia escritorio. Proveedores simulados/red
  externa bloqueada; ninguna escritura real. No se modifican los temporales
  ni herramientas ajenos.
- **62 pruebas únicas de navegador aprobadas**: 20 del formulario (12
  comparaciones en cuatro estados/tres tamaños; guardado+recarga directa,
  validación/reintento, tres cierres, fallo de transporte, respuesta tardía y
  texto seguro), 22 de fuentes y 20 de entrada/pestañas/recarga.
  Las repeticiones de verificación no se suman dos veces.
  **100 pruebas backend aprobadas** (91 API y nueve del servicio anterior),
  incluidos ID de ruta, permisos, alcance, CSRF y contrato de errores.
  Ruff/formato, sintaxis JS, Django y diff aprobados.
- **Fase 10 parcial.** Siguiente: estructura de tarjetas/botones y coordinación
  del Ejecutivo genérico; después casos sin proyecto/cuenta y arranque
  independiente. Mantener script/shim, no activar ACCESS_ENFORCED ni tocar
  Horas por mes. Sin push.

## Bloque anterior: fuentes RAID y tareas del Ejecutivo genérico (25/10/2026)

- `generic_sources.js` usa las APIs v1 `raid/` y `tasks/` existentes;
  `generic_sources_model.js` conserva formato, filas/duplicados, orden,
  inversión, totales del servidor, rango truncado y tareas sin horas (incluye
  negativas como antes). No cambia servicios, permisos, alcance ni cálculos.
- `generic_sources_view.js` y `project_detail_generic_sources.css` conservan
  tabla, resumen, desplegable, tamaños/colores y mensajes. DOM seguro y CSS
  externo. Los dos helpers anteriores solo delegan en la ruta nueva; respaldo
  RPC conservado para comparar. Respuestas superadas o de nodos reemplazados
  no modifican los paneles/totales vigentes. El esqueleto de carga permanece.
- Cinco Node nuevos verifican formato/badges contra originales, orden,
  defaults, totales sin recálculo, no mutación, errores y respuestas tardías.
  Suite completa **450 aprobadas y tres fallos anteriores**
  (`cost_sprint_details`, `executive_report`, `financial`).
- **22 pruebas nuevas de navegador aprobadas**: 18 comparaciones con la
  anterior a 1450/900/390 px (lleno/vacío/error, ambas fuentes), dos fallos
  de transporte, texto seguro con `innerHTML` bloqueado y respuesta tardía
  tras reemplazar el panel. Verifican lecturas API sin RPC de estas fuentes,
  totales y desplegable abierto en tres tamaños. Capturas en
  `tmp/migration/project_detail/generic_sources/`; inspeccionados tareas móvil
  y tabla RAID escritorio. Proveedores simulados/red externa bloqueada.
- Regresión final: **64 pruebas únicas de navegador aprobadas** (las 22
  nuevas, 12 de modelo/fallback genérico, diez de rango Clockify y 20 de
  entrada/pestañas/recarga). **82 API aprobadas**, incluidos los contratos y
  permisos de las lecturas reutilizadas. Ruff/formato, sintaxis JS, Django y
  diff aprobados. No se suman dos veces las pruebas nuevas repetidas.
- **Fase 10 parcial.** Siguiente: acciones genéricas, incluido el formulario
  de alta de riesgos (`abrirModalRiesgo`/`guardarRiesgoDesdeModal`), estructura
  de tarjetas/botones y coordinación; después casos sin proyecto/cuenta y
  arranque independiente. Mantener script/shim, no activar ACCESS_ENFORCED,
  no tocar Horas por mes. Cambios/temporales ajenos intactos; sin push.

## Bloque anterior: rango Clockify por API (25/10/2026)

- `project_clockify_range.js` controla la lectura Discovery→Deployment por
  `screens/proyectos/<id>/clockify-rango/`. Backend con el mismo repositorio y
  `project_rpc.project_range`; conserva permiso `view_operations`, alcance
  total y contrato original. El helper anterior delega en la ruta nueva,
  manteniendo RPC para la comparación. No cambia datos, cálculos ni fechas.
- Mantiene «Consultando rango…», texto/fechas locales y vacío ante fallos o
  datos faltantes. Respuestas superadas y nodos reemplazados no se repintan.
  No añade estilos ni modifica Horas por mes. Se conserva el comportamiento
  de fecha sin hora documentado en el bloque del encabezado.
- **82 pruebas API y 49 de navegador aprobadas**: diez del rango (nueve
  comparaciones contra anterior a 1450/900/390 px y fallo de transporte),
  19 de paneles y 20 de entrada/pestañas/recarga. Proveedores simulados y red
  externa bloqueada. Capturas en `tmp/migration/project_detail/clockify_range/`;
  fecha móvil nueva y escritorio anterior inspeccionados. Cinco Node nuevos
  verifican formato/transporte/carga/errores y respuestas tardías. Suite Node
  completa: **445 aprobadas y tres fallos anteriores** (`cost_sprint_details`,
  `executive_report`, `financial`). Ruff/formato, Django, sintaxis JS y diff
  aprobados. Auxiliares/temporales ajenos intactos.
- **Fase 10 parcial.** Siguiente: fuentes RAID/tasks, acciones, estructura de
  tarjetas/botones y coordinación genérica; después casos sin proyecto/cuenta
  y arranque independiente. Mantener script/shim y ACCESS_ENFORCED apagado.
  Commit local en main, sin push.

## Bloque anterior: gráficas genéricas por área, recurso y rol (25/10/2026)

- `generic_charts_model.js` conserva total/redondeo, SVG, paleta, orden y escala
  de toda la lista. `generic_charts_view.js` dibuja con DOM/SVG seguro y CSS
  externo. `generic_charts.js` monta y controla Ver todos/menos con eventos
  externos locales. Mantiene cinco filas iniciales e IDs originales.
- El renderer transitorio delega directamente; los helpers anteriores no se
  ejecutan en estas gráficas y se conservan para otras rutas/comparación.
  No cambia cálculos, fuentes, permisos ni datos. Expandir no realiza lecturas.
- Tres Node nuevos contrastan arcos/offsets, total y barras contra helpers
  originales; verifican escala de filas ocultas, orden, paleta y ausencia de
  mutación. Suite completa **440 aprobadas y tres fallos anteriores**
  (`cost_sprint_details`, `executive_report`, `financial`).
- **61 pruebas únicas de navegador aprobadas**: 29 de gráficas (27
  comparaciones contra la anterior a 1450/900/390 px, expansión local y texto
  seguro), 12 de pantalla modelo/fallback y 20 de entrada/pestañas/recarga.
  Igual ancho de referencia y cajas relativas; se contrastan también SVG
  namespace/fill/stroke/offsets. La expansión bloquea tres helpers anteriores
  y verifica que no haya solicitudes. Texto probado con `innerHTML` bloqueado.
  Capturas en `tmp/migration/project_detail/generic_charts/` y
  `generic_timeline/`; área y recursos con filas ocultas inspeccionados.
  Ruff/formato, sintaxis JS, Django y diff aprobados. Proveedores simulados/red
  bloqueada, sin consultas reales. No se modifican auxiliares/temporales ajenos.
- **Fase 10 parcial.** Siguiente: fuentes/acciones, estructura de tarjetas/
  botones y coordinación genérica; después casos sin proyecto/cuenta y arranque
  independiente. Mantener script/shim, no activar ACCESS_ENFORCED ni tocar
  Horas por mes. Sin push; cambios/temporales ajenos intactos.

## Bloque anterior: encabezado y seis indicadores genéricos (25/10/2026)

- `generic_header_model.js` conserva metadatos, defaults, presupuesto, umbral
  de ritmo, etiquetas de cierre y fecha PRD/estimada. La vista usa DOM seguro
  y SVG nativo para el mini-donut; CSS fijo externo. Se conserva el ID financiero.
- El renderer transitorio suministra flags de color/riesgo/cierre y monta los
  componentes; no construye el HTML anterior de encabezado/KPIs ni el helper
  HTML del mini-donut. La coordinación y las demás gráficas/fuentes/acciones
  genéricas siguen pendientes. No marcar completa toda la pantalla.
- Cuatro Node nuevos contrastan geometría/etiqueta del donut con su helper
  original y verifican umbral, cierre, defaults, strings numéricos y fecha
  PRD/estimada. Suite completa **437 aprobadas y tres fallos anteriores**
  (`cost_sprint_details`, `executive_report`, `financial`).
- Observación heredada, sin corregir: el formatter original `new Date(valor)`
  más `toLocaleDateString('es-MX')` muestra `2026-08-01` (sin hora) como
  `31 jul 2026` en el entorno local. Se verificó igual en referencia/modular
  durante el caso completado. Revisar funcionalmente las fechas sin hora fuera
  de la migración; no se cambiaron las reglas ni se consultaron datos reales.
- **57 pruebas únicas de navegador aprobadas**: 25 de encabezado/KPIs,
  12 de pantalla moderna modelo/fallback y 20 de entrada/pestañas/recarga.
  Se comparan metadatos e indicadores contra la anterior a 1450/900/390 px,
  con datos faltantes, cierre y salida no PRD, en igual ancho de referencia
  y posiciones relativas. Se contrasta también namespace/estilos SVG y texto
  seguro con `innerHTML` bloqueado, conservando el ID financiero. Capturas en
  `tmp/migration/project_detail/generic_header/` y `generic_timeline/`;
  cierre escritorio y metadatos faltantes móvil inspeccionados. Ruff/formato,
  sintaxis JS, Django y diff aprobados. Proveedores simulados/red bloqueada;
  auxiliares en `tmp/` sin comitear.
- **Fase 10 parcial.** Siguiente: gráficas/fuentes/acciones genéricas y su
  coordinación; después casos sin proyecto/cuenta y arranque independiente.
  Mantener script/shim. No activar ACCESS_ENFORCED ni tocar Horas por mes.
  Sin push y con temporales/cambios ajenos intactos.

## Bloque anterior: tabla de recursos y resumen de hitos genéricos (25/10/2026)

- `generic_panels_model.js` conserva presentación de filas/totales, redondeo,
  estados, formato de fechas, notas y agrupación/orden de hitos. La vista
  `generic_panels_view.js` usa DOM seguro y CSS externo. No cambia reglas,
  cifras, permisos ni fuentes. Mantiene IDs de tarjeta y rango Clockify.
- El renderer transitorio monta ambos componentes en marcadores estáticos,
  sin ejecutar su HTML anterior. El resto genérico sigue pendiente; no dar
  por migrada toda la pantalla. Las comparaciones aisladas usan el mismo
  ancho de referencia y posiciones relativas por las diferencias del
  contenedor genérico todavía pendientes.
- Cuatro Node nuevos contrastan estados/fechas contra helpers originales y
  verifican redondeo, defaults, notas, orden y que no se muten los datos.
  Suite completa **433 aprobadas y tres fallos anteriores**
  (`cost_sprint_details`, `executive_report`, `financial`).
- **51 pruebas únicas de navegador aprobadas**: 19 de paneles (18 comparaciones
  contra la anterior a 1450/900/390 px y texto seguro), 12 de pantalla moderna
  modelo/fallback y 20 de entrada/pestañas/recarga. La segunda tanda repite
  los 19 paneles con comprobación explícita de sus clases modulares; no se
  suman dos veces. Se bloquea `innerHTML` para verificar nombres/notas como
  texto y se comprueba el destino del rango Clockify. Capturas en
  `tmp/migration/project_detail/generic_panels/` y `generic_timeline/`;
  recursos escritorio e hitos con notas inspeccionados. Ruff/formato, sintaxis
  JS, Django y diff aprobados. Proveedores simulados/red bloqueada, sin consultas
  reales. Auxiliares en `tmp/` sin comitear.
- **Fase 10 parcial.** Siguiente: encabezado/KPIs, gráficas, fuentes y
  acciones genéricas; después casos sin proyecto/cuenta y arranque
  independiente. No retirar script/shim ni activar ACCESS_ENFORCED ni tocar
  Horas por mes. Sin push; temporales/cambios ajenos intactos.

## Bloque anterior: vista de la línea temporal genérica (25/10/2026)

- `generic_timeline_view.js` dibuja barras, estados, hitos adicionales, eje,
  leyenda y mensaje sin hitos con DOM seguro. Los estilos fijos están en
  `project_detail_generic_timeline.css`; solo geometría/color de estado usan
  CSSOM. Reutiliza el modelo existente sin cambiar cálculos ni permisos.
- El renderer transitorio reemplaza un marcador estático por el componente;
  la ruta nueva no ejecuta el constructor HTML anterior del Gantt. El resto
  del Ejecutivo genérico, sus formularios y enriquecimientos siguen anteriores.
  No dar por migrada la pantalla completa ni retirar script/shim.
- La comparación aislada contra `?vista=anterior` conserva contenido,
  dimensiones y estilos, alojando ambas versiones en el mismo ancho original
  y comparando cajas relativas al componente. Los botones genéricos ajenos a
  él aún alteran altura/ancho del contenedor (25/44 px); eso sigue pendiente.
  El test incremental de modelo/fallback desactiva también la vista modular
  al leer la referencia. Se preservan todas sus comprobaciones de la pantalla.
- **45 de navegador aprobadas**: 13 del componente (12 comparaciones en tres
  tamaños, incluidos hitos/cierre/sin hitos, y una de texto seguro), 12 de
  modelo/fallback y 20 de entrada/pestañas/recarga. La prueba de texto bloquea
  `innerHTML` e inserta nombres con etiquetas, sin crear nodos HTML.
  Suite Node **429 aprobadas y tres fallos anteriores** (`cost_sprint_details`,
  `executive_report`, `financial`). Capturas en
  `tmp/migration/project_detail/generic_timeline_view/` y `generic_timeline/`;
  hitos escritorio y cierre móvil inspeccionados. Ruff/formato, sintaxis JS,
  Django y diff aprobados. Proveedores simulados/red bloqueada, sin consultas
  reales. Temporales/cambios ajenos intactos; auxiliares en `tmp/` sin comitear.
- **Fase 10 parcial.** Siguiente: resto de vista/controlador/CSS genéricos,
  fuentes/formularios, casos sin proyecto/cuenta y arranque independiente.
  No activar ACCESS_ENFORCED ni tocar Horas por mes. Sin push.

## Bloque anterior: modelo temporal del Ejecutivo genérico (25/10/2026)

- `generic_timeline_model.js` separa fases repetidas, suspensiones, estados,
  marcadores, resumen, detección de finalización, rango y meses. Reutiliza
  categoría/nombre de hitos ya contrastados. No modifica los datos recibidos.
  El renderer de compatibilidad usa el modelo y conserva su cálculo original
  como fallback; HTML, estilos, eventos y enriquecimientos siguen anteriores.
- Dos Node nuevos comparan 79 combinaciones de datos/fechas/estados/límites
  contra el bloque original y comprueban que no se muta el backend. Suite
  completa: **429 aprobadas y tres fallos anteriores** (`cost_sprint_details`,
  `executive_report`, `financial`).
- **32 de navegador aprobadas**: 12 de modelo/fallback genérico y regresión
  de entrada, pestañas y recarga. Los doce casos usan la misma plantilla
  moderna en 1450/900/390 px; la presentación incremental no cambia.
  **No es validación final contra `?vista=anterior`**: se detectaron diferencias
  previas entre plantillas, por ejemplo botones de 25 frente a 44 px. La vista
  genérica/CSS siguen pendientes y no se marcan migradas. Capturas en
  `tmp/migration/project_detail/generic_timeline/` (`fallback.png`/`model.png`);
  escritorio inspeccionado. Ruff/formato, sintaxis JS, Django y diff aprobados.
- **Fase 10 parcial, estimación orientativa alrededor del 85%**, por alcance
  funcional, no por líneas ni como aceptación. Siguiente: vista/controlador/CSS
  genéricos, sus fuentes/formularios, casos sin proyecto/cuenta y arranque
  independiente. Mantener script/shim. No activar ACCESS_ENFORCED ni tocar
  Horas por mes. Sin proveedores reales ni push; cambios/temporales ajenos
  intactos. El script auxiliar de extracción está en `tmp/` y no se comitea.

## Bloque anterior: contexto/recarga directos del proyecto (25/10/2026)

- `project_entry_runtime.js` compone el contexto de entrada/recarga con
  almacén y renderers AER/IXS directos. Conserva los callbacks de compatibilidad
  para sin proyecto/cuenta, cliente y Ejecutivo genérico, sin modificar ramas.
- La recarga de hitos en Planeación IXS ya usa ese controlador/contexto, sin
  `loadDashboard` ni `projectEntryContext`. Los contextos AER compartidos llegan
  desde su runtime. Se elimina `ixsRuntimeBindings` y el método `connect` IXS;
  solo la vista anterior queda inyectada como renderer desde main.
- **33 pruebas de entrada/sesión/pestañas aprobadas**, incluidas dos nuevas de
  guardar hito→recarga y error→reintento con cinco entradas anteriores bloqueadas.
  Conservan payload/ID/índice exactos y vuelta a Ejecutivo tras recargar IXS.
  Tres Node nuevos verifican estado/secuencia, renderers y fallbacks; el test
  del runtime usa sus servicios actuales. Suite completa **427 aprobadas y
  tres fallos anteriores** (`cost_sprint_details`, `executive_report`, `financial`).
- **72 adicionales de navegador aprobadas; 105 en total**: hitos, shell,
  Cliente/Acciones IXS, runtimes AER/IXS y soporte de recursos. Incluyen
  comparación en tres tamaños, guardados/reintentos y respuestas tardías.
  Capturas en `tmp/migration/project_detail/entry/`, `session/`, `tabs/`,
  `ixs_milestones/`, `shell/` e `ixs_client_actions/`. Inspeccionadas entrada
  IXS escritorio y AER móvil. Ruff/formato, sintaxis JS, Django y diff aprobados.
  Sin proveedores reales ni push; temporales/cambios ajenos intactos.
- **Fase 10 parcial.** Siguiente: vista anterior/Ejecutivo genérico, sin
  proyecto/cuenta y arranque independiente. Mantener todavía script/shim,
  no activar ACCESS_ENFORCED ni tocar Horas por mes.

## Bloque anterior: recomendación IA → RAID modular (25/10/2026)

- El runtime IXS usa `project_ixs_tools.js` para abrir RAID y pasar al modo
  manual. `beeIxsRaidCreator` es el mismo controlador para IA y Gestión RAID;
  el modo manual reutiliza su handler existente. Las entradas RAID anteriores
  ya no se inyectan en `ixsRuntimeBindings`.
- Conserva tipo, texto de la recomendación, guardia por ID y recarga del
  registro tras crear. No cambia modelos, API, permisos ni publicación: solo
  crea al pulsar Crear. No se usan Azure/Claude reales en las pruebas.
- Un Node nuevo comprueba proyecto/guardia/recarga y el test del runtime
  verifica apertura/manual sin callbacks anteriores. Suite completa:
  **424 aprobadas y tres fallos anteriores** (`cost_sprint_details`,
  `executive_report`, `financial`). Las primeras **12 de navegador aprobadas**
  comparan los tres tipos a 1450/900/390 px y bloquean cinco funciones previas.
- **Regresión completa: 108 de navegador aprobadas**, incluidas esas doce:
  IA→RAID, alta RAID, Gestión RAID e IA (vistas/acciones). El test nuevo también
  crea un Issue simulado, conserva la descripción exacta y no usa RPC ni
  funciones anteriores. Una comparación intermitente de Oportunidad pasó al
  repetirla; la prueba espera ahora explícitamente fuentes/pintura y guarda
  JSON de diagnóstico, sin relajar igualdad de contenido, cajas ni estilos.
  Capturas/JSON en `tmp/migration/project_detail/ixs_ai_raid/`; también capturas
  de `ixs_raid_create/`, `ixs_raid/` e `ixs_ai_full/`. Inspeccionados Issue en
  escritorio y Risk móvil. Ruff/formato, sintaxis JS, Django y diff aprobados.
  Sin proveedores reales ni push; temporales/cambios ajenos intactos.
- **Fase 10 parcial.** Siguiente: vista anterior y recarga; compatibilidad
  genérica/sin proyecto y arranque independiente. Mantener script/shim, no
  activar ACCESS_ENFORCED ni tocar Horas por mes.

## Bloque anterior: herramientas compartidas IXS (25/10/2026)

- `project_ixs_tools.js` conecta editores de Planeación y Comunicados con sus
  controladores desde el runtime IXS. Mantiene UID decodificado, tipo inicial,
  estado de Planeación, guardias, listas guardadas y repintado. Comunicados
  conserva ID de Planeación, nombre, familia y fechas sugeridas existentes.
- El runtime deja de recibir estilos/editor/Comunicados desde
  `ixsRuntimeBindings`. Las hojas AER/IXS/IA están enlazadas en la plantilla;
  no llama a los inyectores anteriores. Las entradas anteriores siguen para
  compatibilidad/comparación; no se cambian cálculos, permisos ni API.
- Tres Node nuevos verifican UID especial, guardia, listas y datos de apertura;
  el test del runtime comprueba editor/Comunicados sin callbacks previos.
  Suite completa: **423 aprobadas y tres fallos anteriores**
  (`cost_sprint_details`, `executive_report`, `financial`).
- **94 de navegador aprobadas**: runtime IXS, editores, Comunicados, sesión,
  Planeación e IA (fuentes). Incluyen comparación en tres tamaños, guardados,
  UID exacto, errores/reintentos y respuestas tardías. La prueba nueva bloquea
  siete funciones anteriores, registra vacaciones y abre Comunicados por UI.
  La prueba de sesión conserva orden/estado de IA y verifica los enlaces CSS
  externos en vez de esperar llamadas al inyector retirado del runtime.
  Capturas en `tmp/migration/project_detail/ixs_planning_editor/`, `communique/`,
  `session/`, `ixs_planning_view/` e `ixs_ai_sources/`; editor y Comunicado
  inspeccionados. Ruff/formato, sintaxis JS, Django y diff aprobados.
  Proveedores simulados/red bloqueada; sin consultas ni correos reales.
  Sin push, temporales/cambios ajenos intactos.
- **Fase 10 parcial.** Siguiente: RAID, vista anterior, recarga y arranque.
  Después cerrar compatibilidad genérica/sin proyecto y validar independencia.
  No retirar aún script/shim, activar ACCESS_ENFORCED ni tocar Horas por mes.

## Bloque anterior: coordinación directa AER/T&M (25/10/2026)

- `project_aer_runtime.js` conecta sesión, shell, pestañas, estado, paneles,
  formularios, IA y Comunicados directamente con sus módulos. Conserva la
  pestaña al refrescar, alias minutas→IA y orden de las cinco lecturas IA.
  Los CSS ya están enlazados; no requiere el inyector anterior.
- Cliente/Acciones IXS recibe los contextos AER desde este coordinador,
  sin `projectTabsContext`. Las entradas previas delegan para compatibilidad;
  sus eventos/cargas actuales no ejecutan esas entradas.
- Cuatro Node nuevos verifican estado, refresco, orden, flags de acciones IA,
  familia compartida y datos de Comunicados. Suite completa: **420 aprobadas y
  tres fallos anteriores** (`cost_sprint_details`, `executive_report`, `financial`).
  Las **31 pruebas de entrada/sesión/montaje** están aprobadas. Los dobles de
  shell ahora observan el coordinador actual y conservan sus mismos conteos.
- **147 adicionales de navegador aprobadas; 178 en total**: coordinación,
  shell, IA AER (fuentes y acciones), Cliente/Acciones IXS, formularios de
  Planeación, Recursos y Riesgos. Incluyen comparación con la anterior en
  tres tamaños, guardados/reintentos y respuestas tardías. La prueba nueva
  bloquea quince entradas AER anteriores y verifica IA→refresco→Ejecutivo.
  Capturas en `tmp/migration/project_detail/shell/`, `aer_ai_sources/`,
  `aer_planning_forms/`, `aer_resources/`, `aer_risks/` e `ixs_client_actions/`;
  inspeccionadas las del shell y Recursos móvil. Ruff/formato, sintaxis JS,
  Django y diff aprobados. Sin consultas/correos reales, sin push y sin tocar
  temporales/cambios ajenos. La red de pruebas bloqueó los proveedores;
  los dobles del shell se corrigieron al mover la conexión al módulo nuevo.
- **Fase 10 parcial.** Siguiente: cerrar callbacks IXS de estilos, editores,
  RAID, vista anterior y recarga. Después, compatibilidad genérica/sin proyecto
  y arranque independiente. No rehacer pestañas ni retirar todavía script/shim.
  No activar ACCESS_ENFORCED ni tocar Horas por mes.

## Bloque anterior: coordinación directa IXB/SaaS/RaaS (25/10/2026)

- `project_ixs_runtime.js` conecta controladores y almacén para montaje,
  dispatch, selección/refresco, IA y Cliente/Acciones. Recursos/marcadores usan
  soporte/editor modular. Conserva caché, orden de cargas IA y vuelta a Ejecutivo
  al refrescar. `project_ixs_adapters.paint` presenta IA por su vista modular.
- Las entradas anteriores IXS delegan, pero los eventos/pintura de esta
  coordinación no vuelven a ellas. `ixsRuntimeBindings` todavía inyecta estilos,
  contextos AER compartidos, editores, Comunicados, RAID, vista anterior y recarga.
- **31 de entrada/sesión/montaje aprobadas**. Dobles adaptados de los puentes
  previos a módulos actuales; mantienen comprobaciones de estado/orden/conteos.
  Cuatro Node nuevos de coordinación y pintura: suite **416 aprobadas y tres
  fallos anteriores** (`cost_sprint_details`, `executive_report`, `financial`).
- **108 adicionales de navegador aprobadas** de coordinación directa,
  navegación/refresco, Cliente/Acciones y fuentes/acciones IA: **139 en total**.
  La prueba nueva bloquea quince funciones previas y verifica IA→Ejecutivo y
  actualización por módulos. La observación de paneles IA usa el argumento real
  de la vista, sin depender del alias global anterior. Se mantienen todas las
  comprobaciones de texto seguro, navegación, datos, estado y orden de cargas.
  La red e2e bloquea proveedores; dobles corregidos tras mover las conexiones.
  Ruff/formato, Django y diff aprobados. Capturas en
  `tmp/migration/project_detail/entry/`, `session/`, `tabs/`, `shell/`,
  `ixs_client_actions/`, `ixs_ai_sources/` e `ixs_ai_full/`, inspeccionadas.
  Sin consultas ni correos reales, sin push; temporales/cambios ajenos intactos.
- **Fase 10 parcial.** Siguiente: coordinación AER y conexiones/callbacks que
  faltan, después Ejecutivo genérico/sin proyecto y arranque independiente.
  No rehacer vistas/modelos ni retirar script/shim ni activar ACCESS_ENFORCED
  ni tocar Horas por mes.

## Bloque anterior: adaptadores IXB/SaaS/RaaS de IA e hitos (25/10/2026)

- `project_ixs_adapters.js` compone datos IA desde el almacén con los modelos
  existentes (contexto/snapshot/cambios/capacidad e hitos), sin fórmulas nuevas.
  Carga fuentes/historial/Drive y construye acciones con controladores existentes,
  misma guardia y callback de RAID. No usa `_ixsHitos` anterior en el flujo IA.
- Soporte de Planeación obtiene estado del almacén y abre editor de hitos
  directamente con el módulo migrado, conservando ID/índice/fecha/observación y
  callback de recarga. No pasa por el editor previo en esa ruta.
- Ocho Node nuevos contrastan composición completa con la referencia y prueban
  soporte, tres cargas y acciones/RAID. **24 de navegador aprobadas** de fuentes
  IA y recursos compartidos. Prueba de datos IA ajustada al adaptador: observa
  llamadas y desactiva ambos módulos para comparar contra las fórmulas previas.
- **63 adicionales aprobadas** de acciones IA IXS y Planeación: **87 de
  navegador en total**. Incluyen comparación en tres tamaños, editor real de
  hitos, formularios, cargas parciales/reintentos y respuestas tardías.
  Suite Node **412 aprobadas y tres fallos anteriores** (`cost_sprint_details`,
  `executive_report`, `financial`). Ruff/formato, Django y diff aprobados.
  Capturas en `tmp/migration/project_detail/ixs_ai_sources/`, `ixs_ai_full/`
  e `ixs_planning_view/`, inspeccionadas. Sin API/cálculos nuevos, sin consultas
  ni correos reales; sin push y con cambios/temporales ajenos intactos.
- **Fase 10 parcial.** Siguiente: coordinación directa de pintura/navegación/
  arranque/callbacks, luego compatibilidad genérica/sin proyecto y verificación
  independiente. `ixsIAPintar` aún aporta el enlace de vista modular. No rehacer
  vistas/modelos, retirar script/shim todavía, activar ACCESS_ENFORCED ni tocar
  Horas por mes.

## Bloque anterior: contratos Acciones/Riesgos/IA (25/10/2026)

- `project_feature_contexts.js` separa contratos de Acciones AER/IXS, Riesgos y
  fuentes/presentación/acciones IA AER. Estado y lifecycle parten del almacén;
  callbacks de UI/servicios siguen inyectados desde entradas de compatibilidad.
- Acciones conserva detección de familia, caché/pendientes y repintado solo en
  pestaña correspondiente. IA conserva guardias distintas de fuente/formulario,
  recarga del mismo ID y rechazo de otro estado/proyecto. Guardia IXS común en
  fuentes, historial, Drive y acciones. Ninguna fórmula/API/permiso cambia.
- Siete Node nuevos contrastan contratos y guardias con la referencia.
- **68 de navegador aprobadas** de vistas/formularios/transporte de Acciones
  AER/IXS y fuentes IA AER, con comparación en tres tamaños. Suite Node
  **404 aprobadas y tres fallos anteriores** (`cost_sprint_details`,
  `executive_report`, `financial`). API/cálculos sin cambios.
- **110 adicionales aprobadas** de Riesgos AER, acciones IA AER y fuentes/
  acciones IA IXS: **178 de navegador en total**. Incluyen comparación en tres
  tamaños, formularios, guardados, errores y respuestas tardías. Capturas en
  `tmp/migration/project_detail/actions_forms/`, `aer_risks/`, `aer_ai_sources/`,
  `aer_ai_view/`, `ixs_ai_sources/` e `ixs_ai_full/`, inspeccionadas.
  Django y diff aprobados; formato aplicado a los módulos/pruebas nuevos.
  Proveedores simulados, sin consultas ni correos reales; sin push y con
  cambios/temporales ajenos intactos.
- **Fase 10 parcial.** Próximo: adaptadores IXS residuales y conexiones directas
  de callbacks; luego Ejecutivo genérico/sin proyecto y arranque independiente.
  No repetir vistas/contratos migrados ni retirar script/shim todavía. No activar
  ACCESS_ENFORCED ni tocar Horas por mes.

## Bloque anterior: contratos compartidos del proyecto (25/10/2026)

- `project_contexts.js` crea contratos de entrada, sesión, shell y montaje
  directamente desde el almacén. Separa metadata/secuencia, getters/setters,
  snapshot/guardias por familia, caché y sincronización de estados Azure.
- Conserva pestaña AER al refrescar e invalidación Cliente/Acciones y vuelta
  a Ejecutivo IXS. El UID del editor mantiene su codificación anterior.
  Cinco Node comparan contratos con la referencia y prueban ambas familias.
- Las cuatro funciones anteriores delegan, pero aún suministran callbacks
  de estilo/renderizado/cargas/navegación/paneles. No se retiró el script ni el
  shim; no se marca como independiente el arranque.
- **31 de navegador aprobadas** de entrada/sesión/montaje, con comparación
  visual y recorrido de las 18 pestañas. Sin cambios de API/cálculos.
- **51 adicionales aprobadas** de navegación/refresco, Cliente/Acciones y
  almacén: **82 de navegador en total**. Suite Node **397 aprobadas y tres
  fallos anteriores** (`cost_sprint_details`, `executive_report`, `financial`).
  Django y diff aprobados; módulos/pruebas con formato aplicado. Capturas en
  `tmp/migration/project_detail/entry/`, `session/`, `tabs/`, `shell/` y
  `ixs_client_actions/`, inspeccionadas. Proveedores simulados, sin consultas
  ni correos reales, sin push y con cambios/temporales ajenos intactos.
- **Fase 10 parcial.** Siguiente: contextos específicos Acciones/IA y adaptadores
  IXS, conexiones directas a módulos y compatibilidad genérica/sin proyecto.
  Luego arranque independiente y validación final. No rehacer vistas ni activar
  ACCESS_ENFORCED ni tocar Horas por mes.

## Bloque anterior: avisos y guardado compartidos (25/10/2026)

- `project_feedback.js` separa toast, botón en guardado/restauración tras error,
  selección de principal y cierre normal/ancho. Registro antes del script previo;
  las cinco entradas anteriores delegan. Conserva textos, clases y tiempos.
- Éxito conserva botón deshabilitado/saving; error repone nodos y habilita.
  Mensajes como texto, sin interpretar HTML. Conserva no-op sin botón y cierres
  separados/idempotentes. No copia `_aerModal(html)`; formularios modernos ya
  usan DOM seguro. Sin API/cálculos nuevos.
- **15 nuevas de navegador aprobadas**, incluidas doce comparaciones a
  1450/900/390 px, temporizador de referencia (1800+220 ms), texto seguro y
  contrato de éxito/error/cierre. Capturas en
  `tmp/migration/project_detail/feedback/`.
- **62 de regresión aprobadas** de formularios de Planeación, Recursos y
  acciones IA AER: **77 de navegador en total**. Incluyen recuperación tras
  error, reintento, guardado, avisos y cierres de los formularios reales de
  prueba. Suite Node **392 aprobadas y tres fallos anteriores**
  (`cost_sprint_details`, `executive_report`, `financial`). Ruff/formato, Django
  y diff aprobados; capturas inspeccionadas escritorio/móvil. Proveedores
  simulados, sin consultas ni correos reales. Sin push; temporales ajenos intactos.
- **Fase 10 parcial.** Próximo bloque: contextos/adaptadores restantes y sus
  enlaces directos a módulos; luego compatibilidad genérica/sin proyecto y
  arranque independiente. No rehacer formularios, retirar script/shim todavía,
  cambiar cálculos, activar ACCESS_ENFORCED ni tocar Horas por mes.

## Bloque anterior: estados y contextos de paneles (25/10/2026)

- `project_state.js` añade siete estados de paneles: rango/filtros Planeación,
  registros Clockify y selección Recursos AER; Planeación, Planeación Azure y
  Azure IXS. Son 19 valores en total con los doce centrales. Las declaraciones
  anteriores usan el mismo almacén; comparación mantiene sus valores iniciales.
- `project_panels.js` separa contextos de Planeación/Esfuerzo/Recursos AER:
  snapshot/lifecycle, getters y setters de rangos/filtros/registros/selección.
  Conserva los mismos callbacks inyectados. Sus tres entradas anteriores delegan.
- **Fase 10 parcial.** Siguiente: contextos/adaptadores restantes y utilidades
  comunes de guardado/avisos; luego compatibilidad genérica/sin proyecto y
  arranque sin script anterior/shim. El plan tiene tabla actualizada. No rehacer
  vistas, cambiar cálculos, activar ACCESS_ENFORCED ni tocar Horas por mes.
- Diez Node nuevos contrastan estados/contextos con la referencia; prueba del
  almacén ampliada a 19 declaraciones. Suite completa **392 aprobadas y tres
  fallos anteriores** (`cost_sprint_details`, `executive_report`, `financial`).
- **61 de navegador aprobadas** del almacén y Planeación/Esfuerzo/Recursos AER,
  con comparación visual en 1450/900/390 px, filtros/rangos, selección, editores,
  guardado/borrado y respuestas tardías. Se amplió la comprobación de identidad
  en navegador para los siete estados. API/cálculos sin cambios.
- **69 adicionales aprobadas** de Planeación IXS, tabla Azure y montaje de
  pestañas: **130 de navegador en total**. Incluyen comparación en tres tamaños,
  filtros, comentarios/avances/fechas y respuestas tardías. Capturas en
  `tmp/migration/project_detail/aer_planning_controls/`, `aer_effort/`,
  `aer_resources/`, `ixs_planning_view/` e `ixs_azure_table/`, inspeccionadas.
  Ruff/formato, Django y diff aprobados. Datos/proveedores simulados, sin
  consultas ni correos reales; sin push y sin incluir cambios/temporales ajenos.

## Bloque anterior: estados centrales del proyecto (25/10/2026)

- `project_state.js` posee los doce valores centrales de AER/IXS: dashboards,
  pestañas, IA, Clockify, metadata, secuencia, hitos/ID y caché Cliente/Acciones.
  `main.js` lo registra antes de cargar el script de compatibilidad.
- Once nombres asignables previos se enlazan con accesores temporales al mismo
  almacén; caché mantiene referencia constante. Las declaraciones del script
  anterior usan `var` para esos accesores. Sin módulo mantienen sus valores
  originales, conservando comparación. No se duplican los estados centrales.
- **Fase 10 parcial.** Próximo bloque: estados de paneles AER (rangos/filtros,
  Clockify, selección de Recursos) e IXS (Planeación/Planeación Azure/Azure),
  y sus contextos. Luego compatibilidad genérica/sin proyecto y soporte común.
  El plan incluye inventario con ejemplos/criterios de cierre. No rehacer
  pestañas, sustituir Ejecutivo genérico por IXS, retirar script/shim todavía,
  activar ACCESS_ENFORCED ni tocar Horas por mes.
- **35 de navegador aprobadas** de sesión/entrada/carga, con comparación visual.
  Tres Node nuevos del almacén; suite completa **382 aprobadas y tres fallos
  anteriores** (`cost_sprint_details`, `executive_report`, `financial`).
  Modelo IA adapta solo la extracción de los literales originales para comparar.
- Regresión: **44 aprobadas** de almacén/navegación/pestañas y **69 de acciones
  IA AER/IXS y recursos compartidos**, además de las 35 iniciales: **148
  distintas de navegador aprobadas**. Dos pruebas nuevas verifican en navegador
  que los callbacks usan el mismo almacén en ambas familias.
- La primera corrida detectó desplazamiento distinto en pregunta IA AER a
  390 px: cero diferencias de texto/estilos/dimensiones, solo offset vertical.
  `test_aer_ai_view.compare` fija scroll cero y espera dos frames antes de
  capturar; mantiene todas sus comparaciones. Las 69 de repetición aprobaron.
  Ruff/formato, Django y diff aprobados. Capturas de entrada/sesión/shell/IA
  inspeccionadas. Proveedores simulados, sin consultas ni correos reales;
  cambios/temporales ajenos intactos y sin push.

## Bloque anterior: auxiliares compartidos IXB/SaaS/RaaS (25/10/2026)

- `ixs_support{,_model}.js` separa carga de estados de recursos, edición desde
  la línea de tiempo y etapa/fechas sugeridas para Comunicados. Reutiliza API,
  modelos de fecha/fases/nombres y vistas modulares existentes.
- Estados conservan una consulta en vuelo, caché por proyecto, normalización
  de nombres, false y duplicados. Solo repintan el proyecto actual; una respuesta
  tardía conserva su caché anterior sin pintar el nuevo. Fallos liberan la carga.
- Edición conserva tipo/índice/fecha/observación; sugerencias conservan reglas
  de fases reales/planificadas. `ixsSupportContext` aún enlaza al estado/editor;
  wrappers previos solo delegan. No hay API ni cálculos nuevos.
- **Fase 10 parcial.** Siguiente: compatibilidad genérica/sin proyecto y
  almacenamiento/adaptadores compartidos. El Ejecutivo genérico tiene diseño
  propio: no sustituirlo por IXS. No retirar script/shim, reabrir pestañas ni
  activar ACCESS_ENFORCED ni tocar Horas por mes.
- **40 pruebas de Planeación/Ejecutivo aprobadas**, con comparaciones en tres
  tamaños y apertura del editor de hitos. Once Node prueban modelo contra la
  referencia y caché/errores/respuestas tardías; suite completa **379 aprobadas
  y tres fallos anteriores** (`cost_sprint_details`, `executive_report`,
  `financial`). Proveedores simulados; sin consultas ni correos reales.
- Otras **40 aprobadas** de Esfuerzo/Comunicados, incluidas tres nuevas de lectura
  compartida en Ejecutivo/Planeación/Esfuerzo: **80 de navegador en total**.
  Incluye comparaciones visuales de Comunicados y ventanas de Esfuerzo.
  Capturas en `tmp/migration/project_detail/ixs_planning_view/`,
  `ixs_executive/`, `ixs_effort/` y `communique/`, inspeccionadas en móvil y
  escritorio. Ruff/formato, Django y diff aprobados. Sin push; temporales
  y cambios ajenos intactos.

## Bloque anterior: entrada de proyectos y mensajes de carga

- `project_entry{,_model,_view}.js` monta la plantilla, carga/prepara filtros,
  selecciona el ID de ruta y carga el dashboard AER/IXS por API. Conserva la
  clasificación por servicio/prefijo, prioridad de ruta y enlaces de metadata.
  Su contador descarta respuestas superadas/desconectadas e invalida también
  las de compatibilidad. Carga/error/reintento y `showError` son DOM seguro;
  se conserva el reemplazo global de pantalla de este último.
- Comparación de cajas/estilos/texto en carga/error/reintento/error común.
  El botón Reintentar conserva tamaño/peso anterior con CSS externo.
- **Fase 10 parcial.** `projectEntryContext` sigue con metadata y callbacks;
  almacenamiento y otros adaptadores globales pendientes. Las ramas sin
  proyecto/cuenta y el Ejecutivo genérico para servicio no reconocido siguen
  anteriores: revisarlos antes de retirar script/shim. Después, auxiliares de
  Planeación/soporte. No reabrir las pestañas migradas, activar ACCESS_ENFORCED
  ni tocar Horas por mes.
- **12 nuevas de navegador**, con nueve comparaciones a 1450/900/390 px y
  pruebas de respuesta superada (éxito/error), invalidación de compatibilidad,
  contenedor desconectado y texto seguro. **23 de entrada/sesión y 68 de
  regresión aprobadas**: **103 distintas** en total. Comprobación final: 22
  (12 nuevas + diez de entrada repetidas).
- Once Node de clasificación/metadata/parámetros; suite completa **368
  aprobadas y tres fallos anteriores** (`cost_sprint_details`, `executive_report`,
  `financial`). `legacy_tools.test.cjs` adapta solo extracción de firmas con
  argumento opcional. Ruff/formato, Django y diff aprobados. Capturas en
  `tmp/migration/project_detail/loading/`, inspeccionadas escritorio/móvil.
  API/cálculos sin cambios, proveedores simulados, sin correos ni consultas
  reales. Temporales ajenos intactos; sin push.

## Bloque anterior: inicialización y sesión AER/IXS

- `project_session{,_model,_view}.js` separa selección/reinicio de estados,
  inicializadores AER/IXS, apertura IA IXS y enlace compartido Cliente/Acciones.
  Conserva identidad en el mismo ID, semana local Clockify al cambiar de
  proyecto, caché y orden de cargas IA. Cliente/Acciones conserva el objeto
  AER de IA y solo modifica ID/pendientes; rechaza otra familia/proyecto/pestaña.
- Histórico diferido por API existente, guardia de identidad y actualización
  modular del Gantt Ejecutivo/Planeación. Errores/aviso de backend con DOM seguro
  y la misma presentación. Registro en `main.js` antes del script anterior.
- **Fase 10 parcial.** `projectSessionContext` sigue enlazando los globals;
  el almacenamiento, los adaptadores/entrada común y auxiliares siguen pendientes.
  Continuar por ese bloque y Planeación/soporte (incluido showError). No repetir
  vistas ni retirar script/shim ni activar ACCESS_ENFORCED ni tocar Horas por mes.
- **13 nuevas de navegador**, con nueve comparaciones a 1450/900/390 px y
  cuatro de estado/cache/orden IA. **25 de entrada/Cliente/Acciones aprobadas**.
  Siete Node contrastan las fábricas con las originales y prueban ID/semana/
  diagnóstico; suite completa **357 aprobadas y tres fallos conocidos**
  (`cost_sprint_details`, `executive_report`, `financial`). Ruff/formato, Django
  y diff aprobados. Capturas en `tmp/migration/project_detail/session/`,
  inspeccionadas escritorio/móvil. API y cálculos sin cambios; datos/proveedores
  simulados. Sin consultas/correos reales, sin push; cambios ajenos intactos.
- Regresión adicional: **80 aprobadas** de refresco/navegación, fuentes IA
  AER/IXS, histórico diferido (incluida respuesta tardía) y soporte. Con las
  13 nuevas y las 25 de entrada/transporte: **118 aprobadas**. La última
  corrida tuvo 81 (80 de regresión + la nueva de Cliente/Acciones).

## Bloque anterior: montaje de pestañas AER/IXS

- `project_tabs.js` selecciona los módulos de las ocho/diez pestañas. Mantiene
  contextos AER diferidos, presentador compartido Cliente/Acciones, sincronización
  de pestaña, lifecycle, estados Planeación/Azure y callbacks de edición.
  Ejecutivo y Esfuerzo IXS conservan precarga de estados de recursos.
- `main.js` registra el controlador tras las vistas y antes del script anterior.
  `_aerRenderTab` y `_ixsRenderTab` solo delegan en la ruta nueva; conservan la
  comparación anterior. `projectTabsContext` enlaza con globals/getters/contextos.
- Respaldo AER usa el renderer modular ejecutivo, sin aviso adicional. Respaldo
  IXS usa `project_tabs_view.js`, DOM seguro/eventos externos y mantiene el botón
  de compatibilidad que abre la vista anterior. Se comparan ambos respaldos.
- **Fase 10 parcial.** Siguiente: inicialización de proyectos y estado/cachés,
  incluidos `renderDashboard…`, apertura IA IXS y enlace compartido Cliente/
  Acciones; después auxiliares de Planeación y soporte. No repetir vistas,
  retirar script/shim, activar ACCESS_ENFORCED ni tocar Horas por mes.
- **Ocho pruebas nuevas de navegador aprobadas**, con seis comparaciones de
  respaldos a 1450/900/390 px y recorrido de las 18 pestañas bloqueando el
  renderizado HTML anterior. **25 de entrada/transporte Cliente/Acciones
  aprobadas**. Veintiuna Node de montaje/lifecycle/contextos/estados aprobadas;
  suite completa **350 aprobadas y tres fallos anteriores** (`cost_sprint_details`,
  `executive_report`, `financial`). Ruff/formato, Django y diff aprobados.
- Capturas en `tmp/migration/project_detail/tabs/`. API y cálculos sin cambios;
  no se repitieron pruebas de backend. Proveedores simulados, sin consultas
  ni correos reales. Sin push; cambios/temporales ajenos intactos.
- **63 de regresión aprobadas**: Ejecutivos, IA AER y montaje real de las
  demás pestañas (lecturas/edición), más soporte. Con ocho nuevas y 25 de
  entrada/Cliente/Acciones: **96 de navegador/soporte aprobadas**. Respaldos
  inspeccionados escritorio/móvil.

## Bloque anterior: encabezados, navegación y refresco AER/IXS

- `project_shell{,_model,_view}.js` separa los encabezados y las ocho/diez
  pestañas. DOM seguro/eventos externos, mismos iconos SVG y CSS externo.
  Modelo de estado AER y etapa IXS contrastado contra el anterior; reutiliza
  fases/fechas existentes sin cambiar cálculos ni presentación de etapas.
- Navegación AER conserva alias minutas→IA y orden de cargas (análisis,
  minutas, configuración, resumen, pendientes). Acciones conserva pendientes;
  la navegación IXS monta la pestaña con el dispatch anterior.
- Refresco usa la API v1 existente. AER conserva la pestaña capturada; IXS
  invalida Cliente/Acciones y vuelve a Ejecutivo, como antes. Respuestas
  superadas o de otra carga/familia no reemplazan la pantalla. Presentación
  de error y enlace de regreso conservados.
- **Fase 10 parcial.** Siguiente: entrada/estado y montaje de pestañas, después
  auxiliares de Planeación IXS y soporte compartido (incluido showError).
  Los contextos/dispatch e inicializadores `renderDashboard…` aún enlazan con
  el archivo anterior; este bloque no los da por migrados. No retirar script/
  shim, activar ACCESS_ENFORCED ni modificar Horas por mes.
- **34 pruebas de navegador aprobadas por bloques**, con 24 comparaciones en
  1450/900/390 px de ambas familias (completo/vacío/texto especial/cerrado).
  Todas las pestañas, alias/cargas, refresco, regreso, errores y respuestas
  superadas/de otra familia probados. Diez de entrada también aprobadas.
- Nueve Node del modelo aprobadas; suite completa **329 aprobadas y tres fallos
  anteriores** (`cost_sprint_details`, `executive_report`, `financial`).
  Ruff/formato, Django y diff aprobados. Capturas reproducibles en
  `tmp/migration/project_detail/shell/`. Sin API nueva ni pruebas de backend
  repetidas. Datos/proveedores simulados, sin correos ni consultas reales.
  Temporales/cambios ajenos intactos; sin push.
- **65 de regresión aprobadas**: Ejecutivos AER/IXS, fuentes IA AER,
  Cliente/Acciones IXS y soporte. Con diez de entrada y 34 nuevas:
  **109 de navegador/soporte aprobadas**. Capturas inspeccionadas escritorio/móvil.

## Bloque anterior: IA AER — acciones por API (pestaña completa)

- `project_aer_ai.py` expone ocho POST explícitos para análisis, resumen,
  preguntas, correo, borrador de minuta con/sin Drive, guardado y configuración.
  Se añade GET del prompt por defecto (seis lecturas en total). Firmas,
  funciones/proveedores, tipos y errores originales. Proyecto de la ruta,
  edit_operations o manage_integrations para configuración, alcance total y
  CSRF en escrituras. No activa ACCESS_ENFORCED ni modifica cálculos.
- `aer_ai_actions.js` y `aer_ai_minutes_actions.js` controlan operaciones,
  validaciones, mensajes, reintentos y copiado. `aer_ai_actions_model.js`
  conserva clasificación de preguntas y selección de cinco para resúmenes.
  Se mantienen borradores y contenido editado, coste/caché/persistencia,
  guardado y recarga de minutas, configuración y búsqueda posterior.
- Respuestas de otro proyecto/estado se descartan; otro formulario no recibe
  resultados del anterior. La pregunta nueva escrita durante una consulta
  normal se conserva. Duplicados de análisis en curso se bloquean.
- Los puentes globales solo delegan. La ruta activa no ejecuta renderizadores,
  formularios ni acciones RPC anteriores de IA AER. Lecturas, modelos y vistas
  de los bloques anteriores se conservan.
- **IA AER completa; fase 10 parcial.** Siguiente: encabezados/navegación,
  entrada/estado y auxiliares compartidos del detalle (incluidos los de IXB).
  No retirar script/shim todavía; fase 11 para limpieza y CSP. El manejador
  común showError sigue anterior: algunos errores reemplazan el dashboard.
  Se preservó ese comportamiento; revisar aparte al extraer el soporte común.
- **102 API aprobadas** (57 acciones, 45 lecturas), con permisos/alcance antes
  de fuentes, CSRF, firmas/argumentos y errores públicos. **29 casos de navegador
  aprobados por bloques**, incluidos 18 comparaciones en tres tamaños de
  resultados generados. Flujos con/sin Drive, pregunta/resumen, edición/guardado,
  validación, copia, reintento, cambios de formulario/estado y notas nuevas probados.
- Siete Node del modelo y quince del cliente aprobadas; suite completa **320
  aprobadas y los tres fallos anteriores** (`cost_sprint_details`,
  `executive_report`, `financial`). Ruff/formato, mypy del API, Django y diff
  aprobados. Capturas en `tmp/migration/project_detail/aer_ai_view/actions/`,
  inspeccionadas escritorio/móvil. Datos/proveedores simulados; sin Claude,
  Drive, Sheets reales ni correos. Sin push; cambios ajenos intactos.
- **75 de regresión aprobadas**: fuentes/vista/formularios IA AER, entrada,
  Ejecutivo AER y soporte. Con 29 de acciones: **104 de navegador/soporte**.
  Sumadas las 102 API, **206 aprobadas**. No dar por cerrada la fase 10.

## Bloque anterior: IA AER — presentación y formularios (parcial)

- `aer_ai_presentation_model.js`: datos derivados, extracto de minuta, fecha
  de memoria y formato mínimo de resumen. Contraste Node con las funciones
  anteriores; sin cambios de cálculos ni límites.
- `aer_ai_view.js` monta toda la pestaña, `aer_ai_documents_view.js` separa
  historial/documentos y `aer_ai_dom.js` construye texto/strong/br sin HTML
  interpolado. Los documentos solo permiten enlaces HTTP(S).
- `aer_ai_forms_view.js`: lectura de minuta y resumen, correo, generación de
  minuta, configuración y borrador editable con DOM seguro/eventos externos.
  Mismos IDs/valores/estilos; prompt asignado por propiedad value como antes.
- `aer_ai_presentation.js`: historial, ocultar/mostrar documentos, selección
  máxima de cinco, sugerencias de preguntas y lectura/apertura de formularios.
  Recomendaciones reutilizan Acciones. Ruta activa sin `aerIAVista`, tabla,
  archivos, formato ni formularios HTML anteriores; puentes conservados.
- **IA AER sigue parcial:** acciones de análisis, preguntas, correo, resumen,
  generación/guardado de minutas y configuración siguen anteriores/RPC, al
  igual que sus validaciones y copiado. Siguiente: migrar API/controlador de
  esas acciones con permisos originales. No repetir fuentes/modelos/vistas.
  Después encabezados/navegación/estado/auxiliares compartidos. Fase 10 parcial;
  no retirar script/shim, activar ACCESS_ENFORCED ni tocar Horas por mes.
- **29 casos de navegador aprobados por bloques** (27 comparaciones en tres
  tamaños) y doce de fuentes (nueve comparaciones). Se prueban seis formularios,
  pantalla rica/carga/oculta, límite de selección, teclado/foco, historial,
  contenido seguro y montaje con renderizadores anteriores bloqueados.
- Veinte Node del modelo nuevas aprobadas; suite completa **312 aprobadas y
  los tres fallos anteriores** (`cost_sprint_details`, `executive_report`,
  `financial`). Ruff/formato, Django y diff aprobados. Sin cambios de API;
  no se repitieron sus pruebas. Capturas en
  `tmp/migration/project_detail/aer_ai_view/`, inspeccionadas escritorio/móvil.
- Proveedores/datos simulados, sin consultas reales ni correos. Sin push;
  temporales ajenos intactos.
- **34 de regresión aprobadas** (entrada, Ejecutivo AER y soporte). Con los
  29 casos nuevos y doce de fuentes: **75 casos aprobados**.

## Bloque anterior: IA AER — lecturas, modelo y CSS (parcial)

- `project_aer_ai.py`: cinco GET explícitos en
  `screens/proyectos/<id>/ia-aer/{analisis,resumen,minutas,config,archivos}/`.
  Mismos servicios de `apps.aer.services.ai_functions` y contexto de `ai_rpc`;
  no genera análisis. `view_operations` y alcance total antes de fuentes,
  excepto configuración con `manage_integrations`, como su RPC anterior.
  El contexto comparativo del análisis guardado se recibe como query JSON objeto.
- `aer_ai_sources.js`: cargas/caché de análisis y resumen guardados, minutas,
  configuración y búsqueda Drive. Conserva restauración, avisos y reintentos;
  no pisa análisis recién generado. Descarta respuestas de otro estado/proyecto.
  Refresco del mismo proyecto conserva las cargas sin dejar flags bloqueados.
- `aer_ai_model.js`: contexto y hechos/alertas exactos, contrastados con el
  anterior. Mantener 28 compromisos en el contexto, ocupación sobre toda la
  planeación, umbral 6, filtros de estados/vacaciones y ventana de 30 días.
- `project_detail_aer_ai.css`: CSS principal externo; link `aer-ia-styles-v55`
  evita la reinyección en la ruta nueva. La referencia anterior sigue igual.
- **IA AER sigue parcial:** `aerIAVista`, presentación y formularios aún son
  anteriores. Generación de análisis/preguntas/correo/resumen/minutas y guardado
  de minutas/configuración aún requieren migración a API/controladores/vistas
  seguras. Siguiente: esos bloques de IA, después estructura/estado/auxiliares
  compartidos. Fase 10 parcial; no retirar script/shim ni activar ACCESS_ENFORCED.
- **38 API aprobadas**. Seis Node del modelo, nueve del controlador y catorce
  del cliente aprobadas. Suite completa **292 aprobadas y tres fallos anteriores**
  (`cost_sprint_details`, `executive_report`, `financial`). Nueve comparaciones
  a 1450/900/390 px: vacío, análisis guardado y carpeta Drive configurada.
  Capturas en `tmp/migration/project_detail/aer_ai_sources/`, inspeccionadas
  escritorio/móvil. Ruff/formato, mypy del API nuevo y Django aprobados.
- **46 de navegador/soporte aprobadas**: doce de IA AER, entrada, Ejecutivo AER
  y soporte. Con las 38 API: **84 total**. Cubren caché, reintento, estado
  reemplazado y refresco del mismo proyecto, sin generar IA al entrar. Diff limpio.
- Datos/proveedores simulados, sin Claude/Drive/Sheets reales ni correos enviados.
  Sin push; cambios/temporales ajenos intactos. Horas por mes sin cambios.

## Bloque anterior: Recursos AER

- `aer_resources{,_model,_view}.js` separa indicadores, selección por persona,
  última evaluación, gráfica/historial, distribución, comentarios y editor.
  DOM seguro, SVG y eventos externos; reutiliza estilos AER ya externos. No
  ejecuta renderer, categorías ni formulario HTML anteriores en la ruta nueva.
- Las evaluaciones llegan en el dashboard AER por API existente. Guardado y
  borrado usan POST `screens/proyectos/<id>/evaluaciones-aer/<operacion>/` en
  `project_aer_resources.py`, servicios/firmas originales, proyecto de la ruta,
  edit_operations, alcance total y CSRF antes de consultar fuentes.
- Conserva selección inicial, score/categorías y orden por fechas. La gráfica,
  últimas evaluaciones y comentarios son del proyecto completo: el selector
  solo cambia el resumen individual. Próxima evaluación también sale de todo
  el histórico, incluidas fechas pasadas; no se cambió esa regla.
- Guardar selecciona el recurso enviado; borrar conserva el resumen del servicio.
  Errores mantienen borradores y permiten reintentar. Respuestas de otra carga
  del proyecto se descartan y no cierran un editor abierto posteriormente.
- **Recursos AER completo; fase 10 parcial.** Siguiente: IA AER; después estructura,
  estado/entrada y auxiliares compartidos. No retirar script/shim todavía. Fase
  11 para limpieza/CSP. No activar ACCESS_ENFORCED ni tocar Horas por mes.
- **15 API, 11 de soporte y 18 de navegador aprobadas**. Quince comparaciones
  a 1450/900/390 px de pantalla completa/vacía/seleccionada y alta/edición.
  Permisos, CSRF, argumentos, CRUD, reintento, selección, texto seguro y respuestas
  tardías probados. Capturas reproducibles en
  `tmp/migration/project_detail/aer_resources/`; inspeccionadas escritorio/móvil.
- **46 de regresión aprobadas**: entrada, Ejecutivo AER y Riesgos AER.
  Con las nuevas y soporte, **90 pruebas aprobadas**.
- Diecisiete Node del modelo y trece del cliente aprobadas. Suite completa:
  **276 aprobadas y los tres fallos anteriores** (`cost_sprint_details`,
  `executive_report`, `financial`). Ruff/formato, mypy del API nuevo, Django y
  diff aprobados. Datos/proveedores simulados, sin correos reales. Sin push;
  temporales ajenos intactos.

## Bloque anterior: Riesgos AER

- `aer_risks{,_model,_view}.js` separa modelo, controlador, indicadores, matriz,
  distribución, atención, seguimiento y editor. DOM seguro/eventos externos;
  no ejecuta renderer, tabla de acciones ni ventana HTML anteriores.
- API `project_aer_risks.py`: GET `screens/proyectos/<id>/riesgos-aer/` y POST
  `guardar/`, `eliminar/`, `limpiar-duplicados/`. Mismos servicios y firmas del
  RPC; lectura/edición, alcance total y CSRF antes de consultar fuentes.
  Borrado por UID y recarga posterior conservados.
- Reutiliza el editor modular de Acciones. No añade botón para limpiar: el
  auxiliar global anterior sigue invocable y delega a la API.
- Preserva la clasificación y agrupación anteriores. Hallazgo para revisar
  aparte: riesgos con el mismo título pero responsables/fechas distintos quedan
  agrupados visualmente conservando la primera fila. No se modificó esa regla.
  Tampoco se cambia el repintado de Riesgos tras guardar una acción compartida.
- Las respuestas de otro dashboard se descartan y no cierran un editor abierto
  después de iniciar el guardado. Se conservan borradores ante error y reintento.
- **Riesgos AER completo; fase 10 parcial.** Siguiente: Recursos AER; después IA
  AER y estructura/estado/auxiliares compartidos. Mantener script/shim hasta
  completar el detalle; fase 11 para limpieza/CSP. No activar ACCESS_ENFORCED ni
  modificar Horas por mes.
- **28 API y 23 de navegador aprobadas**. Dieciocho comparaciones a 1450/900/390
  px con datos completos/vacíos/duplicados y formularios alta/edición. Probados
  CRUD, permisos, alcance, CSRF, argumentos, confirmación, reintento, limpieza,
  acción compartida, texto seguro y respuestas tardías. Capturas reproducibles
  en `tmp/migration/project_detail/aer_risks/`; inspección escritorio y móvil.
- **48 de regresión/soporte aprobadas**: entrada, Ejecutivo AER, transporte de
  Acciones y soporte del frontend. **99 total** junto con las anteriores.
- Nueve Node del modelo y doce del cliente aprobadas; suite completa **258
  aprobadas y los tres fallos anteriores** (`cost_sprint_details`,
  `executive_report`, `financial`). Ruff/formato, mypy del API, Django y diff
  aprobados. Datos/proveedores simulados, sin correos reales. Sin push;
  temporales ajenos intactos.

## Bloque anterior: Esfuerzo AER

- API: `GET screens/proyectos/<id>/aer/registros/?desde=...&hasta=...` en
  `project_detail.py`; llama a `dashboard.entries_in_range` con el mismo store y
  proveedor de horas que `getRegistrosClockifyAERRango`. Mantiene validación,
  deduplicación y límite del servicio. `view_operations` y alcance total antes
  de consultar fuentes, como el RPC anterior.
- `aer_effort_model.js`: semana por defecto, filtro de registros, vista previa
  de cinco filas, límites de actividades/recursos y datos de indicadores/gráficas.
  Contraste Node con el original, sin mutar datos ni recalcular horas.
- `aer_effort_view.js`: indicadores, distribución, tendencia, dona, consumo por
  recurso, detalle por fechas y ventana «Ver más» con DOM seguro/eventos externos.
  `aer_effort.js` controla estado/consulta por API. El montaje y los puentes
  globales delegan; no ejecuta `_aerVistaEsfuerzo` ni la ventana HTML anterior.
- El rango solo filtra los registros. Indicadores/tendencia/consumo siguen del
  proyecto completo, igual que antes. El total recibido no reemplaza la cantidad
  de registros disponibles en «Ver más». Se conservan las reglas de presentación.
- Respuestas de otra carga del proyecto o de una consulta anterior no reemplazan
  las más recientes. Filtro/caché y ciclo de vida siguen enlazados a la entrada
  compartida, cuya integración general sigue pendiente.
- Siguiente: Riesgos AER; después Recursos e IA AER, estructura/estado/auxiliares
  compartidos y retiro de dependencia activa del script/shim. Fase 10 parcial.
  Fase 11: limpieza y CSP. No activar ACCESS_ENFORCED ni modificar Horas por mes.
- Capturas reproducibles en `tmp/migration/project_detail/aer_effort/`.
  Inspeccionada la pantalla completa en escritorio y móvil. Datos/proveedores simulados.
- **Esfuerzo AER completo; fase 10 parcial.** Validación: **75 API** (incluyen
  el endpoint nuevo y regresión de lecturas) y **67 de navegador/soporte** (19 de
  Esfuerzo, entrada, Ejecutivo AER, Acciones y soporte), todas aprobadas: 142 total.
  Quince comparaciones a 1450/900/390 px de pantalla completa/vacía/caché y ventana
  con/sin registros. Rango, cinco filas frente a ventana completa, permisos,
  reintento, respuestas fuera de orden/proyecto y texto seguro probados.
- Trece Node del modelo y once del cliente de datos aprobadas; suite completa:
  **248 aprobadas y los tres fallos anteriores** (`cost_sprint_details`,
  `executive_report`, `financial`). Ruff/formato, mypy de project_detail, Django
  y diff aprobados. Sin consultas a proveedores reales ni correos enviados.
  Temporales ajenos intactos; sin push.

## Bloque anterior: controles de Planeación AER (pestaña completa)

- `aer_planning_controls.js` separa búsqueda/filtros, selección e inicialización/
  cambio del rango. `aer_planning_filters_model.js` conserva coincidencias,
  opciones y valores iniciales. `aer_planning_filter_view.js` crea los seis
  menús con DOM seguro/eventos externos y cierre al pulsar fuera.
- El montaje aplica filtros directamente y no llama a los auxiliares anteriores.
  Los puentes globales solo delegan para compatibilidad. El contexto conserva
  getters/setters de rango/filtros y el ciclo de vida del proyecto compartido;
  su integración con el encabezado/estado general sigue pendiente de fase 10.
- Conserva coincidencia exacta de tipo/responsable/estado, búsqueda sin acentos,
  fechas inclusivas, selección de filas visibles y selección oculta anterior.
  Un menú de otro dashboard no aplica filtros al proyecto recién abierto.
- Siguiente: Esfuerzo AER. Después Riesgos, Recursos e IA AER; estructura/estado
  y auxiliares compartidos IXB; retirada de dependencia activa del script/shim.
  Fase 11: limpieza y CSP. No activar ACCESS_ENFORCED ni modificar Horas por mes.
- Capturas de los seis menús a 1450/900/390 px en
  `tmp/migration/project_detail/aer_planning_controls/`. El título vacío del
  bloqueo crítico anterior se conserva como se documentó en el bloque de vista.
- **Planeación AER completa; fase 10 parcial.** Validación: 52 e2e de Planeación
  anteriores, 22 nuevas de controles y 48 de regresión aprobadas (122 total).
  Se incluyen 57 comparaciones de Planeación; 18 de los menús. Se comprueban
  fechas inclusivas, teclado/foco, cierre externo, selección visible/oculta,
  indeterminate, texto seguro y menú de otro dashboard que no cambia el proyecto.
  Los auxiliares anteriores se sustituyen por errores para comprobar la delegación.
- Trece Node nuevas aprobadas contra el original; suite completa **234 aprobadas
  y tres fallos anteriores** (`cost_sprint_details`, `executive_report`, `financial`).
  Ruff/formato, Django y diff aprobados. Sin cambios de backend; no se repitieron
  sus API. Inspeccionados filtro de compromiso en escritorio y estado en móvil.
  Datos/proveedores simulados, sin correos reales. Sin push; temporales ajenos intactos.

## Bloque anterior: vista principal e indicadores de Planeación AER (parcial)

- `aer_planning_model.js`: indicadores, estados/agrupaciones/posiciones del Gantt,
  atención, vacaciones y ocupación. Mismos cálculos y orden que el renderer
  anterior; pruebas Node contra su prefijo original, incluidos rangos invertidos.
- `aer_planning_view.js`, `aer_planning_timeline.js`, `aer_planning_tables.js` y
  auxiliares DOM de la página presentan toda la pestaña con DOM seguro y eventos
  externos. `aer_planning.js.mount()` la conecta a formularios y operaciones API.
  `_aerRenderTab` delega en la ruta activa, sin ejecutar `_aerVistaPlaneacion`.
- Se conserva «Comunicados» en Roadmap y su flujo ya migrado. Estados/cierres y
  marcadores del Gantt reutilizan operaciones API, con los mismos campos.
- **Todavía parcial:** filtros de cabecera/búsqueda, selección y estado del rango
  delegan a auxiliares anteriores. El popup de filtros todavía es anterior.
  Son el siguiente bloque; no retirar script/shim ni marcar la fase 10 completa.
- Hallazgo preservado: la alerta de bloqueo intenta mostrar `x.label`, pero el
  grupo original guarda `dependencia`; su título puede quedar vacío. No se corrigió
  durante esta migración. La fila de dependencia sí conserva su texto original.
- Después: Esfuerzo, Riesgos, Recursos e IA AER; estructura/estado/auxiliares
  compartidos; finalmente limpieza y CSP. Genesis/accesos sigue como despliegue.
- Validación: **52 pruebas de Planeación y 48 de regresión aprobadas** (entrada,
  Ejecutivo AER, Acciones y soporte). Treinta y nueve comparaciones de Planeación
  a 1450/900/390 px: datos completos/vacíos, alertas/vacaciones, rangos invertidos,
  filtros activos y formularios. Probados controles, cierres, guardados, texto/UID
  seguros y montaje con renderizadores anteriores sustituidos por errores.
- Veintiuna Node del modelo aprobadas, incluidas nueve comparaciones de resumen
  y funciones de posición/fechas/estados con el original. Suite completa:
  **221 aprobadas y tres fallos anteriores** (`cost_sprint_details`,
  `executive_report`, `financial`). Ruff/formato, Django y diff aprobados.
  No hay cambios de backend; no se repitieron las API anteriores.
- Capturas en `tmp/migration/project_detail/aer_planning_view/` y las carpetas
  anteriores de formularios/transporte. Inspeccionadas atención en escritorio y
  filtros en móvil. Proveedores simulados; temporales ajenos intactos. Sin push.

## Bloque anterior: formularios y modelo de Planeación AER (parcial)

- `aer_planning_forms.js`: alta/edición de actividades/hitos, vacaciones y carga
  CSV/TSV; DOM seguro/eventos externos, mismos campos, estados, avisos y diseño.
  El controlador `aer_planning.js` los conecta a sus operaciones API existentes.
  No usa `_aerModal` ni los constructores anteriores en la ruta nueva.
- `aer_planning_model.js`: recursos, ocupación actual, consumo/máximo de capacidad,
  parser y fechas de importación, extraídos sin cambiar las reglas. Los wrappers
  compartidos delegan; formularios/guardados lo usan directamente. Las pruebas
  Node comparan contra los originales, incluidos casos límite y datos vacíos.
- Siguiente: modelo de indicadores/fechas del Gantt y vista principal; después
  filtros y selección de tabla. Esos bloques todavía usan `_aerVistaPlaneacion`
  y auxiliares anteriores. **Planeación AER y fase 10 siguen parciales**.
- Después faltan Esfuerzo, Riesgos, Recursos e IA AER; encabezado/navegación/estado
  y auxiliares compartidos IXB; retirar dependencia del script/shim en la ruta
  nueva. Fase 11: limpieza anterior y CSP. Genesis/accesos sigue como despliegue.
- Capturas: `tmp/migration/project_detail/aer_planning_forms/` (sobrecarga,
  capacidad completa, cierre y edición de vacaciones) y `aer_planning_transport/`.
  Inspeccionados el editor con sobreasignación en escritorio y vacaciones en móvil.
  Validación: **40 pruebas de Planeación** y **48 de regresión** (entrada,
  Ejecutivo AER, Acciones y soporte), todas aprobadas; 30 comparaciones de
  Planeación a 1450/900/390 px, incluidas cajas/estilos/texto y valores/disabled.
  Doce Node del modelo y diez del cliente de datos aprobadas; suite completa
  **212 aprobadas y los tres fallos anteriores** (`cost_sprint_details`,
  `executive_report`, `financial`). Ruff/formato, Django y diff aprobados.
  No hay cambios de backend en este bloque; no se repitieron las 49 API anteriores.
  Sin fuentes reales.
  Temporales ajenos intactos; sin push.

## Bloque anterior: operaciones de Planeación AER (parcial)

- `project_aer_planning.py`: ocho POST explícitos de guardar/importar, estado,
  cierre, borrar simple/lote y guardar/borrar vacaciones. Firmas y servicios
  originales de AER; edición, alcance total y CSRF heredados. El ID de la ruta
  prevalece donde el servicio recibe proyecto; borrado simple sigue por UID.
- `sections/aer_planning.js`: controlador de operaciones conectado desde
  `main.js`, `data.js` y los puentes de `proyecto_detalle.js`. Conserva avisos,
  borradores al reintentar, sobreasignación, cierre automático, guardado ligero,
  confirmación física de borrado e importación. Respuestas de otro dashboard
  se descartan; un guardado no cierra un editor abierto después.
- La vista y formularios siguen anteriores a propósito; comparar no significa
  que Planeación esté terminada. También siguen anteriores filtros, selección,
  parser CSV/TSV, presentación de fechas y cálculos/advertencias de capacidad.
  Siguiente extraerlos sin reescribir las reglas, reutilizando esta API/controlador.
- Se conserva el caso original de borrado individual que recarga incluso con
  `{ok:false}` si no hubo error de transporte; no corregirlo dentro de la migración.
- Capturas reproducibles en `tmp/migration/project_detail/aer_planning_transport/`;
  comparación de pantalla completa/vacía y formularios contra `?vista=anterior`.
  Inspeccionada la captura completa de escritorio. Proveedores simulados.
- Validación: **109 aprobadas** entre API, soporte y navegador (incluye 49 API,
  25 e2e de Planeación, regresión de entrada y Acciones). Dieciocho comparaciones
  de pantalla/formularios a 1450/900/390 px. Diez Node del cliente de datos
  aprobadas; suite completa **200 aprobadas y los tres fallos anteriores**
  (`cost_sprint_details`, `executive_report`, `financial`). Ruff/formato, mypy
  del módulo nuevo, Django y diff aprobados. Sin fuentes ni correos reales.
- Después Planeación: Esfuerzo, Riesgos, Recursos e IA AER, más estructura y
  auxiliares compartidos. Fase 10 parcial, fase 11 pendiente. Sin push.

## Bloque anterior: vista y formularios de Acciones AER/IXS

- `actions_view.js` presenta indicadores, atención, responsables, seguimiento
  semanal, las dos tablas, búsqueda y ambos formularios con DOM seguro/eventos
  externos. `actions.js` monta la vista y abre los editores; reutiliza los
  contratos/API del bloque anterior. El puente aporta el dashboard/caché y
  mantiene el fallback para `?vista=anterior`.
- La ruta nueva no usa `_aerVistaAcciones`, `aerIAAccionesPartesVista` ni
  `_aerModal` en esta pestaña. Los formularios también sirven al alta de
  pendientes desde IA AER; el resto de esa pestaña todavía es anterior.
- Se conserva exactamente el funcionamiento previo, incluidos «Filtros» que
  abre el alta, «Ver todas las acciones» que limpia duplicados y «Próxima
  revisión» que edita `fechaReal` en la tabla principal. No corregirlos dentro
  de la migración sin cambiar su alcance.
- Etiquetas accesibles en campos editables/búsqueda/borrado; no se modifica la
  presentación. Las pruebas ejercitan teclado, texto que parece HTML, búsqueda
  sin acentos, errores/reintento y respuestas tardías que no cierran otro editor.
- Capturas: `tmp/migration/project_detail/actions_transport/` y `actions_forms/`.
  Inspeccionadas Acciones IXB en móvil, edición AER en escritorio y pendiente
  IXB en móvil; comparaciones de cajas/estilos y texto contra la anterior.
- Validación final: **184 aprobadas, nueve deseleccionadas** (99 API y 85 e2e
  de Acciones, entrada, carga Cliente/Acciones y navegación AER). Incluye 42
  comparaciones de vista/formularios en AER/IXS a 1450/900/390 px. Las nueve
  excluidas son variantes del Ejecutivo sin cambios en este bloque. Dieciocho
  Node dirigidas aprobadas; suite completa **199 aprobadas y tres fallos
  anteriores** (`cost_sprint_details`, `executive_report`, `financial`).
  Ruff/formato, Django y diff aprobados. Proveedores simulados, sin correos reales.
- Siguiente: Planeación AER; después Esfuerzo, Riesgos, Recursos e IA AER.
  Quedan entrada/estado, encabezados/navegación y auxiliares compartidos de
  Planeación IXB. La fase 10 sigue parcial y fase 11 (limpieza/CSP) pendiente.
  No activar ACCESS_ENFORCED ni retirar shim/archivo anterior. Sin push.

## Revisión posterior a Claude y bloque Acciones AER/IXS (bloque anterior parcial)

- Git actualizado en `main`: se revisaron directamente los commits `06c2444`,
  `66c1095`, `c82b6d0`, `75fa0db` y `e29994f`, rutas API, importaciones en
  `main.js` y delegación activa de `_aerRenderTab`/`_ixsRenderTab`.
  Cliente de ambas familias y Centro de Comunicación IXS sí están conectados
  a módulos nuevos; el resumen anterior de AGENTS/plan estaba desactualizado.
- Comprobación propia de esos avances: **94 e2e** (comparaciones y escrituras),
  **26 API** y **siete Node** aprobadas. Mypy de Cliente/detalle aprobado: los
  seis errores anteriores quedaron corregidos por Claude. No se repitieron
  las 1437 pruebas históricas que él documentó; este alcance es dirigido.
- Nuevo `project_actions.py`: dos GET (acciones y pendientes) y siete POST
  explícitos para guardar, actualizar campo, eliminar, limpiar duplicados y
  guardar/actualizar/eliminar pendientes Beecker/Cliente. Reutiliza las mismas
  tablas de servicios AER/IXS. Lecturas con `view_operations`; escrituras con
  `edit_operations`, alcance total y CSRF. No modifica reglas de los servicios.
  El borrado normal sigue la firma por UID del original, autorizada a portafolio
  completo; los argumentos que incluyen proyecto usan el ID de la ruta.
- `actions_model.js` separa el resumen (prioridad por fecha/estado, responsables,
  cinco semanas) y lo contrasta con el original. `actions.js` ejecuta operaciones
  por API, conserva confirmaciones, borrador/reintento, caché y avisos. Evita que
  un guardado cierre un editor abierto después y descarta respuestas de otro
  dashboard. Los puentes anteriores delegan; el fallback sigue intacto.
- **Acciones NO está completa:** vista, filtro de tabla y construcción de los
  dos formularios siguen en el renderer anterior, con eventos en línea. Siguiente
  separarlos con DOM seguro reutilizando modelo/controlador y API nuevos.
- Regresión del bloque: **152 aprobadas**, incluidas 99 API, 14 e2e de Acciones,
  entrada/soporte y regresión de Cliente/Comunicación. Seis comparaciones de
  Acciones AER/IXS a 1450/900/390 px. Doce Node dirigidas aprobadas; Node completo
  **198 aprobadas y los tres fallos previos** (`cost_sprint_details`,
  `executive_report`, `financial`). Ruff/formato, mypy del módulo nuevo y diff
  aprobados. Proveedores simulados, sin consultas reales ni correos enviados.
- Capturas: `tmp/migration/project_detail/actions_transport/`. El fixture del
  detalle ahora simula la lectura de pendientes por API al navegar a Acciones/IA.
  Revisión final de esa navegación y Acciones: **17 e2e aprobadas** adicionales;
  inspeccionada la captura completa de IXB en escritorio. Django sin incidencias.
- Inventario real: IXB pendiente de vista/formularios de Acciones y estructura
  compartida. AER pendiente de Acciones, Planeación, Esfuerzo, Riesgos, Recursos
  e IA. Planeación IXB ya presenta/edita por módulos; sus auxiliares de estado
  (`ixsEditarHitoTimeline`, `_ixsCargarEstadosRecursos`, `_ixeAuto`) se extraen
  con encabezado/navegación/entrada compartidos. Después limpieza/CSP (fase 11).
  ACCESS_ENFORCED/Genesis es despliegue, no activar. Temporales ajenos intactos.

## Bloque: fase 10, pestaña Cliente (AER/T&M e IXB/SaaS/RaaS) completa

- API v1: `POST screens/proyectos/<id>/cliente/<operacion>/` con
  `contacto-guardar|contacto-eliminar|info-guardar|gobierno-guardar|
  documento-guardar|documento-eliminar` y `servicio` ("aer" | "ixs") en el
  cuerpo. Llama a la misma función que el RPC anterior (`guardar*AER` o
  `ixsGuardar*`), con el proyecto de la ruta; `edit_operations`, alcance total y
  CSRF (`apps/portal/api/project_client.py`).
- Frontend: `sections/client_model.js` (datos derivados, filtros, CSV; contrastado
  en Node con las funciones originales), `client_view.js` (DOM seguro: pestaña,
  contacto, ficha, gobierno y documento) y `client.js` (`window.beeProjectClient`).
  `_aerRenderTab` lo monta para ambas familias y, con `?vista=anterior`, queda el
  renderer anterior. El dato se actualiza en el lugar en `dashboard.cliente`
  (misma caché que usa Cliente/Acciones de IXB).
- Cambio menor: si falla eliminar un contacto, avisa con un aviso en lugar de
  reemplazar toda la pantalla por el error (comportamiento anterior).
- Pruebas: 20 de API, 54 comparaciones elemento por elemento con la anterior
  (AER e IXS × 9 estados — pestaña, filtros, búsqueda y las cuatro ventanas
  nuevas/edición — × 1450/900/390), 14 de guardado/borrado/avisos/CSV/enlaces/
  texto seguro, las 15 de Cliente/Acciones de Chat y 3 de Node. Regresión de
  proyecto, AER y portal: 1437 aprobadas.
- Falta de la fase 10: Acciones (comparte renderer con AER), el resto de pestañas
  AER (Planeación, Esfuerzo, Riesgos, Recursos, IA), integración restante de
  Planeación IXB, encabezados/navegación compartidos y retirar el shim.

## Bloque: fase 10, Comunicación (Centro de Comunicación) IXB/SaaS/RaaS

- API v1: `GET screens/proyectos/comunicados/` y `POST .../comunicados/guardar/`,
  mismos servicios que `beeComListar` y `beeComGuardar` (`bee_com`). La lista es
  del portafolio; la pantalla muestra los comunicados del proyecto abierto y los
  generales. Lectura `view_operations`; guardar `edit_operations` + alcance total
  + CSRF. Los errores de validación del servicio llegan como `{ok:false,error}`.
- Frontend: `sections/bee_com_model.js` (categorías, filtros, orden, puntos
  clave, payload; Node), `bee_com_view.js` (DOM seguro: lista, KPIs, detalle y
  formulario) y `bee_com.js` (`window.beeIxsCommunication`). Estilos externos en
  `project_detail_bee_com.css` (los mismos de la pestaña anterior). Con
  `?vista=anterior` sigue la pestaña anterior.
- Pruebas: 6 de API, 26 de navegador (21 comparaciones con la anterior a
  1450/900/390: lista, por tipo, búsqueda, orden, detalle, formulario nuevo y de
  edición; más API/CSRF, texto seguro, publicar, edición con uid, errores) y 4 de
  Node. Regresión de proyecto + portal: 1263 aprobadas.
- Queda de la fase 10: vistas/filtros/editores de Cliente y Acciones (comparten
  renderer con AER), integración restante de Planeación, encabezados y
  navegación compartidos, pestañas de AER distintas del Ejecutivo y retirar el
  shim.

## Bloque: fase 10, carga de Cliente/Acciones IXB (parcial)

- `sections/ixs_client_actions.js` carga por la API `cliente/` ya existente,
  conserva la caché entre ambas pestañas, mensajes, proyecto ejecutivo de
  IXB/SaaS/RaaS y registros de las hojas IXS. Rechaza respuestas de otro ID y
  descarta respuestas tardías tras nueva carga o salida de pestaña/proyecto.
- El puente `ixsCargarClienteAcciones` conserva estilos y aplica el resultado
  al renderer compartido con AER. **Las vistas, cálculos de presentación,
  filtros/exportaciones y editores compartidos siguen anteriores**: no contar
  Cliente ni Acciones como pestañas completas. Sin nuevos endpoints ni cambios
  de permisos/negocio. Siguiente separar modelo/vista y sus editores.
- **81 pruebas aprobadas**: 15 e2e de Cliente/Acciones, 43 API de lecturas,
  10 entrada, 11 soporte y dos flujos de IA tras incorporar el módulo.
  Incluye 12 comparaciones llena/vacía a 1450/900/390 px, caché entre pestañas,
  error/reintento, ID inválido, texto seguro y respuesta tras abandonar la pestaña.
  Cinco Node nuevas aprobadas (caché, fallos, reintento, carreras y salida).
  Ruff/formato y diff aprobados. Proveedores simulados, sin fuentes reales.
- Capturas en `tmp/migration/project_detail/ixs_client_actions/`; inspeccionada
  Cliente llena de escritorio. IA está completa en el bloque anterior. La fase
  10 sigue parcial; faltan Cliente/Acciones, Comunicación, integración restante
  de Planeación, encabezados/navegación compartidos y pestañas AER pendientes.
  Conservar shim y script anterior. Sin push.

## Bloque: fase 10, pestaña IA IXB/SaaS/RaaS completa

- `ixs_ai_view.js` presenta toda la pestaña con DOM seguro y eventos externos:
  cabecera/indicadores, resumen, atención, recomendaciones, fuentes, preguntas,
  historial, documentos, transcripciones; reutiliza modelo y paneles separados.
- `ixs_ai_controller.js` implementa ventanas y acciones: evidencias, preguntas,
  análisis, memoria, reportes/comunicados editables, minutas manuales/desde
  transcripciones, acción sugerida, conexión/borrado de carpetas y lectura de
  documentos/importación. RAID reutiliza su editor ya migrado.
- Nueve POST explícitos en `project_ai.py` conservan servicios, argumentos y
  permisos RPC: edición, integración para carpetas y lectura para documento;
  todos con alcance total y CSRF. El proyecto lo fija la ruta. `data.js` usa
  el cliente compartido, sin RPC. Mantiene prompts, revisión antes de guardar,
  límites de minutas/archivos/transcripciones y fórmulas originales.
- Ventanas cerradas/proyectos cambiados descartan respuestas tardías. Conserva
  borrador tras error y reintento. La ruta nueva no ejecuta los renderizadores
  ni formularios anteriores de IA; conserva wrappers de estado/entrada/modelo
  y el código anterior para comparar. No retirar el archivo grande ni shim.
- **185 aprobadas**: 106 API (permisos/alcance/CSRF/servicio exacto), 58 e2e IA,
  10 entrada y 11 soporte. Incluye 18 comparaciones de pantalla y 27 de ventanas
  a 1450/900/390 px; flujos de guardado/error, borradores, filtros, cinco
  transcripciones, texto seguro y prueba que bloquea los renderizadores/formularios
  anteriores. Fuentes simuladas, sin IA/Drive/Azure/Gmail reales.
- Node completo: **181 aprobadas y tres fallos previos** (`cost_sprint_details`,
  `executive_report`, `financial`); 17 dirigidas de IA/cliente aprobadas.
  Ruff/formato, Django y diff aprobados. Mypy conserva seis errores previos
  en otros archivos, ninguno nuevo en IA. No es regresión completa del portal.
- Capturas: `tmp/migration/project_detail/ixs_ai_full/` (rica) y
  `ixs_ai_sources/` (completa/vacía/parcial/comparable/incompleta); inspeccionada
  rica de escritorio. **IA completa; fase 10 parcial.** Siguiente Cliente/Acciones
  (comparten renderer con AER), Comunicación e integración/encabezados pendientes.

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

## Ajuste: comunicados en la tarjeta Roadmap y Pendientes de Business Overview (24/10/2026)

- El botón de comunicados ya no está arriba del Ejecutivo AER/T&M: vive en la
  tarjeta "Roadmap de compromisos" de su pestaña Planeación (`✉ Comunicados`,
  solo con el módulo nuevo; `?vista=anterior` no lo muestra). En IXB/SaaS/RaaS el
  botón de "Línea de tiempo — Hitos principales" pasó de "Extensión" a
  "Comunicados" (vista nueva y anterior, para que sigan idénticas). Se eliminó
  `communique_actions.js`.
- El cierre IXB ya llena "Nombre del proyecto" con el nombre del proyecto abierto
  (si el nombre es solo el ID no lo repite; lo escrito se conserva al cambiar de
  tipo).
- **Causa de los "Pendiente"** de Facturación del periodo y Trabajo por entregar:
  el servidor manda los importes Decimal como texto (`"1950326.71"`) y
  `formatCompact`/`formatMoney` exigían número. Ahora aceptan texto numérico
  (`lib/format.js`). Otros importes Decimal en otras pantallas no se auditaron.
- Pruebas: Node (formato), e2e de Business Overview con importes como texto,
  comunicados (AER desde la tarjeta, nombre prellenado).

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
