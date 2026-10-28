# Inventario de Summary — primer bloque

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
