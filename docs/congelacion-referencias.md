# Congelación de comparaciones: avance del 27/10/2026

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

Quedan **33 archivos de pruebas Node** que leen directamente el script
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
