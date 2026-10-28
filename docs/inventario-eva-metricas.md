# Métricas EVA persistidas en el inventario

## Iconos y disponibilidad al consultar cortes

Los encabezados WI usan 🤖/✅/⌛ con títulos y nombres accesibles. Consultar
un corte conserva GET y funcionamiento sin JS; un módulo de página muestra
indicador/celdas de carga durante la navegación, bloquea doble envío y restaura
estado en pageshow. A los 15 s restaura controles y ofrece reintento, sin
simular una extracción ni añadir consultas a proveedores. Respeta reduced-motion.

Los cortes anteriores a la observación muestran Sin histórico y una explicación,
en lugar del ambiguo Pendiente. Otros faltantes muestran Sin observación/Sin
datos. No se deja un spinner sin trabajo en curso ni se presentan los estados
actuales como históricos. Datos, fórmulas, permisos y fuentes conservados.

21 servidor de inventario/métricas y cinco Chrome con rutas reales/CSP
aprobados, incluidos iconos, disponibilidad histórica, inicio de carga, salida
por timeout con reloj simulado, recarga y tres tamaños. Ruff/mypy aprobados.
Sin extracciones adicionales ni push.

28/10/2026. Por solicitud del usuario, `sync_summary_inventory` incorpora
horas facturables de Clockify y work items de Azure al mismo inventario de
Summary/iteraciones. No modifica el inventario ni los cortes publicados del
EVA nativo/KPI. Mantiene SQLite y los permisos existentes.

## Datos guardados

EvaExtraction → EvaAzureSource → EvaScopeSnapshot conserva las relaciones
existentes, sin migración. El payload de cada fuente guarda Summary, árbol
de iteraciones, work items completos, evidencia Clockify por ID proveedor,
mapeo de proveedores por bloque y fecha observada. Cada fila guarda
`eva_metrics`: Burn, ETC, hoursDeviation, avance, conteos por etapa y riesgos.
Reproceso `--from-local` reutiliza esa evidencia y conserva fecha de fuente.

Se consultan todos los proyectos visibles al PAT, incluidos cerrados y todos
los servicios. WIQL usa el nombre del proyecto, no su GUID. La extracción
usa cuatro workers; una sola publicación transaccional, bajo candado. Los
fallos de transporte o identidad permanecen pendientes, nunca ceros ficticios.

## Reglas

- Start/Finish de iteraciones: inicio Discovery y último fin válido de etapa.
- Burn facturable dentro del rango y hasta el corte; deduplicación por entry ID,
  asignación por tarea/tag y alcance. Se reutilizan meses completos persistidos;
  el mes actual se consulta. No hay solicitudes de proveedores desde la página.
- ETC = Budget − Burn; Desv. Hrs = min(ETC, 0); Avance = Burn/Budget×100.
  Budget ausente o cero no genera un porcentaje ficticio.
- Se mantienen aliases CR autorizados, sin unir sprints/CR diferentes.
  Proyectos Clockify dedicados aíslan sus horas de los proveedores hermanos;
  cuando el proyecto es compartido, horas ambiguas dejan el bloque pendiente.
- Discovery/Development/Deployment: total, cerrados, pendientes del bloque;
  General usa el conteo general del motor EVA existente. Riesgos usa su misma
  regla de Risk activo/propuesto, excluyendo cerrados.
- La etapa visible se sigue calculando por calendario a la fecha consultada.
  Tareas/riesgos solo se muestran cuando el corte coincide con la observación.
  Horas de fechas anteriores se calculan sobre registros guardados; esto no
  reconstruye cómo era el reporte antes de correcciones retroactivas en origen.
  Fechas posteriores a la observación no reciben horas o estados inventados.

## Comprobación

Pruebas específicas cubren persistencia real de campos/evidencia, lectura con
proveedores bloqueados, corte anterior/futuro, cero/sobregasto, riesgos cerrados,
duplicados de alcance, aliases y proveedores dedicados. Chrome comprueba valores
persistidos (incluido cero), porcentajes y tabla responsiva con rutas reales/CSP.
La interfaz no cambia su conjunto de columnas ni sus filtros.

Validación final: 110 servidor dirigidas (Azure, inventario, métricas,
iteraciones, resumen DM y EVA nativo), cuatro Chrome con rutas reales/CSP
(tres tamaños y cifras persistidas), Ruff, mypy de pages.py y manage.py check.
Chrome local real AMK.004 al 28/10: Burn 96.75, ETC/Desv. Hrs -35.75,
avance 158.6%, riesgo activo visible y sin errores JS. Captura local
`tmp/summary-inventory/metrics-real.png`.

Extracción real: 450 proyectos, 685 bloques, 436.354 s, 1245 peticiones de
reportes Clockify y cero fallos de work items Azure. Reproceso local posterior
18.668 s sin red, conservando la fecha de esa extracción. 430 bloques con
horas verificables y 488 con conteos Azure verificables en el conjunto total;
los demás quedan pendientes por rangos/identidad/alcance. Al corte de hoy
hay nueve filas visibles y las nueve tienen horas/conteos. No extrapolar este
resultado a fechas históricas sin observación de tareas/riesgos.

Lectura local de ese corte medida una vez: 0.275 s (antes de limitar fuentes
al rango: 5.759 s). La consulta limita en SQL los proveedores que pueden
entrar al corte y conserva todos sus hermanos al asignar horas, evitando
duplicar la evidencia por cada fila. No es una medición de producción.
Sin PostgreSQL, cambios de permisos ni push.
