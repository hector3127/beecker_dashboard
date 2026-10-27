# Congelación de comparaciones: avance del 27/10/2026

## Recursos AER: referencia del diseño actual aprobado

Base `1478793`, posterior a la aclaración del usuario. No se cambia ningún
archivo de aplicación, CSS, plantilla ni cálculos. Se conserva la interfaz
vigente y se reemplazan únicamente comparaciones old→nuevo por referencias
estáticas del diseño actual. No usar el antiguo diseño como objetivo visual.

Quince escenarios en tests/e2e/frozen/aer_resources:

- Vista full/empty/selected, cada una a 1450/900/390 por 1000 px de viewport.
- Editor nuevo y e1, cada uno en los mismos tres tamaños; conserva todos
  los valores de input/select/textarea además del estado visual del modal.

Se mantienen los mismos selectores, texto, orden DOM, estilos computados y
geometría a precisión 0.1 px de las pruebas anteriores. Son 3024 elementos
medidos, más valores de formularios, aproximadamente 1.3 MB de JSON. Se
registra source=approved_current_design, commit base, digest de datos,
viewport, versión de navegador y plataforma. No se afirma identidad de
píxeles, ni se usa un margen de tolerancia nuevo. No regenerar expectativas
automáticamente ante un fallo.

Generador manual: tests/e2e/frozen/gen/aer_resources_capture.py, fuera del
patrón normal test_*.py. Usa las rutas actuales con config.urls, CSP efectiva
y sin carpetas templates/static de referencia. Sólo ese generador escribe
JSON; las pruebas normales únicamente leen/comparan. El helper
frozen/aer_resources_support.py comparte preparación/medición y no importa
modelos de negocio para producir expectativas. Estas referencias son
visuales del diseño actual, no expectativas de cálculos originales.

Las **18 Chrome** del archivo pasan: quince comparaciones más tres pruebas
de funcionamiento preservadas (guardado con error/reintento, eliminación
confirmada/cancelada, selección, texto seguro y respuesta tardía que no
sobrescribe otro editor/proyecto). La lectura y escrituras siguen probadas
por API con dobles locales; no se consulta a proveedores ni se envían correos.
**473 Node** aprobadas; Ruff y formato pasan. No se repiten servidor/mypy:
sólo cambian pruebas/referencias y documentación.

Las quince capturas se reprodujeron byte por byte. Dos controles negativos
con plugin temporal modifican únicamente el DOM del navegador de pruebas:
padding de la vista y valor de input del editor. Ambos fallan precisamente
en assert actual == expected; no se tocó producción ni se guardaron esas
alteraciones como referencias. Los plugins viven en tmp/ y no se comitean. La corrida final de Chrome sin alteraciones
se registra en tmp/current-resources-final.log. También quedan logs ignorados
current-resources-capture/reproduce/node y current-resources-negative-*.

No retirar referencias compartidas todavía. Otros módulos de navegador aún
usan comparaciones antiguas y deben pasar al criterio de diseño actual sin
modificar la aplicación. Fase 11 abierta; sin push.

## Corrección de criterio visual solicitada por el usuario

El usuario aclaró que el diseño vigente es el aprobado y no debe ajustarse
al old. Esta instrucción sustituye el requisito histórico de paridad visual
con la pantalla anterior. No se cambia aplicación ni se revierten rediseños.
Las referencias originales Node siguen siendo útiles para comprobar cálculos
y contratos; no representan una decisión estética.

El generador del piloto AER ahora captura exclusivamente la ruta actual con
config.urls, CSP y sin directorios de referencia. Sus nueve JSON se etiquetan
approved_current_design con base 0dbb3f7, inputs y hashes vigentes. Se mantienen
las mismas variantes, tamaños, mediciones y 13 pruebas, sin bajar precisión.
Se comparan los elementos antes/después de recapturar para identificar si
hubiera cambios: las expectativas antiguas son evidencia histórica, no una
meta a la que modificar el producto. El resto de comparaciones old debe
clasificarse antes de continuar, sin cambios automáticos al frontend.

Validación de este ajuste: nueve capturas actuales aprobadas; los nueve
arrays de elementos coinciden exactamente con los guardados antes de la
corrección de criterio. Trece pruebas Chrome y 473 Node aprobadas; Ruff y
formato pasan. Ningún archivo de apps/ ni frontend/ modificado. Registros
ignorados: tmp/approved-design-{capture,final,node}.log.

Los bloques siguientes describen el criterio histórico de sus respectivas
fechas; no prevalecen sobre esta instrucción. No regenerar baselines ante
fallos sin investigar ni afirmar validación visual de pantallas no revisadas.

## Decimosexto bloque: piloto de navegador, Ejecutivo AER

Base `3c0f9cc`. Se conserva el archivo y sus **13 pruebas**: nueve variantes
visuales y cuatro casos de navegación por teclado/texto seguro. El test de
paridad deja de abrir ?vista=anterior y carga JSON generados exclusivamente
desde esa ruta antes del cambio. No se reduce la comparación: mismo selector,
orden, texto sin espacios, tag, 12 propiedades CSS y cuatro coordenadas con
la precisión original de 0.1 px. Se espera a document.fonts.ready para evitar
capturar una fuente todavía pendiente.

| Variante | 1450 px | 900 px | 390 px |
|---|---|---|---|
| full | 221 elementos | 221 | 221 |
| empty | 175 | 175 | 175 |
| attention | 239 | 239 | 239 |

Son **1905 elementos** en nueve JSON, unos 0.8 MB en el checkout de captura. Cada archivo
registra fuente original, commit base, instante fijo, viewport, Chrome,
plataforma, digest de inputs y hashes de JS/CSS/template originales y fixtures.
Capturado con Chrome 156.0.8078.48 sobre Windows. No se afirma portabilidad
pixel a pixel a otro motor, versión o fuentes; un cambio ambiental debe
investigarse, nunca regenerar expectativas desde la pantalla actual.

El generador temporal explícito es
`tests/e2e/frozen/gen/aer_executive_capture.py`. No coincide con test_*.py y
no entra en la suite normal. Sólo él escribe expectativas. Antes de escribir
comprueba que cargó el script original y que el renderer no es modular.
Comando desde raíz: `.venv/Scripts/python.exe -m pytest
 tests/e2e/frozen/gen/aer_executive_capture.py -q --no-cov --browser chromium
 --browser-channel chrome`. La repetición produjo los nueve JSON idénticos
byte por byte; el runner temporal conserva/restaura los guardados para impedir
que una diferencia de captura sustituya una referencia aprobada.

El helper aer_executive_support conserva inputs y medición, además de la
fixture production_site. Los **13 casos permanentes** usan config.urls,
retiran las carpetas templates/static de tests/reference y aplican CSP real
en las respuestas HTML. Los nueve casos comparan contra los JSON originales,
validan el digest de inputs y comprueban que no hay RPC ni script anterior.
Conservan data-renderer modular, ausencia de onclick y hoja externa única.
El generador no aplica esa fixture: necesita únicamente el original para
producir expectativas. No importa modelos/renderizadores modernos.

Validación antes: 13 Chrome con comparación anterior→actual aprobadas.
Captura: 9 aprobadas; reproducción: 9 aprobadas y archivos idénticos. Final:
**13 Chrome y 473 Node aprobadas**, sin omisiones. Tres controles negativos
ejecutan el mismo test permanente con un plugin temporal que altera su DOM:
texto, padding/geometría y color. Las tres ejecuciones fallan precisamente
en `assert after == before`; la corrida final sin plugin vuelve a pasar.
No se editó código de producción para estos controles. Ruff y formato pasan.
No se repiten servidor/mypy porque sólo cambian tests, JSON y documentación.

Comparación adicional de imágenes (no se añade una tolerancia al test):
seis recortes son idénticos RGB. Los tres de 390 px difieren sólo en las
letras centrales de la dona: 240–365 píxeles, entre 0.034% y 0.043% del recorte.
En full-390, el diagnóstico confirmó HTML, tipografía y rectángulos sin
redondear idénticos, antes y después de scroll; dos capturas consecutivas
por ruta también son estables. Una prueba sólo diagnóstica que fuerza la
misma composición con opacity=0.999999 en ambos textos da imágenes idénticas.
No se aplica ese estilo a producción ni a los tests permanentes y no se
ocultan/máscaran las letras. El flag --disable-lcd-text por sí solo no eliminó
la variación. Se registra la diferencia de pintado, no se afirma que los nueve
PNG normales sean idénticos ni se cambia el diseño para forzarlo.

Evidencia ignorada: `tmp/frozen-browser-pilot-{before,after,final}.log`,
`tmp/frozen-browser-{capture,reproduce}.log`, `tmp/frozen-browser-negative-*.log`,
`tmp/frozen-browser-pilot-node.log`, `tmp/frozen-browser-pixels.json`,
`tmp/frozen-browser-pixel-probe-standard.json`,
`tmp/frozen-browser-composition-pixels.json` y recortes original/current en
`tmp/frozen-browser/aer_executive/<variante>-<ancho>/`. El diagnóstico temporal
se guardó en tmp/frozen-browser-pixel-probe-source.py y no se comitea.

Piloto completado; no equivale a congelar todo navegador. La búsqueda literal
de vista=anterior encuentra también enlaces antiguos que ya sirven frontend:
no usarla como conteo de pantallas pendientes sin clasificar consumidores.
Seguir otros bloques de proyecto (por ejemplo Riesgos/Esfuerzo AER) y después
inventario final antes de retirar originales y generadores. Conservar los
JSON y helpers que usan las pruebas actuales. Fase 11 abierta, sin push.

## Decimoquinto bloque: actualización del corte por la API vigente

Base `6f69346`. `cached_page.test.cjs`, último consumidor Node de archivos
anteriores, conserva sus cuatro pruebas y ahora ejecuta cut.js junto con el
cliente api-client.js real sobre DOM/transporte de prueba. No se simula
apiGet/apiSend: se comprueban los argumentos que llegan a fetch, el token
CSRF, los filtros y los intervalos. `cached_page.gen.mjs` registra las cuatro
salidas originales antes del cambio; cached_page_previous.json se reproduce
exactamente normalizando CRLF/LF. Guarda invariantes y mensajes históricos;
no se afirma que los dos protocolos sean idénticos.

Diferencias vigentes conservadas: el modo HTML antiguo de Comercial ya no es
el controlador de esta pantalla. Business Overview usa API v1 y un botón
persistente. En un corte cargado espera la acción del usuario; al solicitar
actualización aplica el resultado mediante recarga cuando termina. El sondeo
pasivo puede ofrecer un corte parcial mediante «Ver corte preparado» o aplicar
bloques recién disponibles. Esas decisiones ya existían y no se reescriben
para imitar el script anterior. Las pruebas ejercitan corte visible/periodo,
espera, aplicación, reintento, parcial, fuente financiera ausente, error de
red e inicio fallido. Los textos vigentes se conservan.

La auditoría encontró dos diferencias reales que sí impedían conservar la
protección anterior:

- El GET anterior pedía cache:no-store y su respuesta llevaba Cache-Control.
  El cliente y API actuales no lo indicaban. Se añade cache opcional al
  cliente (sin propiedad cache en otras lecturas) y no-store solo al sondeo;
  ExecutiveRefreshView devuelve Cache-Control:no-store para GET/POST.
- fail() detenía el timer, pero el onclick lo rearmaba al terminar check()
  porque applyWhenReady seguía true. Se limpia esa bandera tras fallo;
  el botón queda habilitado y el corte visible se conserva para reintentar.

Antes de corregir fallan la regresión de cache del cliente, tres pruebas del
corte y ocho combinaciones de estado/método del servidor. Después pasan:

- 473 Node completas en UTC y America/Mexico_City; 20 dirigidas cliente/corte.
- 23 servidor dirigidas (test_executive_api y test_executive_refresh), incluidas
  ocho respuestas queued/running/ready/failed por GET/POST sin caché.
- 29 Chrome de Business Overview. Tras reforzar la prueba nueva, revalidación
  separada: 1 Chrome con config.urls, sin carpetas de referencia en templates/
  staticfiles y con CSP efectiva. Comprueba periodo, valores, GET no-store,
  ausencia de intervalos tras fallo y reintento con recarga. Hay solapamiento;
  no sumar ambas ejecuciones como 30 escenarios diferentes.
- Regresión amplia: 1747 aprobadas en tests/portal, tests/core y tests/access
  con --no-cov; incluye las 23 dirigidas. No equivale a ejecutar todos los
  directorios del repositorio. Ningún caso omitido en estas ejecuciones.
- Ocho mutaciones en copias temporales detectadas: caché del sondeo, bandera
  de fallo, filtros del POST, CSRF, aplicación del resultado, bloqueo ante
  fuente financiera ausente, etiqueta parcial y transmisión de cache.
- Ruff/formato, mypy de screens.py y manage.py check con settings de prueba
  aprobados. No se activan accesos ni se cambia la política CSP global.

La primera corrida de navegador tuvo 29 errores de setup porque faltaba el
Chromium distribuido por Playwright; se repitió con el Chrome instalado
(--browser-channel chrome), sin descargar ni instalar navegadores. La nueva
prueba con CSP usa solo mocks y servidor local: no envía correos ni consulta
fuentes reales. La advertencia staticfiles inexistente ya estaba presente.

Evidencia local ignorada: cut-cache-before-node/server, cut-current-before/
after, cut-server-after/regression, cut-browser, cut-browser-chrome,
cut-browser-production, cut-all-{UTC,America-Mexico_City}, cut-mypy,
cut-django-check y cut-*.mutation.log en tmp/. Ningún test Node normal lee
ya tests/reference (41 del motor más cuatro auxiliares convertidos).
No retirar aún originales ni generadores: falta congelación de navegador,
inventario completo de otros consumidores y regresión final de fase 11.
Sin cambios de diseño, cálculos o permisos. Sin push; fase 11 abierta.

## Decimocuarto bloque: carga, navegación y CSS

Base `b33c4f1`. Tres archivos auxiliares dejan de leer tests/reference sin
cambiar producción. Se conservan sus **10 pruebas**. El generador temporal
`portal_auxiliary.gen.mjs` captura del original, antes de reemplazarlo:
10 mensajes, cuatro estados de consultas superpuestas, dos estados de
skeleton, cinco enlaces y restauración/edición de filtros de cuentas,
además del hash y longitud del CSS. JSON reproducible exactamente con
normalización CRLF/LF.

- portal_loading.test.cjs ejecuta el módulo vigente ui/portal-loading.js.
  Conserva isLoadingMessage, contador/fin idempotente y limpieza del skeleton.
  inspect se expone solo en el sandbox de la prueba, sin cambiar exports
  de producción. Pendiente nunca se toma por carga.
- return_navigation.test.cjs ejecuta el listener de ui/return-links.js para
  preservar padre inmediato, cadena anidada, nombre y periodo, excluyendo
  regreso/exteriores. El último caso ahora ejecuta el controlador completo
  all_accounts/main.js y url-state.js actuales sobre una lista vacía. Comprueba
  restauración, pintado inicial y guardado de búsqueda/clasificación/año;
  no pretende validar filas pobladas ni apariencia de la tabla en este bloque.
  El controlador pinta directamente: no emite el input sintético del helper
  anterior, por lo que esa señal interna se reemplaza por comprobar que pintó.
- project_independence conserva la auditoría del grafo activo y compara el
  CSS base contra SHA-256 y longitud capturados del original. Solo se
  normalizan CRLF→LF para admitir distintos checkouts; no se normalizan
  reglas, espacios, comentarios ni BOM. El test anterior pasó antes de
  capturar, verificando que la copia vigente tenía los mismos bytes.

**472 Node completas y 10 dirigidas pasan en UTC y America/Mexico_City**,
ninguna omisión. Seis mutaciones en copias temporales detectadas: añadir
Pendiente a mensajes de carga, quitar idempotencia del cierre, perder periodo,
reescribir regreso, perder clasificación y modificar color CSS. Prettier
JS/diff comprobados. Evidencia ignorada: `tmp/frozen-aux-before.log`,
`tmp/frozen-aux-after.log`, `tmp/frozen-aux-{UTC,America-Mexico_City}.log`,
`tmp/frozen-aux-all-{UTC,America-Mexico_City}.log` y
`tmp/frozen-aux-*.mutation.log`. No se repiten servidor/e2e ni se afirma una
comparación visual nueva. Diseño, datos, fórmulas, CSP y permisos intactos.

Queda **un archivo Node** que lee tests/reference: cached_page.test.cjs,
con sus cuatro pruebas intactas. Su modo HTML y endpoint anterior no están
presentes en el controlador vigente executive/sections/cut.js, que usa
apiGet/apiSend. Antes de reemplazarlo contrastar los casos de actualización,
conservación de filtros/corte visible, reintento, parcial, CSRF, caché y
momento de recarga. No afirmar equivalencia de protocolos ni cambiar el
controlador para que copie el anterior; documentar las diferencias vigentes.
La suite completa sigue incluyendo esas cuatro pruebas del anterior.

Los 41 archivos del motor de proyectos continúan sin leer su script anterior.
También falta navegador. No borrar tests/reference ni generadores aún.
Fase 11 abierta, sin push.

## Decimotercer bloque: arranque, enlaces directos y compatibilidad

Base `884fb69`. Se conservan las **10 pruebas** de los dos últimos archivos
Node que leían el motor de proyectos. Dos generadores temporales originales
`project_compatibility.gen.mjs` y `project_startup.gen.mjs` capturan antes del
cambio 16 transiciones de cuenta/caché/selector y los seis escenarios de las
cuatro pruebas de entrada. Ambos JSON son reproducibles exactamente
normalizando CRLF/LF; no importan implementaciones actuales.

`legacy_tools.test.cjs` ahora ejecuta el controlador project_entry, su modelo,
su vista y el helper el actuales sobre un DOM de prueba. No copia la lógica
del controlador para fabricar resultados. Conserva: entrada vacía sin lecturas,
dos enlaces directos que consultan filtros, TYM sin metadata por endpoint
AER/T&M, montaje de template y dos arranques desde ID en JSON con filtros antes
del dashboard. Las solicitudes se normalizan al tipo de servicio original;
el transporte actual es la API inyectada, sin RPC ni proveedores reales.
El aviso mantiene clase, texto Consultando y ausencia de selectores.

`project_compatibility.test.mjs` ejecuta createProjectCompatibility sobre las
16 trazas de antes/después de refresh, con/sin caché y selector. Las otras
pruebas siguen activas: argumentos/identidad/retorno síncrono de callbacks,
caché leída al momento del cambio, 18 combinaciones de reportes del almacén
y selectores ausentes. La última comprueba el arranque modular real a través
de createEntryRuntime, con un contexto fresco al invocarlo, en vez de ejecutar
la rama modular de la wrapper anterior.

**472 Node completas y 10 dirigidas pasan en UTC y America/Mexico_City**,
sin fallos, cancelaciones u omisiones. Ocho mutaciones en copias temporales
detectadas: envolver callback perdiendo identidad, omitir puerta de cuenta,
ignorar caché AER, perder contexto fresco, quitar TYM del fallback, ignorar
seed JSON, omitir consulta de filtros y cambiar encabezado de carga. Prettier
de JS y diff comprobados. No cambia código de producción, diseño, cálculos,
CSP o permisos; no se repiten servidor/e2e en este bloque de tests Node.

Evidencia ignorada: `tmp/frozen-startup-before.log`,
`tmp/frozen-startup-after.log`, `tmp/frozen-startup-{UTC,America-Mexico_City}.log`,
`tmp/frozen-startup-all-{UTC,America-Mexico_City}.log` y
`tmp/frozen-startup-*.mutation.log`.

**Cero tests Node leen proyecto_detalle.js: los 41 del inventario inicial
están convertidos.** El conteo se refiere a ese motor, no a todas las
referencias del repositorio. Una búsqueda amplia de tests/reference en
los tests Node identifica cuatro archivos auxiliares aún pendientes:

- cached_page.test.cjs: actualización de cortes.
- portal_loading.test.cjs: marcadores de carga.
- return_navigation.test.cjs: navegación de regreso y filtros.
- project_independence.test.mjs: comparación del CSS base original.

Revisar sus equivalentes vigentes antes de reemplazar/retirar expectativas;
no asumir que las pruebas de los archivos anteriores validan la ruta actual.
Además siguen pendientes el piloto y las referencias de navegador. No borrar
originales ni generadores todavía. Fase 11 abierta, sin push.

## Duodécimo bloque: estado, contextos y adaptadores IXB

Base `52fb330`. Cuatro archivos dejan de leer el original conservando sus
**24 pruebas**, sin skips. No se guardan cuerpos de funciones ni código
anterior dentro de los JSON: se capturan valores, claves, trazas e identidad
esperada. Los tests ejecutan el almacén, bindings, contratos y adaptadores
actuales con callbacks instrumentados.

| Archivo | Referencia original guardada / comportamiento vigente probado |
|---|---|
| project_state | 23 defaults y correspondencias nombre/celda; aislamiento, lectura/escritura en ambos sentidos y preservación de cachés calientes |
| project_ixs_adapters | 3 estados completos de contexto/snapshot/cambios/capacidad; 6 integraciones de editor, fuentes/history/Drive, RAID y guardias siguen vivas |
| project_contexts | Entrada, sesión, dos shells y pestañas: claves, referencias, secuencia, caché, callbacks, sincronización Azure y UID escapado |
| project_feature_contexts | 2 familias de Acciones, 4 contratos Riesgos/IA y 5 resultados de guardia IA IXB; conserva sus diferencias al refrescar |

Generadores temporales `project_{state,ixs_adapters,contexts,feature_contexts}`
y helper `project_original_state.mjs` en `frozen/gen/`, solo originales. El
helper evalúa las 23 declaraciones de fallback y sus funciones sobre un
estado enlazado por el harness; no importa createProjectState ni bindProjectState.
La memoria previa del adaptador se captura desde su snapshot original, que
antes se fabricaba con el adaptador actual. Las wrappers de render/dispatch
se identifican observando su delegación original; los tests reconstruyen
callbacks de prueba con esos nombres e identidades, no sus implementaciones.
Cuatro JSON reproducibles exactamente normalizando CRLF/LF. Fechas fijas
para los fixtures de IA/hitos, sin llamadas a proveedores.

Se conserva que Riesgos/Acciones invalidan por reemplazo de dashboard, mientras
las fuentes IA pueden mantener validez ante refresh del mismo ID si conserva
estado; reemplazar el estado IA invalida esas cargas. También se mantienen
las guardias DOM, selección de pestaña, caché compartida, actualización de
partes, retorno de contexto y orden del traspaso RAID.

**472 Node completas y 24 dirigidas pasan en UTC y America/Mexico_City**,
cero fallos/omisiones. Doce mutaciones en copias temporales detectadas:
request inicial, escritura de aliases, preparación de hitos, orden RAID,
incremento de secuencia, identidad de setter, guardia de shell, escape de
UID, guardia de snapshot, guardia de estado IA, caché de partes y pintado en IA.
La mutación de identidad inicialmente no falló: el caso anterior escribía
solo null mediante el setter moderno. Se añadió escribir un objeto y verificar
que conserva exactamente su referencia, comparando con la identidad capturada
del setter original. Con eso se detecta introducir structuredClone.

Prettier de JS/diff aprobados. Evidencia local ignorada:
`tmp/frozen-runtime-before.log`, `tmp/frozen-runtime-after.log`,
`tmp/frozen-runtime-{UTC,America-Mexico_City}.log`,
`tmp/frozen-runtime-all-{UTC,America-Mexico_City}.log` y
`tmp/frozen-runtime-*.mutation.log`. No se editó código de aplicación ni
se repitieron servidor/e2e: cambian pruebas, generadores, JSON y documentación.
Diseño/cálculos/CSP/permisos intactos. Quedan **2 archivos Node** que leen el
original: `legacy_tools.test.cjs` y `project_compatibility.test.mjs` (6 antes,
41 al inicio), 39 convertidos. No retirar aún los originales: siguen esos
consumidores y las comparaciones de navegador. Fase 11 abierta, sin push.

## Undécimo bloque agrupado: modelos genéricos y contratos de paneles/carga

Base `611e820`. Cuatro archivos dejan de ejecutar el original, conservando
las **23 pruebas** del bloque y sus casos. No se guarda código de funciones
como expectativa: se guardan valores, identidad esperada de callbacks/estado,
claves de contratos y trazas del comportamiento original.

| Archivo | Expectativas originales guardadas |
|---|---|
| generic_sources | 9 formatos de horas (undefined etiquetado) y 9 clases de impacto; modelos/lecturas/respuestas tardías se siguen ejecutando |
| generic_executive | 105 cortes por zona a partir de 7 fixtures compartidas y 6 clasificaciones de servicio; casos directos de cierre y dispatch actuales conservados |
| project_panels | 7 valores iniciales y 3 contratos AER completos: callbacks, setters, identidad, selección y guardias de ciclo de vida |
| project_script_loader | 4 combinaciones cuenta/caché, secuencia de llamadas y selección; las dos pruebas concurrentes/reintento del cargador actual se conservan |

Los cuatro generadores temporales de `frozen/gen/` solo ejecutan el original.
JSON reproducibles exactamente normalizando CRLF/LF. Ejecutivo anteriormente
recibía el flag de cierre del modelo actual dentro de la expectativa; ahora
el generador ejecuta la línea de tiempo original para calcular ese flag. Las
105 variantes siguen coincidiendo, en UTC y America/Mexico_City. Los inputs
compartidos se guardan una vez para evitar repetir siete fixtures en cada
combinación. Se conserva precedencia de metadata, límites de palabras de
servicio (xIXB no cuenta), PRD, cierre y ausencia de hitos planificados.

En paneles, los defaults se capturan de los literales originales; el generador
no usa createProjectState para fabricar las expectativas. El test nuevo
comprueba el almacén y contratos actuales, referencias de callbacks, getters/
setters, instancias independientes y respuesta tras cambiar pestaña/proyecto.
El puente de carga antes comprobaba solo la función anterior; ahora ejecuta
createProjectCompatibility.bindings con callbacks explícitos contra las trazas
originales. Conserva orden AER→IXB→riesgos, navegación con/sin cuenta y caché.
No se sustituye la ejecución de callbacks por comparaciones de JSON estáticas.

**472 Node completas y 23 dirigidas pasan en ambas zonas**, sin skips.
Diez mutaciones en copias temporales detectadas: redondeo, clase Alto,
límites de servicio, estado de cierre, guardia de proyecto reemplazado,
identidad del rango, default sinPAT, puerta por cuenta, omisión de caché AER
y marca manual del cargador. Producción intacta. Prettier de JS y diff pasan.
Evidencia ignorada: `tmp/frozen-contract-before.log`,
`tmp/frozen-contract-after.log`, `tmp/frozen-contract-{UTC,America-Mexico_City}.log`,
`tmp/frozen-contract-all-{UTC,America-Mexico_City}.log` y
`tmp/frozen-contract-*.mutation.log`.

Quedan **6 archivos Node** que leen el original: legacy_tools,
project_compatibility, project_contexts, project_feature_contexts,
project_ixs_adapters y project_state (10 antes, 41 al inicio), 35 congelados.
No borrar todavía el original: siguen estas dependencias y las de navegador.
Sin nueva corrida servidor/e2e porque solo cambian tests, JSON, generadores
y documentación. Diseño, cálculos, CSP y permisos intactos. El piloto de
navegador y el cierre completo de fase 11 siguen pendientes. Sin push.

## Décimo bloque agrupado: IA, Esfuerzo, soporte IXB y Planeación AER

Base `6336783`. Cuatro archivos más dejan de leer el script anterior.
Se conservan sus **40 pruebas**, sin eliminar casos. Las pruebas de caché,
recursos en vuelo, respuestas tardías, errores/reintentos y editor de hitos
siguen ejecutando los controladores actuales: no se sustituyen por JSON.
El comportamiento lazy de IA también sigue probado con un callback que lanza
si se solicita un snapshot sin memoria.

| Archivo | Expectativas originales guardadas |
|---|---|
| ixs_ai_model | 4 estados: contexto, snapshot, cambios y capacidad, con fuentes completas/vacías/parciales |
| ixs_support | 6 sugerencias de etapa/fecha; los 5 tests restantes de estados/controladores siguen vivos |
| ixs_effort | 12 totales, 3 variantes de actividades/tendencia/exceso y 4 semanas; la regresión de caché sigue viva |
| aer_planning_model | Por zona: 3 recursos/ocupaciones y sus filas, 7 consultas de capacidad por conjunto, 8 parsers, 18 fechas y 9 modelos completos con funciones derivadas |

Los generadores temporales ixs_ai, ixs_support, ixs_effort y aer_planning en
`tests/frontend/frozen/gen/` solo usan el código original. Los cuatro JSON se
reproducen exactamente normalizando CRLF/LF, sin importar modelos actuales.
Se preservan en IA las sumas originales distintas de contexto (9.35 h) y
snapshot (10.35 h): no se intentó hacerlas iguales. Se conservan horas negativas,
no facturables, IDs duplicados, acentos y recursos inactivos. Soporte fija la
fecha de captura y evaluación, manteniendo sus fixtures de 2010.

Planeación AER guarda sus resultados por UTC y America/Mexico_City. Además
del JSON del modelo, captura estado de compromiso/dependencia y cada posición,
formato y ancho por fila. Undefined y números no finitos se etiquetan para
conservar su significado; no se confunden con null al serializar. Mantiene
limitaciones del parser, año del proyecto, fechas sin reconocer, esfuerzo,
capacidad, vacaciones, rangos invertidos, ocupación y alertas. Los tests
comprueban no mutación de las entradas; los modelos siguen siendo los actuales.

**472 Node completas y 40 dirigidas pasan en ambas zonas**, cero fallos,
cancelaciones u omisiones. Diez mutaciones en copias temporales detectadas:
minutas 3→2, inclusión de recursos inactivos, prioridad de cierre real/plan,
aplicación de estados, redondeo a la baja, desactivar deduplicación, incluir
horas no facturables en exceso, consumir capacidad en hitos, cierre de importación
con avance cero y ancho mínimo del Gantt 0.8→0.9. Ningún archivo de producción
se editó para estas comprobaciones. Prettier de JS y diff comprobados.

Evidencia ignorada: `tmp/frozen-next-before.log`, `tmp/frozen-next-after.log`,
`tmp/frozen-next-{UTC,America-Mexico_City}.log`,
`tmp/frozen-next-all-{UTC,America-Mexico_City}.log` y
`tmp/frozen-next-*.mutation.log`. Sin nueva corrida servidor/navegador porque
el bloque solo cambia pruebas, JSON, generadores y documentación; sin cambios
de diseño, fórmulas, permisos o CSP. Quedan **10 archivos Node** que leen el
original (14 antes, 41 al inicio), 31 congelados. Seguir los modelos genéricos;
los contratos/arranque y el piloto de navegador siguen pendientes. No borrar
las referencias originales todavía. Fase 11 abierta, sin push.

## Noveno bloque agrupado: Riesgos AER, líneas de tiempo y Planeación IXB

Base `98698cd`. Cuatro archivos adicionales dejan de ejecutar el original.
Las 15 pruebas existentes siguen presentes, sin omitir casos ni aserciones
funcionales; se amplía no mutación donde antes no se comprobaba.

| Archivo | Expectativas originales guardadas |
|---|---|
| aer_risks_model | 4 resúmenes, 25 porcentajes por resumen, 4 variantes de deduplicación y conservación del primer responsable/fecha |
| generic_timeline | 63 cortes/estados y 16 límites de suspensión por zona, con estados derivados de cada fila |
| ixs_executive | 32 resúmenes y 10 líneas de tiempo por zona, con tres posiciones de fechas para cada línea no vacía |
| ixs_planning | 4 resúmenes originales y 1 caso semanal nuevo, 4 modelos de indicadores/etapas/vacaciones por zona |

Se conservan agrupación por título de riesgos aunque cambie responsable/fecha,
precedencia de suspensiones/fases repetidas, marcadores y detección de cierre,
umbrales de ritmo, fuentes ausentes, semanas de vacaciones y responsables
normalizados. No se corrige ninguna regla de negocio. Los resultados que son
funciones (porcentaje, estado por fila y posición) se guardan explícitamente,
además del JSON de los demás campos.

Los cuatro generadores temporales en `tests/frontend/frozen/gen/` ejecutan
solo el original, capturado antes del reemplazo. Planeación antes inyectaba
dateMs/milestones/resourceKey actuales en su expectativa: ahora se capturan
sus equivalentes originales. Ejecutivo usa una lista explícita de campos,
sin consultar al modelo actual para decidir qué comprobar. Los cuatro JSON
se reproducen exactamente normalizando CRLF/LF. Los casos temporales se
capturan y ejecutan en UTC y America/Mexico_City, restaurando TZ y Date.

**472 Node completas y 15 dirigidas aprobadas en ambas zonas**, sin skips.
Ocho mutaciones en copias temporales se detectan: peso de impacto, elección
del responsable, ancho de etiquetas, regla de cierre, umbral de ritmo,
posición del Gantt, ventana semanal y cantidad de semanas. La mutación de
ventana semanal inicialmente no falló: los casos antiguos no tenían fechas
a mitad de semana. Se añadió al generador un caso original con fechas del
22 al 31 de octubre (incluye 26 y 29); con él sí detecta pasar de 7 a 1 día.
No se modificó producción para probar errores.

Prettier de JS y diff comprobados; los JSON conservan el formato reproducible
de JSON.stringify. Evidencia local ignorada: `tmp/frozen-group-before.log`,
`tmp/frozen-group-after.log`, `tmp/frozen-group-node.log`,
`tmp/frozen-group-UTC.log`, `tmp/frozen-group-America-Mexico_City.log` y
`tmp/frozen-group-*.mutation.log`. Sin nueva corrida de servidor/navegador:
este bloque solo cambia tests, referencias JSON, generadores y documentación.
Diseño, datos, cálculos, CSP y permisos intactos. Quedan **14 archivos Node**
que leen el original (18 antes, 41 al inicio), 27 congelados. No representa
un porcentaje de toda la fase 11: aún falta el piloto de navegador y los
bloques restantes. Sin push; fase 11 abierta.

## Octavo bloque: resumen Azure IXB/SaaS/RaaS

Base `c1d0308`. `ixs_azure_summary.test.mjs` conserva sus cinco pruebas;
cuatro estados guardan doce campos originales: totales, cerrados, QA,
avance, riesgos, distribución/gradiente, notas, responsables y próximas fechas.
Conserva vacío, allItems vacío, cerrado, orden y límite de ocho elementos,
avance sin recorte y no mutación. La captura se ejecutó antes del reemplazo.

El generador temporal `frozen/gen/ixs_azure_summary.gen.mjs` solo ejecuta
funciones originales. JSON reproducible exactamente con CRLF/LF normalizado
(se mantiene JSON.stringify, sin reformatear arrays con Prettier). El test
carga el clasificador actual de Planeación sin sus imports DOM y el módulo
actual de agrupación; ya no inyecta clasificadores anteriores al modelo nuevo.

**472 Node completas y cinco dirigidas en UTC y America/Mexico_City pasan**,
sin omisiones. Dos mutaciones en copias temporales detectadas: riesgos +1 y
límite de fechas 8→1. No cambia producción, diseño, fórmulas, CSP ni permisos;
sin nueva corrida servidor/e2e para este bloque de tests. Prettier del JS y
diff comprobados; registros ignorados `tmp/frozen-azure-summary-node.log` y
`tmp/ixs_azure_summary.next-mutation.log`. Quedan **18 archivos Node** que
leen el original, 23 congelados; fase 11 abierta, piloto navegador pendiente.
Sin push.

## Séptimo bloque: Recursos IXB/SaaS/RaaS

Base `4c7767a`. Recursos IXB/SaaS/RaaS (`ixs_resources.test.mjs`) compara
contra cuatro resultados completos del original y cuatro casos del editor,
capturados antes de cambiar el test. Conserva normalización, duplicados,
prioridad de asignaciones, horas negativas/inválidas, alertas y no mutación.
El generador temporal `frozen/gen/ixs_resources.gen.mjs` solo ejecuta el original;
el JSON se reproduce exactamente normalizando CRLF/LF.

**472 Node completas aprobadas**, sin omisiones. Tres mutaciones en copias
temporales detectadas: suma de horas +1, activo por defecto invertido y
prioridad de asignaciones eliminada. Prettier y diff comprobados. No cambia
aplicación, diseño, cálculos, CSP o permisos; no se repiten servidor/e2e en
este bloque exclusivamente Node. Evidencia local ignorada:
`tmp/frozen-ixs-resources-node.log` y `tmp/ixs_resources.next-mutation.log`.
Quedan **19 archivos Node** que leen el original y 22 congelados en total.
Piloto de navegador pendiente; fase 11 abierta, sin push.

## Sexto bloque: Recursos, Acciones y presentación IA AER

Base `81b6d12`. Tres archivos adicionales dejan de ejecutar el original:

| Archivo | Salidas originales guardadas |
|---|---|
| aer_resources_model | 16 resúmenes completos, 14 límites de categoría/clase y 7 fechas en dos zonas |
| actions_model | 17 triples de normalización/fecha/color y 3 resúmenes completos |
| aer_ai_presentation_model | 5 extractos de minuta, 5 timestamps, 6 textos escapados y 8 presentaciones |

Se conservan selección/fallback de recursos, fechas mixtas/duplicadas,
gráfica global de últimas cinco evaluaciones, métricas por recurso y límites
de categoría. Acciones mantiene prioridades, responsables, semanas, vencidas,
detenidas y ausencia de fechas. IA mantiene memoria, recomendaciones,
extractos, saltos de línea, escape HTML y consumo de 0/90/110/250%.
Los tests siguen ejecutando los modelos actuales y comprueban no mutación.

Generadores temporales aer_resources, actions y aer_ai_presentation en
frozen/gen. No importan modelos actuales. La presentación anterior antes
recibía facts del modelo nuevo en su harness; el generador ahora ejecuta
aerIAContexto/aerIAHechos originales con el mismo instante fijo, para evitar
que el modelo comprobado genere parte de su propia expectativa. Las
presentaciones siguen coincidiendo. Los tres JSON se reproducen exactamente
normalizando CRLF/LF. Los casos undefined de categoría se guardan con tipo
explícito y Date.parse se comprueba en UTC y America/Mexico_City.

**472 Node completas y 41 dirigidas aprobadas**, sin omisiones; las 41 pasan
en ambas zonas horarias. Cinco mutaciones en copias temporales detectadas:
historial de 5→4, umbral 90→91, vencidas +1, escape HTML eliminado y mínimo
del indicador 0→1. Prettier/diff comprobados. No cambia aplicación, diseño,
cálculos, CSP ni permisos; sin nueva corrida servidor/e2e por tests Node.
Registros ignorados: `tmp/frozen-resources-actions-*.log` y
`tmp/*.next-mutation.log`.

Quedan **20 archivos Node** que leen el original (23 antes, 41 al comenzar),
veintiún archivos congelados en total. Piloto de navegador pendiente; no
retirar aún referencias ni servicios compartidos. Fase 11 abierta, sin push.

## Quinto bloque: encabezado, gráficas y tabla Azure

Base `15f619d`. Se congelan tres archivos adicionales:

| Archivo | Salidas originales guardadas |
|---|---|
| project_shell_model | 8 etapas y 11 clasificaciones de estado AER |
| generic_charts | Paleta original Beecker, 5 geometrías/etiquetas SVG y anchos de dos renderers de barras |
| ixs_azure_table | 8 filtros, 3 listas de opciones y 8 títulos/requerimientos |

Se mantienen los escenarios de vacío, cierre, suspensión, fase activa,
primer día, fase futura, última fase y fechas inválidas. Las gráficas siguen
comprobando ceros, negativos, fracciones, redondeo, filas ocultas que fijan
la escala, orden de recursos/roles, colores y no mutación. Azure conserva
selectores exactos, búsquedas combinadas, espacios/acentos, parsing de códigos
y los datos originales de las cuatro filas.

Generadores explícitos en frozen/gen: project_shell, generic_charts e
ixs_azure_table. No importan modelos actuales; capturan funciones del original
y, en gráficas, extraen geometría y anchos del HTML original. La paleta se
extrae de PALETA_BEECKER, no del modelo comprobado. Tres JSON reproducibles
normalizando CRLF/LF, sin guardar ni ejecutar el renderer anterior en tests.

**472 Node completas aprobadas** y **14 dirigidas aprobadas tanto en UTC
como en America/Mexico_City**, sin omisiones. Cuatro mutaciones en copias
temporales se detectan: Cerrado→Abierto, radio 77→78, escala de barras 100→90
y búsqueda alterada. No se modifica la aplicación. Prettier/diff comprobados;
sin nueva corrida de servidor/e2e por este bloque exclusivo de pruebas Node.
Registros ignorados: `tmp/frozen-shell-charts-*.log` y
`tmp/*.next-mutation.log`.

Al cierre del quinto bloque quedaban **23 archivos Node** que leían directamente el script anterior
(26 antes, 41 al comenzar). Dieciocho archivos congelados en total. El piloto
de navegador sigue pendiente y las referencias/servicios aún no se retiran.
Fase 11 abierta; sin push ni cambios de diseño/cálculos/CSP/permisos.

## Cuarto bloque: contexto IA, esfuerzo AER y severidad RAID

Base `1f0dbef`. Tres archivos dejan de leer/ejecutar el script original:

| Archivo | Resultados del original conservados |
|---|---|
| aer_ai_model | 6 contextos y hechos completos: vacío, fixture y sobrecarga/truncado, con/sin acciones de partes |
| aer_effort_model | 12 resúmenes y estados resultantes: vacío/fixture/truncado × cuatro estados de rango/registros |
| raid_model | 13 pares severidad/nivel, 5 estados de cierre y 3 filas normalizadas |

Los JSON incluyen entradas y resultados completos; no solo cifras escogidas.
Se conserva la no mutación de dashboards y estados, límites de 28 compromisos,
8 tareas/10 recursos y 5 registros de vista previa, vacaciones, estados de
acciones y valores pendientes. Las pruebas de semana lunes→domingo, fechas
elegidas, salud/matriz/etapas, filtros y enlaces seguros permanecen intactas.
Undefined se codifica explícitamente donde formaba parte de las entradas RAID.

Generadores temporales originales e independientes de los modelos actuales:
`aer_ai_context.gen.mjs`, `aer_effort.gen.mjs` y `raid_severity.gen.mjs` en
frozen/gen. Los tres JSON se reproducen exactamente normalizando CRLF/LF.
Contexto/hechos y esfuerzo capturan las funciones originales con el mismo
instante fijo de sus pruebas previas (2026-10-23T18:00:00Z).

**472 Node completas aprobadas**, sin omisiones. Las **22 dirigidas** pasan
tanto en UTC como en America/Mexico_City, restaurando la variable TZ después
de las comprobaciones. Cuatro alteraciones en copias temporales se detectaron:
contexto 28→27, alerta de esfuerzo >6→>100, preview 5→4 y CLOSED dejado de
reconocer. Prettier y diff de espacios comprobados. No cambia aplicación,
diseño, cálculo, seguridad ni permisos; sin nueva corrida servidor/e2e por
este bloque de pruebas Node. Logs ignorados: `tmp/frozen-context-effort-*.log`
y `tmp/*.next-mutation.log`.

Al cierre del cuarto bloque quedaban **26 archivos Node** que leían directamente el original (29 antes del
bloque, 41 al empezar). Quince archivos congelados en total. Piloto de
navegador pendiente; no retirar aún referencias/generadores ni servicios.
Fase 11 abierta, sin push.

## Tercer bloque: RAID, Azure, paneles y rango Clockify

Base `5814968`. Cuatro archivos adicionales dejan de ejecutar la referencia:

| Archivo | Salidas conservadas del original |
|---|---|
| raid_create_model | 6 formatos de líneas de plan, viñetas y saltos de línea |
| ixs_azure_groups | 13 estados, 5 rutas de iteración y 4 agrupaciones completas |
| generic_panels | 8 clases de estado y 9 fechas en dos zonas horarias |
| project_clockify_range | 3 textos de rango en dos zonas horarias |

Se conservan los demás casos: validación/publicación RAID, sugerencias/padre,
búsqueda sin normalizar acentos en Azure, orden y no mutación de agrupaciones,
totales/redondeo/observaciones de paneles, errores/rango sin ID, respuestas
tardías y reemplazo de nodos Clockify. Los valores undefined siguen explícitos
en los JSON; no se convierten a null ni a una cadena accidentalmente.

Los formatos de fecha del original dependen de la zona local. Se capturan en
UTC y America/Mexico_City; las pruebas se ejecutan en ambas y restauran TZ
con finally. No cambia el formato ni la zona de la aplicación. Esta ampliación
evita expectativas que solo funcionen en el equipo que generó el archivo.

Generador temporal `frozen/gen/raid_azure_panels.gen.mjs`, ejecutado solo
expresamente, sin importar modelos actuales. Cuatro JSON reproducibles desde
el original normalizando CRLF/LF. **472 Node completas y 14 dirigidas pasan**,
sin omisiones. Cinco mutaciones en copias temporales se detectaron: viñeta
RAID, ACTIVE→other en Azure, badge de riesgo, locale de fecha y texto de rango.
No se alteraron fuentes de aplicación. Prettier y diff de espacios comprobados.
Registros ignorados en `tmp/frozen-raid-azure-node.log` y
`tmp/*.next-mutation.log`; no se repite servidor/e2e por cambios solo de tests.

Al cierre del tercer bloque quedaban **29 archivos Node** que leían directamente proyecto_detalle.js
(33 antes de este bloque, 41 al empezar). Doce archivos congelados en total;
no es un porcentaje de fase. Continúan pendientes el piloto de navegador y
los modelos más complejos. No borrar todavía referencias ni servicios. Sin push.

## Segundo bloque: contactos, entrada, avance y sesión

Base `7d59edf`. Cuatro archivos adicionales dejan de leer el original:

| Archivo | Salidas congeladas del original |
|---|---|
| client_model | 18 resultados de nivel, iniciales, CSV y normalización |
| project_entry_model | 9 servicios × 4 IDs: 36 clasificaciones de familia |
| ixs_work_items | 8 valores de desarrollo × QA sí/no: 16 avances |
| project_session_model | Los dos estados iniciales completos de IA AER/IXS |

Las otras comprobaciones existentes permanecen: tarjetas/filtros/CSV/enlaces
de Cliente, prioridad del ID de ruta, identidad y duplicados de metadata,
referencias independientes de los objetos de sesión, cambio de proyecto,
caché y fechas de Clockify. No se sustituye la implementación por el JSON:
los tests siguen ejecutando los modelos actuales. Work Items conserva su
harness VM del módulo actual, porque importa DOM; ya no ejecuta el anterior.

Generador temporal `frozen/gen/entry_client_workitems.gen.mjs`, sin importar
modelos actuales: extrae las funciones/literales del original y captura sus
resultados. Los cuatro JSON se reproducen exactamente normalizando CRLF/LF.
Entradas incluyen acentos, comillas/CSV, valores vacíos, null, servicios
desconocidos, normalización de IXB y números inválidos/negativos/excedidos.

Validación del segundo bloque: **472 Node completas y 22 dirigidas aprobadas**,
sin omisiones. Cuatro mutaciones sobre copias temporales se detectaron con
AssertionError: iniciales en minúsculas, familia AER desviada a executive,
peso de desarrollo 0.8→0.7 y resumenConsultado inicialmente true. Los modelos
de aplicación nunca se modificaron; sus pruebas normales siguen pasando.
Prettier y diff de espacios comprobados. No se repite servidor/navegador por
un bloque exclusivo de pruebas Node. Registros ignorados:
`tmp/frozen-entry-client-node.log`, `tmp/*.next-mutation.log`.

Al cierre del segundo bloque quedaban **33 archivos de pruebas Node** que leían directamente el script
anterior (37 antes de este bloque, 41 al empezar). Ocho archivos congelados
en total. El piloto de navegador sigue pendiente; no borrar la referencia,
sus generadores o servicios compartidos todavía usados. Sin push.

## Primer bloque integrado

Base main: `1c37925`. Se revisó el piloto de Claude `4103ed6` y se integró
mediante cherry-pick en `2e580ec`, sin cambiar de rama ni modificar su rama
local `congelar-referencias`. Solo incorpora test, resultados y generador de
`aer_executive`; no modifica código de aplicación.

Se continúa por tres casos pequeños, obteniendo esperados del script
original de tests/reference antes de adaptar sus pruebas:

| Archivo de prueba | Referencia conservada |
|---|---|
| aer_executive | 27 variantes de presentación y formatos/dimensiones del piloto |
| aer_ai_actions_model | 6 preguntas y 3 payloads; acentos, resumen y límite de cinco documentos |
| aer_planning_filters | 3 filas × 12 filtros y 4 rangos iniciales; fechas vacías/invertidas, tipo, acentos y responsable |
| generic_header | 9 geometrías/etiquetas SVG; negativos, exceso, fracción, texto numérico, null, undefined y NaN |

Los resultados están en `tests/frontend/frozen/*.json`. Undefined y NaN se
codifican con un tipo explícito y se restauran al probar; no se confunden con
null. Los demás tests del encabezado mantienen sus expectativas anteriores.
Se conservan las 26 pruebas de estos cuatro archivos y se agregan controles
de número de escenarios y de no mutación de entradas donde corresponde.

Los generadores en `frozen/gen/` son temporales, se ejecutan expresamente y
no forman parte de `node --test tests/frontend/*.test.*`. El generador de los
tres casos nuevos no importa modelos actuales; ejecuta solo funciones del
original. El piloto usa claves del modelo para capturar el renderer original,
como en el trabajo de Claude. Sus cuatro JSON se reprodujeron exactamente
normalizando finales de línea Windows (CRLF/LF); todos sus valores coinciden.
No regenerar expectativas desde la implementación actual para aceptar cambios.

## Validación

- **472 Node aprobadas**, sin fallos ni omisiones, tras los cambios:
  `node --test tests/frontend/*.test.*`.
- **26 dirigidas aprobadas** en los cuatro archivos.
- Cuatro pruebas negativas sobre copias temporales de los modelos, sin
  modificar fuentes de aplicación: cambio del formato de horas, máximo de
  archivos 5→6, ignorar tipo de actividad y redondeo round→floor. Las cuatro
  provocaron AssertionError en las mismas pruebas congeladas.
- JSON reproducibles con los generadores originales (normalizando CRLF/LF). Formato
  Prettier de archivos nuevos/modificados y diff de espacios comprobados.

Registros locales ignorados en `tmp/frozen-small-node.log` y
`tmp/*.mutation.log`; herramientas de comprobación en tmp. No se cambiaron
fuentes de negocio, fórmulas, HTML/CSS, transporte, CSP ni permisos. No se
repitió servidor/navegador por este bloque exclusivo de pruebas Node; la
auditoría de a370589 sigue siendo evidencia separada, no una nueva corrida.
La comprobación inicial byte a byte del piloto señaló únicamente su final
de línea CRLF frente a LF (un byte); se confirmó igualdad de todos los valores
JSON y se repitió normalizando ese final, sin modificar las expectativas.

## Qué sigue

Al cierre del primer bloque quedaban **37 archivos de pruebas Node** que leían directamente
proyecto_detalle.js (41 al comenzar). Esto cuenta archivos, no escenarios,
porcentaje de fase ni estimación de tiempo. Continuar por modelos simples,
después intermedios/complejos. El piloto de congelación de navegador sigue
pendiente; las referencias y sus servicios no se retiran en este bloque.

Fase 11 abierta. Sin push; se conservan cambios ajenos y la rama del piloto.
