# Inventario de Summary — primer bloque

**Actualización de campos EVA, 28/10:** Burn/ETC/desviación/avance, conteos
por etapa y riesgos se extraen y guardan en el inventario. Ya no son columnas
vacías por diseño: se muestran valores verificables y pendientes según
disponibilidad/fecha. Reglas, evidencias y mediciones actuales en
[inventario-eva-metricas.md](inventario-eva-metricas.md), que sustituye las
notas históricas de esta página sobre esos campos aún no extraídos.

## Encabezado inverso SPRINT #1 CR — 28/10

AIN.002 usaba SPRINT #1 CR, que quedaba como línea no reconocida en BASE,
separando la metadata de Lea Dayana Julian Figueroa de las iteraciones CR.
El parser reconoce también sprint/sprnt antes de CR, con número opcional.
Conserva identidad compuesta CR_S1/CR2_S1 y no colapsa S2. El inventario
aplica después la regla autorizada de ignorar S1 en el encabezado CR.

Verificación real AIN.002_CR al 26/02/2026: Lea Dayana Julian Figueroa,
RaaS, Order Entry, Budget 88 y Deployment. Reprocesados 450 proyectos/685
bloques en 1.048 s, sin red y conservando fecha original de fuente.
103 servidor (Azure, inventario/iteraciones/resumen y EVA nativo) aprobadas;
Ruff/mypy aprobados. Sin cambios de interfaz ni nueva corrida de navegador,
sin modificar cortes publicados ni hacer push.

## Primer change request CR1 / CR — 28/10

MCC.016 tenía datos de Summary bajo CR1 y etapas bajo CR. Ahora se relaciona
el único candidato CR1 con CR solo si ambos extremos de fechas coinciden,
no hay candidato Summary CR y no existe iteración CR1. Nunca se une CR2 con
CR. El campo summary_scope conserva CR1 y scope_link_evidence documenta la
correspondencia. Fechas inválidas/no coincidentes siguen sin relacionarse.
Esto amplía la relación estricta anterior sin modificar el parser compartido.

Reproceso local: 450 proyectos, 685 bloques, 1.161 s, fuente original
conservada. Verificado MCC.016_CR al 29/01/2026: Jose Patricio Ochoa Garza,
IxB, Altas Empleados CR, Budget 125, Deployment. 18 servidor de inventario,
iteraciones/resumen aprobadas; incluye alias CR1/CR con fechas coincidentes
y rechazo con fin diferente. Ruff/mypy aprobados; sin cambios de interfaz
ni nueva corrida de navegador. Sin extracción externa ni push.

## Corrección de encabezados CR — 28/10

Instrucción posterior explícita del usuario: CHANGE REQUEST 1 / SPRNT 1
se identifica como CR1; CHANGE REQUEST 2 / SPRNT 1 como CR2. Se admite
también SPRINT 1. Esta regla sustituye el requisito de igualdad literal
CR2_S1/CR2 para el inventario. No elimina S2 ni une CR1 con CR sin número.
El original sigue guardado en Summary y summary_scope; la identidad visible
y la relación de iteraciones usan CR1/CR2. Otros campos conflictivos siguen
pendientes. No se cambian el parser compartido ni los cortes EVA/KPI.

La fila vacía AMK.012_CR2 se debía a que el Summary se guardó en CR2_S1
y las fechas en una fila exclusiva de iteraciones CR2. Corregido: al corte
29/01/2026 muestra Alberto Carlos Rodriguez Veloz, RaaS, Corrección de
asistencia, Budget 90 y Deployment.

Comando --from-local permite reprocesar el último inventario con su evidencia
guardada, sin peticiones externas y conservando source_observed_at. Se guarda
una nueva observación derivada; no se modifica el original. Último reproceso:
450 proyectos, 694 bloques, 0.828 s. No equivale a una extracción nueva.
16 servidor dirigidas aprobadas, incluidas variantes CR1/CR2 y replay con
proveedor bloqueado; Ruff/mypy aprobados. Sin push.

## Resumen por Delivery Manager — 28/10

Tabla adicional antes del detalle con Service (IXB, PoC, RaaS, RaaS+, SaaS)
y Status (Sus, Dis, Dev, Dep), totales por DM y total general. Cuenta una vez
cada fila visible (proyecto/sprint/CR), sobre el mismo corte/búsqueda.
Servicios adicionales y Pendiente se muestran cuando existen, sin descartar
filas. Los DM ausentes quedan como Sin DM confirmado. Status usa la misma
etapa por calendario que el detalle; no se deducen suspensiones de fechas.

Consulta local real al 30/04/2026: 17 bloques, seis DM, suma de servicios y
etapas 17. Pruebas: 13 servidor de inventario/iteraciones/resumen y tres
Chrome con rutas reales/CSP a 390/900/1450; cambio de fecha actualiza ambos
totales a uno/cero en el fixture. Ruff/mypy aprobados. Capturas en
tmp/summary-inventory. Sin extracción adicional, sin push.

## Columnas EVA y corte por rango — 28/10

Por instrucción del usuario se retiran de la tabla las columnas técnicas,
fechas de Summary, validaciones y desplegables de etapas. Se muestran solo
los campos EVA, incluidos conteos por etapa, horas y riesgos aún pendientes
de extracción. Los datos de auditoría siguen guardados en la base.

Formulario GET con corte por defecto timezone.localdate y buscador conjunto.
Solo incluye bloques con inicio y fin de iteraciones válidos que cumplan
inicio ≤ corte ≤ fin. No usa fechas Summary como sustituto. Estatus se
recalcula en cada lectura con esa fecha, no la fecha de extracción.
La consulta es local y filtra calendario actual guardado; no reconstruye
los estados reales históricos ni modifica EVA/KPI activos.

Verificación local real: AMK.004_CR al 28/10/2026 muestra Deployment,
inicio 07/05/2026 y fin 06/11/2026. 33 servidor dirigidas aprobadas, incluidas
ambas fronteras, exclusión fuera de rango y recálculo de etapas. Ruff y mypy
aprobados. Tres Chrome con rutas reales/CSP a 390/900/1450 px aprobados:
consulta de corte, conservación del buscador y exclusión al día siguiente
del fin; capturas actualizadas en tmp/summary-inventory. Sin nuevas
extracciones, sin push.

## Iteraciones y fechas — segundo bloque, 28/10

Se incorpora classificationnodes/iterations con profundidad 15 para todos los
proyectos. Se guarda el árbol completo con identifiers, rutas y fechas junto
al Summary; los bloques que solo aparecen en iteraciones también tienen fila,
con Summary pendiente. Relación por código exacto: CR no absorbe CR2 ni S1
absorbe S10/CR2_S1. Las discrepancias de código requieren revisión, no se unen.

Inicio: fecha de Discovery inequívoca. Fin, por aclaración expresa del usuario:
última fecha final válida registrada entre las etapas del bloque, aunque
Deployment esté vacío. Ejemplo probado: Discovery 14/05–26/05, Development
27/05–22/06, Deployment vacío → fin 22/06/2026. Se conservan los campos de
Summary y los avisos de fechas faltantes/diferencias. Etapa calculada a la fecha
de extracción; un rango vencido no significa cerrado. Solapamientos quedan
explícitos. Estado real y cortes EVA/KPI no cambian.

Extracción local real: 450 proyectos, 697 bloques, cero fallos de iteraciones,
36.482 s. AMK.012: S1 26/06/2025–24/10/2025, CR 29/10/2025–28/11/2025,
CR2 22/12/2025–24/04/2026. Summary llama a dos bloques CR1_S1/CR2_S1;
se mantienen pendientes de relacionar en vez de asumir equivalencia.

87 servidor (inventario/iteraciones/EVA nativo/Azure) y tres Chrome con CSP,
buscador y fechas Development a 390/900/1450 px aprobados. Capturas en
tmp/summary-inventory. Ruff y mypy de pages.py aprobados. Sin push.

## Primera extracción

28/10/2026. Por solicitud del usuario se prepara primero un inventario de
todos los proyectos visibles al PAT configurado, cerrados o no. Se revisaron
`msp_qa/services/project_catalog.py` y `block_splitter.py` como referencia.

Ruta: `/operativa/eva-1/summary/`, enlazada desde EVA 1. Buscador GET local
por ID, bloque, DM y resto de campos guardados. La tabla mantiene scroll
horizontal interno en pantallas pequeñas y no necesita JavaScript.

Comando: `.venv/Scripts/python.exe manage.py sync_summary_inventory`.
Azure lista con `stateFilter=all` y paginación; no hay exclusión por servicio,
ID comercial o cierre. Se guarda el Summary original y su estado Azure;
se separan los bloques reconocidos S1, S2, CR, CR2 y compuestos mediante el
diccionario existente. Los campos desconocidos/conflictivos quedan pendientes.
El estado técnico Azure no se interpreta como cierre de negocio.

Persistencia reutiliza las relaciones existentes EvaExtraction →
EvaAzureSource → EvaScopeSnapshot, sin migración ni cambio de conexión.
`metrics.kind=summary_inventory` y `full_inventory=False` aíslan estas
observaciones de los cortes publicados EVA y KPIs. Consulta con permiso
view_operations y alcance total; respuesta no-store. Extracción bajo candado,
publicación transaccional; fallo de transporte conserva el inventario anterior.
No se extraen Clockify/work items en este primer bloque: sus cifras y riesgos
no se inventan a partir del Summary. Tampoco se reconstruyen cortes antiguos.

Extracción real local: 450 proyectos, 558 bloques, 4.625 s. Las filas sin ID
válido conservan nombre/identidad Azure y aparecen pendientes. Los cerrados
no se descartan. Esto acredita lectura con el PAT actual, no acceso a proyectos
fuera de su alcance ni que todos los Summary tengan datos completos.

Validación: 84 pruebas servidor (inventario, EVA nativo y Azure), tres Chrome
con rutas reales/CSP a 390/900/1450 px, buscador y ausencia de desbordamiento
de página; capturas `tmp/summary-inventory/summary-{ancho}.png` inspeccionadas.
Ruff, mypy de pages.py y manage.py check aprobados. Ajustes de tipado en el
parser/lector conservan sus reglas. Sin push; fase 11 sigue abierta.
