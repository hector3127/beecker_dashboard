# Retirada del flujo anterior de EVA — 28/10/2026

El inventario de Summary e iteraciones es la fuente activa de EVA, junto con
horas facturables Clockify y revisiones históricas Azure guardadas localmente.
Se retiran el extractor anterior, sus rutas de estado y cerrados, su comando,
el panel de actualización y el enlace auxiliar de inventario. Las tareas de
sincronización y la precarga usan el flujo nuevo; no se instalaron tareas.
Los KPIs mensuales también consultan este inventario.

La migración 0010 elimina cuatro extracciones del flujo anterior y su candado.
Conserva diez extracciones de Summary y las 781,628 revisiones Azure. Respaldo
local previo: `tmp/backups/before-retire-eva-20261028.sqlite3`. La 0011 elimina
los campos obsoletos `full_inventory` y `closed`; las tablas compartidas se
conservan porque almacenan el inventario nuevo. No se retiran servicios Sheets
que siguen usando otras pantallas. PostgreSQL continúa pendiente de Genesis.

Suspendido requiere evidencia explícita: estado del General, intervalo de
suspensión explícito o WI RSP activo (situación Suspended, o sin situación).
RCP solo aplica si declara situación Suspended; un RCP de cancelación no basta.
No se infieren suspensiones de huecos entre etapas. La evidencia se evalúa al
corte con revisiones históricas. Se enriquecieron 1,834 revisiones RSP/RCP en
4.371 s, sin duplicarlas, incluyendo ProjectSituation y fechas del reporte.

T y C son proporciones de proyectos conformes entre todos los visibles, como
en KPIs de DM: desviación de días <= 0 y avance <= 100%, respectivamente.
No se reduce el denominador por datos faltantes ni se inventan costos.
En la comprobación local del 29/01/2026 hay 22 proyectos, siete suspendidos y
T=100%; C queda pendiente porque MCC.023_S2 carece de Burn verificable.

Validación: regresión previa de este bloque, 1,842 pruebas servidor; después,
183 dirigidas tras migración 0011 y 21 dirigidas finales (alcances solapados).
478 Node aprobadas. Check, makemigrations --check, mypy de pages y Ruff de
los módulos nuevos pasan. La ejecución inicial del navegador no encontró el
Chromium empaquetado; los diez casos pasan con Chrome instalado (EVA a tres
tamaños, filtros, exportación, navegación y Summary). No se hizo push.
