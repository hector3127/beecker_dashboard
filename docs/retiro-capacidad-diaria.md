# Fase 11: retiro de la presentación anterior de Capacidad diaria

Base: **ad14366**. No se modifican las fuentes ni las reglas de fechas de
`834bbfa`, los servicios de Capacidad, las horas, el modelo vigente, la
clasificación de conceptos o las fórmulas de disponibilidad.

## Retiro

- `views.capacidad_detalle` y su bifurcación en `pages.capacity_daily`.
- `portal/capacidad_detalle.html`.
- `portal/js/capacidad_instalada.js` y `portal/css/capacidad_instalada.css`.

La ruta y su nombre Django permanecen, al igual que el regreso a Operativa.
`vista=anterior` ahora entrega la pantalla modular. Se conserva la emisión
de cookie CSRF de la vista retirada mediante `ensure_csrf_cookie` en la
entrada vigente; no se activan políticas ni permisos globales.

Los únicos consumidores de esos assets eran la plantilla retirada y sus
pruebas. `core/js/gas_shim.js` no se borra: otros respaldos aún lo necesitan.

## Referencias guardadas antes de borrar

1. **Ocho escenarios del modelo anterior**, ejecutados desde su archivo aún
   presente y comprobados contra el modelo actual antes del retiro. Incluyen
   horas conocidas, pendientes, Sin Asignación, proyectos compartidos, sin ID,
   fuera del mes, reglas ausentes o excluyentes y error de fuente. Sus salidas
   completas se versionan en `tests/frontend/snapshots/capacity_daily_model.json`.
   La prueba actual sigue comparando esos ocho resultados, sin ejecutar código
   antiguo ni recalcular la referencia desde el modelo que se comprueba.
2. **Seis snapshots de diseño vigente**: matriz y recursos, a 1450/900/390 px.
   Cajas y estilos calculados en `tests/e2e/snapshots/capacity_daily_layout_*`.
   Se capturaron antes de borrar y pasan después con CSP real en el navegador.
   Las seis imágenes completas son idénticas píxel a píxel.

Los dos tests del controlador RPC anterior se sustituyen por dos contratos
del modelo/exportación vigente. La interacción que antes simulaban se mantiene
en navegador real: base/carga progresiva, selección, búsqueda, recursos, cambio
de jornada, CSV filtrado y actualización forzada. Ese flujo ahora se ejecuta
con y sin el parámetro obsoleto. No se elimina cobertura del modelo ni se
omiten casos para retirar el archivo.

La prueba de página sin lectura de fuentes se conserva en la ruta actual,
incluyendo cookie CSRF y login. La comprobación antigua del body `class="ds"`
falló en la primera corrida dirigida (17 aprobadas, un fallo); se actualizó
a la clase vigente `ds capacity-daily-page`, sin cambiar HTML de producción.
Se extienden al parámetro obsoleto los casos de alcance limitado, capacidad
incorrecta y acceso anónimo.

## Verificación

- **23 Chrome aprobadas**: `test_capacidad_diaria.py`, `test_capacidad.py` y
  `test_project_independence.py`, con `--no-cov --browser-channel chrome
  --tb=short` (81 s). Incluyen las seis referencias con CSP y sus avisos,
  actualización/CSV con enlaces obsoletos, fallos/reintento, paginación y texto
  seguro, Capacidad mensual y las cinco familias sin motor/shim/RPC anteriores.
- **504 Node aprobadas**: `node --test tests/frontend/*.test.*`. Se mantienen
  los tres casos de modelo y los dos contratos que sustituyen los tests RPC.
- **1727 servidor aprobadas** con `pytest tests/portal tests/core tests/access
  tests/capacidad/test_history_range.py tests/test_api.py -q --no-cov
  --tb=short` (162 s), sin fallos ni omisiones. Incluye cookie CSRF/login,
  enlaces obsoletos y rechazo de alcance/capacidad antes de leer fuentes.
- Ruff/formato (712 archivos), mypy de pages.py y diff de espacios aprobados.

Artefactos locales ignorados: `tmp/fase11/capacity-daily-before/`,
`tmp/migration/capacity_daily/`, `tmp/phase11-daily-*.log`. El capturador del
modelo se ejecutó antes de borrar (`tmp/capture-daily-model.mjs`) y no forma
parte del producto ni de las pruebas versionadas.

## Siguiente bloque

El recuento real del directorio es **19 HTML y 32 estáticos** en portal;
este dato corrige las estimaciones de estáticos de bloques anteriores.
Las otras comparaciones y sus
dependencias siguen pendientes, junto a la certificación CSP integral. No
recrear estos archivos ni retirar servicios, bases o shim todavía utilizados.
No se activa CSP global/ACCESS_ENFORCED; sin push de este bloque.
