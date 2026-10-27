# Congelación de comparaciones: avance del 27/10/2026

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
