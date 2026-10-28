# Inventario de Summary — primer bloque

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
